#!/usr/bin/env python3
"""
Link existing videos/audio files in Supabase Storage to evaluations in the database.

This script:
1. Lists all files in the evaluation-media bucket
2. Extracts evaluation IDs from file paths (format: {user_id}/{evaluation_id}/{filename})
3. Updates the evaluations table with video_url or audio_url

Usage:
    python scripts/link_evaluation_videos.py

Requires:
    - SUPABASE_URL environment variable
    - SUPABASE_SERVICE_ROLE_KEY environment variable (for admin access)
    - supabase-py package: pip install supabase
"""

import os
import re
import sys
from pathlib import Path
from supabase import create_client, Client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_supabase_client() -> Client:
    """Create Supabase client from environment variables."""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set")
        print("Get these from: Supabase Dashboard → Settings → API")
        sys.exit(1)
    
    return create_client(supabase_url, supabase_key)

def is_video_file(filename: str) -> bool:
    """Check if filename is a video file."""
    video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.quicktime']
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def is_audio_file(filename: str) -> bool:
    """Check if filename is an audio file."""
    audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
    return any(filename.lower().endswith(ext) for ext in audio_extensions)

def extract_evaluation_id_from_path(path: str) -> str:
    """
    Extract evaluation ID from storage path.
    Expected format: {user_id}/{evaluation_id}/{filename}
    """
    parts = path.split('/')
    if len(parts) >= 3:
        # Second part should be the evaluation ID
        eval_id = parts[1]
        # Validate UUID format
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, eval_id, re.IGNORECASE):
            return eval_id
    return None

def link_videos_to_evaluations():
    """Main function to link storage files to evaluations."""
    supabase = get_supabase_client()
    bucket_name = 'evaluation-media'
    
    print(f"🔍 Listing files in '{bucket_name}' bucket...")
    
    try:
        # Get storage bucket - use the correct API method
        # Supabase Python client: storage.from() returns a StorageFileApi object
        storage_bucket = getattr(supabase.storage, 'from')(bucket_name)
        
        # List files recursively (get all files in all subdirectories)
        def list_files_recursive(path=''):
            """Recursively list all files in the bucket."""
            try:
                # Call the list method (note: 'list' is a built-in, so we use getattr)
                list_method = getattr(storage_bucket, 'list', None)
                if not list_method:
                    # Try alternative: some versions use list_files()
                    list_method = getattr(storage_bucket, 'list_files', None)
                
                if not list_method:
                    raise AttributeError("Storage bucket doesn't have list() or list_files() method")
                
                response = list_method(path) if path else list_method()
                all_files = []
                
                # Handle different response formats
                if isinstance(response, list):
                    items = response
                elif hasattr(response, 'data'):
                    items = response.data or []
                elif hasattr(response, 'json'):
                    # If it's a response object, get JSON
                    items = response.json() or []
                else:
                    items = []
                
                for item in items:
                    item_name = item.get('name') or item.get('id', '')
                    if not item_name:
                        continue
                    
                    # Check if it's a file (has metadata or is not a folder)
                    # Files typically have 'id' or 'metadata', folders don't
                    is_file = item.get('id') is not None or (item.get('metadata') is not None and not item.get('name', '').endswith('/'))
                    
                    if is_file:
                        full_path = f"{path}/{item_name}" if path else item_name
                        all_files.append({
                            'name': full_path,
                            'id': item.get('id'),
                            'metadata': item.get('metadata', {})
                        })
                    else:
                        # It's a folder, recurse
                        folder_path = f"{path}/{item_name}" if path else item_name
                        all_files.extend(list_files_recursive(folder_path))
                
                return all_files
            except Exception as e:
                print(f"Warning: Error listing path '{path}': {e}")
                return []
        
        files = list_files_recursive()
        
        if not files:
            print("No files found in bucket.")
            return
        
        print(f"Found {len(files)} files in bucket")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for file_info in files:
            file_path = file_info.get('name', '')
            
            # Skip if not in expected format
            if '/' not in file_path:
                skipped_count += 1
                continue
            
            # Extract evaluation ID
            eval_id = extract_evaluation_id_from_path(file_path)
            if not eval_id:
                skipped_count += 1
                continue
            
            # Get public URL
            try:
                # Get public URL from storage
                public_url_response = storage_bucket.get_public_url(file_path)
                
                # Handle different response formats
                if isinstance(public_url_response, dict):
                    public_url = public_url_response.get('publicUrl') or public_url_response.get('public_url') or str(public_url_response)
                elif isinstance(public_url_response, str):
                    public_url = public_url_response
                else:
                    # Construct URL manually if needed
                    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
                    public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
                
                # Determine if video or audio
                filename = file_path.split('/')[-1]
                is_video = is_video_file(filename)
                is_audio = is_audio_file(filename)
                
                if not is_video and not is_audio:
                    skipped_count += 1
                    continue
                
                # Check if evaluation exists and needs update
                eval_response = supabase.table('evaluations').select('id, video_url, audio_url').eq('id', eval_id).execute()
                
                if not eval_response.data:
                    print(f"⚠️  Evaluation {eval_id} not found for file: {file_path}")
                    skipped_count += 1
                    continue
                
                eval_data = eval_response.data[0]
                needs_update = False
                update_data = {}
                
                if is_video and not eval_data.get('video_url'):
                    update_data['video_url'] = public_url
                    needs_update = True
                elif is_audio and not eval_data.get('audio_url'):
                    update_data['audio_url'] = public_url
                    needs_update = True
                
                if needs_update:
                    # Update evaluation
                    result = supabase.table('evaluations').update(update_data).eq('id', eval_id).execute()
                    
                    if result.data:
                        updated_count += 1
                        media_type = 'video' if is_video else 'audio'
                        print(f"✅ Linked {media_type}: {file_path} → evaluation {eval_id}")
                    else:
                        error_count += 1
                        print(f"❌ Failed to update evaluation {eval_id} for file: {file_path}")
                else:
                    skipped_count += 1
                    print(f"⏭️  Skipped {file_path} (evaluation already has media URL)")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing {file_path}: {e}")
        
        print("\n" + "="*60)
        print("Summary:")
        print(f"  ✅ Updated: {updated_count}")
        print(f"  ⏭️  Skipped: {skipped_count}")
        print(f"  ❌ Errors: {error_count}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        print("\nMake sure:")
        print("  1. The 'evaluation-media' bucket exists in Supabase Storage")
        print("  2. You have SUPABASE_SERVICE_ROLE_KEY set (not just ANON_KEY)")
        print("  3. The bucket has proper RLS policies or you're using service role key")
        sys.exit(1)

if __name__ == '__main__':
    link_videos_to_evaluations()
