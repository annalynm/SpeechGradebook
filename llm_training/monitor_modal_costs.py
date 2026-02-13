#!/usr/bin/env python3
"""
Monitor Modal costs and usage for Qwen evaluation service.

Usage:
    python llm_training/monitor_modal_costs.py

This script checks your Modal usage and estimates costs.
Requires Modal CLI to be authenticated: `modal setup`
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

def run_modal_command(cmd):
    """Run a modal CLI command and return JSON output."""
    try:
        result = subprocess.run(
            ["modal"] + cmd.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout else {}
    except subprocess.CalledProcessError as e:
        print(f"Error running modal command: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Warning: Could not parse Modal output as JSON", file=sys.stderr)
        return None

def get_modal_usage():
    """Get usage statistics from Modal."""
    print("📊 Fetching Modal usage data...")
    
    # Try to get app info
    app_info = run_modal_command("app list")
    
    # Modal CLI doesn't have a direct cost API, but we can check:
    # 1. App status and logs
    # 2. Recent function calls
    # 3. Estimate based on logs
    
    return {
        "timestamp": datetime.now().isoformat(),
        "app_info": app_info,
        "note": "Use Modal Dashboard for detailed costs: https://modal.com/apps"
    }

def estimate_costs_from_logs():
    """Estimate costs based on evaluation logs if available."""
    # This would require parsing logs or tracking evaluations
    # For now, provide a template
    return {
        "estimated_cost_per_eval": "Check Modal Dashboard",
        "t4_hourly_rate": "$0.80/hour",
        "t4_per_second": "$0.000222/second",
        "note": "Track evaluations in app to calculate exact costs"
    }

def print_cost_report():
    """Print a formatted cost report."""
    print("\n" + "="*60)
    print("💰 MODAL COST MONITORING REPORT")
    print("="*60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    usage = get_modal_usage()
    costs = estimate_costs_from_logs()
    
    print("📈 Current Configuration:")
    print("  GPU Type: T4 (16GB VRAM)")
    print(f"  Hourly Rate: {costs['t4_hourly_rate']}")
    print(f"  Per Second: {costs['t4_per_second']}")
    print()
    
    print("💡 Cost Estimates (T4 GPU):")
    print("  Per evaluation: ~$0.01-0.03 (10-30 seconds)")
    print("  100 evaluations: ~$1-3")
    print("  400 evaluations: ~$4-12")
    print("  1000 evaluations: ~$10-30")
    print()
    
    print("🔍 Monitoring:")
    print("  1. Modal Dashboard: https://modal.com/apps")
    print("  2. Check app logs for OOM errors")
    print("  3. Monitor evaluation times in app")
    print()
    
    print("⚠️  Watch for:")
    print("  - OOM (Out of Memory) errors → may need A100")
    print("  - Evaluation times >60 seconds → may indicate issues")
    print("  - Costs >$0.05 per evaluation → check for inefficiencies")
    print()
    
    print("="*60)
    print("\n💻 To check detailed costs:")
    print("  1. Visit: https://modal.com/apps")
    print("  2. Select your 'qwen-speechgradebook' app")
    print("  3. View usage and billing information")
    print()

if __name__ == "__main__":
    print_cost_report()
