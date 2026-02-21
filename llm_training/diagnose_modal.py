#!/usr/bin/env python3
"""
Diagnostic script to check Modal service status and identify issues.

Run this to get a comprehensive report of what's happening with your Modal deployment.
"""

import subprocess
import sys
import json
import os

def run_command(cmd, description):
    """Run a command and return output."""
    print(f"\n{'='*60}")
    print(f"Checking: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, "", str(e)

def check_modal_status():
    """Check if Modal CLI is available and authenticated."""
    print("\n" + "="*60)
    print("STEP 1: Checking Modal CLI Status")
    print("="*60)
    
    success, stdout, stderr = run_command("modal --version", "Modal CLI version")
    if not success:
        print("❌ Modal CLI not found or not working")
        print("   Install with: pipx install modal")
        return False
    
    success, stdout, stderr = run_command("modal app list", "List Modal apps")
    if not success:
        print("❌ Cannot list Modal apps - check authentication")
        print("   Run: modal setup")
        return False
    
    if "qwen-speechgradebook" in stdout:
        print("✅ qwen-speechgradebook app found")
    else:
        print("⚠️  qwen-speechgradebook app not found - may need to deploy")
    
    return True

def check_modal_logs():
    """Check recent Modal logs for errors."""
    print("\n" + "="*60)
    print("STEP 2: Checking Modal Logs (Last 50 lines)")
    print("="*60)
    
    success, stdout, stderr = run_command(
        "modal app logs qwen-speechgradebook --tail 50",
        "Recent Modal logs"
    )
    
    if not success:
        print("⚠️  Could not fetch logs - check Modal dashboard manually")
        print("   https://modal.com/apps → qwen-speechgradebook → Logs")
        return False
    
    # Look for common errors
    errors_found = []
    if "OOM" in stdout or "out of memory" in stdout.lower():
        errors_found.append("Out of Memory (OOM) - GPU may not have enough memory")
    if "model not loaded" in stdout.lower():
        errors_found.append("Model not loaded - service may be starting")
    if "timeout" in stdout.lower():
        errors_found.append("Timeout errors detected")
    if "503" in stdout or "Service Unavailable" in stdout:
        errors_found.append("503 Service Unavailable errors")
    if "error" in stdout.lower() or "exception" in stdout.lower():
        errors_found.append("General errors detected")
    
    if errors_found:
        print("\n⚠️  Potential Issues Found:")
        for error in errors_found:
            print(f"   - {error}")
    else:
        print("\n✅ No obvious errors in recent logs")
    
    return True

def check_health_endpoint():
    """Check the health endpoint."""
    print("\n" + "="*60)
    print("STEP 3: Checking Health Endpoint")
    print("="*60)
    
    # Try to get URL from environment or config
    modal_url = os.environ.get("QWEN_API_URL", "")
    if not modal_url:
        print("⚠️  QWEN_API_URL not set in environment")
        print("   Check Render dashboard for QWEN_API_URL")
        modal_url = input("Enter Modal URL (or press Enter to skip): ").strip()
        if not modal_url:
            return False
    
    # Remove trailing slash
    modal_url = modal_url.rstrip('/')
    health_url = f"{modal_url}/health"
    
    try:
        import requests
        print(f"Testing: {health_url}")
        response = requests.get(health_url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("status") == "ok":
                    print("✅ Service is healthy and model is loaded")
                elif data.get("status") == "model_not_loaded":
                    print("⚠️  Service is up but model is still loading")
                else:
                    print(f"⚠️  Unexpected status: {data}")
            except:
                print(f"⚠️  Could not parse JSON response: {response.text}")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except ImportError:
        print("⚠️  'requests' library not installed - using curl")
        success, stdout, stderr = run_command(
            f"curl -s {health_url}",
            f"Health endpoint: {health_url}"
        )
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False
    
    return True

def check_render_config():
    """Check Render configuration."""
    print("\n" + "="*60)
    print("STEP 4: Configuration Check")
    print("="*60)
    
    print("Please verify in Render Dashboard:")
    print("1. QWEN_API_URL is set correctly")
    print("2. Should be: https://annalynm--qwen-speechgradebook.modal.run")
    print("3. No trailing slash")
    print("4. Service is deployed and running")
    
    return True

def main():
    """Run all diagnostic checks."""
    print("\n" + "="*60)
    print("MODAL SERVICE DIAGNOSTIC TOOL")
    print("="*60)
    print("\nThis script will check your Modal deployment and identify issues.")
    print("Make sure you have:")
    print("  - Modal CLI installed (pipx install modal)")
    print("  - Authenticated (modal setup)")
    print("  - Deployed the service (modal deploy llm_training/qwen_modal.py)")
    
    input("\nPress Enter to continue...")
    
    results = []
    results.append(("Modal CLI", check_modal_status()))
    results.append(("Modal Logs", check_modal_logs()))
    results.append(("Health Endpoint", check_health_endpoint()))
    results.append(("Configuration", check_render_config()))
    
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Review the output above for specific errors")
    print("2. Check Modal dashboard: https://modal.com/apps")
    print("3. Check Render logs: https://dashboard.render.com")
    print("4. If issues persist, see llm_training/TROUBLESHOOTING_500_ERROR.md")
    print("\nIf Modal continues to be unreliable, consider alternatives:")
    print("  - RunPod, Lambda Labs, or Vast.ai (similar serverless GPU)")
    print("  - Self-hosted on cloud VM (AWS, GCP, Azure)")
    print("  - Different model/service architecture")

if __name__ == "__main__":
    main()
