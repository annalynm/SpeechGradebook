# Modal Cost Monitoring Guide

This guide helps you track and monitor costs for the Qwen evaluation service on Modal.

## Quick Cost Reference (T4 GPU)

| Evaluations/Month | Estimated Cost |
|-------------------|----------------|
| 50 | ~$0.50-1.50 |
| 100 | ~$1-3 |
| 400 | ~$4-12 |
| 1,000 | ~$10-30 |
| 2,000 | ~$20-60 |

**Cost per evaluation:** ~$0.01-0.03 (10-30 seconds of GPU time)

## Monitoring Methods

### 1. Modal Dashboard (Primary)

**URL:** https://modal.com/apps

**What to check:**
- Select your `qwen-speechgradebook` app
- View **Usage** tab for GPU hours
- Check **Billing** for current month costs
- Review **Logs** for errors (especially OOM)

**Frequency:** Check weekly or after significant usage

### 2. Run Monitoring Script

```bash
cd /path/to/SpeechGradebook
python llm_training/monitor_modal_costs.py
```

This provides a quick cost estimate and reminders.

### 3. Track in Application

The app logs evaluation requests. Monitor:
- Evaluation completion times
- Error rates (especially OOM errors)
- Number of evaluations per day/week

## Cost Alerts

### Red Flags (Investigate Immediately)

1. **Cost >$0.05 per evaluation**
   - Possible causes: Long processing times, inefficient code, wrong GPU type
   - Action: Check logs for bottlenecks

2. **OOM (Out of Memory) errors**
   - T4 may not have enough memory for large videos
   - Action: Consider switching back to A100 or optimizing video processing

3. **Monthly cost >$50**
   - May indicate unexpected usage or inefficiency
   - Action: Review evaluation patterns, check for stuck processes

### Yellow Flags (Monitor Closely)

1. **Evaluation time >60 seconds**
   - May indicate performance issues
   - Action: Check video file sizes, model loading times

2. **Cold starts >90 seconds**
   - Normal but indicates idle time
   - Action: Consider if you need more frequent usage

## Cost Optimization Tips

1. **Batch evaluations** when possible (reduces cold starts)
2. **Monitor video file sizes** (larger = longer processing = higher cost)
3. **Check for stuck/retry loops** (can inflate costs)
4. **Use T4 for most evaluations** (switch to A100 only if needed)

## Monthly Cost Tracking

Create a simple spreadsheet or document to track:

| Date | Evaluations | Estimated Cost | Notes |
|------|-------------|----------------|-------|
| Month Start | 0 | $0 | Baseline |
| Week 1 | X | $X | |
| Week 2 | X | $X | |
| Week 3 | X | $X | |
| Week 4 | X | $X | |
| **Total** | **X** | **$X** | Compare to Modal dashboard |

## When to Reconsider Infrastructure

**Switch to RunPod if:**
- Monthly costs consistently >$30
- Need concurrent evaluations (Modal allows only 1 at a time)
- Cold starts become a major bottleneck
- You have predictable usage patterns (can schedule uptime)

**Switch back to A100 if:**
- Frequent OOM errors on T4
- Video processing consistently fails
- Evaluation quality degrades

## Quick Commands

```bash
# Check Modal app status
modal app list

# View app logs
modal app logs qwen-speechgradebook

# Run cost monitoring script
python llm_training/monitor_modal_costs.py

# Deploy updated configuration
modal deploy llm_training/qwen_modal.py
```

## Support

- **Modal Dashboard:** https://modal.com/apps
- **Modal Docs:** https://modal.com/docs
- **Modal Support:** Check Modal dashboard for support options
