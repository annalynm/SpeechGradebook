#!/usr/bin/env python3
"""
Link existing videos/audio files in Supabase Storage to evaluations in the database.

Simpler version that uses the Supabase Storage API correctly.

Usage:
    python3 scripts/link_evaluation_videos_simple.py

Requires:
    - SUPABASE_URL environment variable
    - SUPABASE_SERVICE_ROLE_KEY environment variable (for admin access)
    - supabase-py package: pip install supabase
"""

import os
import re
import sys
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # Try to manually parse .env file if dotenv not available
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
        except Exception:
            pass
except Exception:
    pass  # .env file might not exist, that's okay

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: supabase package not installed. Run: pip install supabase")
    sys.exit(1)

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
    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    
    print(f"🔍 Listing files in '{bucket_name}' bucket...")
    print(f"Supabase URL: {supabase_url}")
    
    try:
        # Get storage bucket using the correct method
        # The Supabase Python client uses: storage.from(bucket_name)
        storage_api = supabase.storage
        bucket = storage_api.from_(bucket_name)  # Use from_ to avoid keyword conflict
        
        # List all files recursively
        def list_all_files(path='', all_files=None):
            """Recursively list all files."""
            if all_files is None:
                all_files = []
            
            try:
                # List items in current path
                result = bucket.list(path)
                
                # Handle response - could be list, dict, or response object
                items = []
                if isinstance(result, list):
                    items = result
                elif hasattr(result, 'data'):
                    items = result.data or []
                elif isinstance(result, dict) and 'data' in result:
                    items = result['data'] or []
                
                for item in items:
                    item_name = item.get('name', '') or item.get('id', '')
                    if not item_name:
                        continue
                    
                    full_path = f"{path}/{item_name}" if path else item_name
                    
                    # Check if it's a file (has 'id' or 'metadata') or folder
                    if item.get('id') or item.get('metadata'):
                        # It's a file
                        all_files.append(full_path)
                    else:
                        # It's a folder, recurse
                        list_all_files(full_path, all_files)
                
            except Exception as e:
                print(f"Warning: Error listing '{path}': {e}")
            
            return all_files
        
        files = list_all_files()
        
        if not files:
            print("No files found in bucket.")
            print("\nTrying alternative method...")
            # Try listing root directory only
            try:
                root_items = bucket.list('')
                print(f"Root listing result type: {type(root_items)}")
                if isinstance(root_items, list):
                    print(f"Found {len(root_items)} items in root")
                    files = [item.get('name', '') for item in root_items if item.get('name')]
            except Exception as e2:
                print(f"Alternative method also failed: {e2}")
                print("\nYou may need to manually update evaluations. See docs/LINK_EVALUATION_VIDEOS.sql")
                return
        
        print(f"Found {len(files)} files in bucket")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        skip_reasons = {
            'invalid_path': 0,
            'no_eval_id': 0,
            'not_media': 0,
            'eval_not_found': 0,
            'already_has_media': 0
        }
        
        for file_path in files:
            if not file_path or '/' not in file_path:
                skipped_count += 1
                skip_reasons['invalid_path'] += 1
                continue
            
            # Extract evaluation ID
            eval_id = extract_evaluation_id_from_path(file_path)
            if not eval_id:
                skipped_count += 1
                skip_reasons['no_eval_id'] += 1
                # Show all files that couldn't extract eval ID (usually only a few)
                print(f"  ⏭️  Skipped (no eval ID): {file_path}")
                continue
            
            # Determine if video or audio
            filename = file_path.split('/')[-1]
            is_video = is_video_file(filename)
            is_audio = is_audio_file(filename)
            
            if not is_video and not is_audio:
                skipped_count += 1
                skip_reasons['not_media'] += 1
                continue
            
            # Construct public URL
            public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
            
            try:
                # Check if evaluation exists
                eval_response = supabase.table('evaluations').select('id, video_url, audio_url').eq('id', eval_id).execute()
                
                if not eval_response.data:
                    print(f"⚠️  Evaluation {eval_id} not found for: {file_path}")
                    skipped_count += 1
                    skip_reasons['eval_not_found'] += 1
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
                        print(f"❌ Failed to update evaluation {eval_id}")
                else:
                    skipped_count += 1
                    skip_reasons['already_has_media'] += 1
                    if skipped_count <= 5:  # Show first few examples
                        media_type = 'video' if is_video else 'audio'
                        existing = eval_data.get('video_url') or eval_data.get('audio_url')
                        print(f"  ⏭️  Skipped (already has {media_type}): {file_path}")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing {file_path}: {e}")
        
        print("\n" + "="*60)
        print("Summary:")
        print(f"  ✅ Updated: {updated_count}")
        print(f"  ⏭️  Skipped: {skipped_count}")
        print(f"  ❌ Errors: {error_count}")
        print("\nSkip Reasons:")
        if skip_reasons['invalid_path'] > 0:
            print(f"  - Invalid path format: {skip_reasons['invalid_path']}")
        if skip_reasons['no_eval_id'] > 0:
            print(f"  - Could not extract evaluation ID: {skip_reasons['no_eval_id']}")
        if skip_reasons['not_media'] > 0:
            print(f"  - Not a video/audio file: {skip_reasons['not_media']}")
        if skip_reasons['eval_not_found'] > 0:
            print(f"  - Evaluation not found in database: {skip_reasons['eval_not_found']}")
        if skip_reasons['already_has_media'] > 0:
            print(f"  - Evaluation already has media URL: {skip_reasons['already_has_media']}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set")
        print("  2. Check that the 'evaluation-media' bucket exists")
        print("  3. Verify you have admin access (service role key)")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    link_videos_to_evaluations()
