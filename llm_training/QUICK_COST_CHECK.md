# Quick Cost Check - Modal A100 GPU

## Current Configuration
- **GPU:** A100 (40GB VRAM) - Switched from T4 due to OOM errors
- **Cost per second:** ~$0.0011-0.0014
- **Cost per hour:** ~$4-5
- **Expected cost per evaluation:** ~$0.05-0.15 (30-90 seconds)

**Note:** T4 (14GB VRAM) was causing Out of Memory errors with larger videos, so we switched to A100 for reliability.

## How to Monitor Costs

### 1. Check Modal Dashboard (Primary)
**URL:** https://modal.com/apps

1. Log in to Modal
2. Select your `qwen-speechgradebook` app
3. View **Usage** or **Billing** tab
4. Check current month's GPU hours and costs

### 2. Check Application Logs
Cost tracking is automatically logged in your Render/Render logs:
- Look for `[COST_TRACKING]` entries
- Each evaluation logs: duration, estimated cost, status
- Check Render logs: https://dashboard.render.com → Your service → Logs

### 3. Run Monitoring Script
```bash
python llm_training/monitor_modal_costs.py
```

## Cost Estimates

| Evaluations | Estimated Cost (A100) |
|-------------|----------------------|
| 50 | $2.50-7.50 |
| 100 | $5-15 |
| 400 | $20-60 |
| 1,000 | $50-150 |

## Red Flags

⚠️ **Investigate if you see:**
- Cost >$0.20 per evaluation (may indicate inefficiency)
- OOM (Out of Memory) errors in logs (shouldn't happen with A100)
- Monthly cost >$200 (may need optimization)
- Evaluation times consistently >120 seconds

## Next Steps After Deployment

1. **Deploy T4 configuration:**
   ```bash
   modal deploy llm_training/qwen_modal.py
   ```

2. **Test 2-3 evaluations** and check:
   - No OOM errors (shouldn't occur with A100)
   - Cost per evaluation is ~$0.05-0.15
   - Evaluation completes successfully

3. **Monitor for first week:**
   - Check Modal dashboard daily
   - Review application logs for cost tracking entries
   - Verify costs match expectations

4. **If issues occur:**
   - OOM errors → Consider switching back to A100
   - High costs → Check for stuck processes or retry loops
   - Slow evaluations → Check video file sizes
