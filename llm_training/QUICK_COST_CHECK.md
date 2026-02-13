# Quick Cost Check - Modal T4 GPU

## Current Configuration
- **GPU:** T4 (16GB VRAM)
- **Cost per second:** ~$0.000222
- **Cost per hour:** ~$0.80
- **Expected cost per evaluation:** ~$0.01-0.03 (10-30 seconds)

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

| Evaluations | Estimated Cost (T4) |
|-------------|---------------------|
| 50 | $0.50-1.50 |
| 100 | $1-3 |
| 400 | $4-12 |
| 1,000 | $10-30 |

## Red Flags

⚠️ **Investigate if you see:**
- Cost >$0.05 per evaluation
- OOM (Out of Memory) errors in logs
- Monthly cost >$50
- Evaluation times consistently >60 seconds

## Next Steps After Deployment

1. **Deploy T4 configuration:**
   ```bash
   modal deploy llm_training/qwen_modal.py
   ```

2. **Test 2-3 evaluations** and check:
   - No OOM errors
   - Cost per evaluation is ~$0.01-0.03
   - Evaluation completes successfully

3. **Monitor for first week:**
   - Check Modal dashboard daily
   - Review application logs for cost tracking entries
   - Verify costs match expectations

4. **If issues occur:**
   - OOM errors → Consider switching back to A100
   - High costs → Check for stuck processes or retry loops
   - Slow evaluations → Check video file sizes
