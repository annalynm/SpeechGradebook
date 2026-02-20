# Incident Response Runbook

This document outlines procedures for responding to common incidents in SpeechGradebook. Follow these steps when issues occur during the pilot or production use.

## General Incident Response Process

1. **Assess the situation**: Determine severity and scope
2. **Check status pages**: Verify if it's a known outage
3. **Notify stakeholders**: Inform instructors/users if service is affected
4. **Document the incident**: Record timeline and actions taken
5. **Post-incident review**: Analyze root cause and improve procedures

---

## 1. Supabase Down

### Symptoms
- Database queries fail
- Authentication fails
- Storage uploads/downloads fail
- Error messages mention Supabase connection

### Response Steps

1. **Check Supabase Status**
   - Visit: https://status.supabase.com
   - Check for known outages or maintenance
   - Review status page for your region

2. **Verify Connection**
   - Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` environment variables
   - Test connection: Visit `/config-check` endpoint
   - Review Render logs for connection errors

3. **Notify Users**
   - Send email/Slack notification to instructors
   - Post status update if you have a status page
   - Estimated downtime: Check Supabase status page

4. **Workaround (if possible)**
   - Switch to read-only mode if frontend can handle it
   - Instructors can continue working offline (localStorage fallback)
   - Data will sync when Supabase is restored

5. **Escalation**
   - Contact Supabase support if outage is unexpected
   - Check Supabase Discord/Slack for community updates
   - Document incident for post-mortem

### Recovery
- Service typically restores automatically
- Verify all systems operational after restoration
- Check for any data loss or inconsistencies

---

## 2. Modal (Qwen API) Down

### Symptoms
- Video evaluations fail
- `/qwen-api/health` returns 503
- Timeout errors when calling evaluation endpoint
- Error: "Failed to connect to Qwen service"

### Response Steps

1. **Check Modal Status**
   - Visit: https://modal.com/status (if available)
   - Check Modal dashboard for service status
   - Review Modal logs: https://modal.com/apps

2. **Verify Configuration**
   - Check `QWEN_API_URL` environment variable
   - Test endpoint: `GET /qwen-api/health`
   - Verify Cloudflare tunnel is running (if using tunnel)

3. **Notify Users**
   - Inform instructors that evaluations are temporarily unavailable
   - Provide estimated downtime if available
   - Suggest manual evaluation as temporary workaround

4. **Temporary Workaround**
   - Instructors can manually evaluate speeches
   - Disable Qwen endpoint temporarily to prevent error spam:
     - Set `QWEN_API_URL` to empty string
     - Or add feature flag to disable evaluations
   - Provide manual evaluation instructions

5. **Escalation**
   - Contact Modal support if service is down
   - Check if Cloudflare tunnel needs restart
   - Review Modal logs for error details

### Recovery
- Restart Modal service if needed
- Verify Qwen API is responding
- Test evaluation endpoint with sample video
- Re-enable evaluations when confirmed working

---

## 3. Render Deployment Failed

### Symptoms
- App returns 500 errors
- Recent deployment shows as failed
- Logs show application errors
- Service is unreachable

### Response Steps

1. **Check Render Dashboard**
   - Visit: https://dashboard.render.com
   - Review deployment logs
   - Check service status and health checks

2. **Review Recent Changes**
   - Check git commit history
   - Identify what changed in last deployment
   - Review error logs for specific failure

3. **Rollback Procedure**
   ```bash
   # Option 1: Revert last commit
   git revert HEAD
   git push
   
   # Option 2: Rollback to previous deployment in Render dashboard
   # Go to Service → Deploys → Select previous successful deploy → Rollback
   ```

4. **Fix and Redeploy**
   - Fix the issue in code
   - Test locally if possible
   - Deploy fix to Render

5. **Notify Users**
   - Inform if service was down
   - Apologize for interruption
   - Confirm service is restored

### Prevention
- Test changes locally before deploying
- Use staging environment if available
- Review logs before deploying
- Enable health checks in Render

---

## 4. Cost Spike

### Symptoms
- Unexpected high costs in Modal dashboard
- Cost tracking dashboard shows unusual activity
- Multiple evaluation requests in short time
- Rate limiting not working

### Response Steps

1. **Immediate Actions**
   - Check Modal logs for unusual activity
   - Review cost tracking dashboard
   - Check rate limiting logs
   - Disable Qwen endpoint temporarily if needed:
     - Set `QWEN_API_URL` to empty string
     - Or add emergency kill switch

2. **Investigate Source**
   - Check evaluation logs for patterns
   - Identify if single user or multiple users
   - Review rate limiting effectiveness
   - Check for automated/bot requests

3. **Mitigation**
   - Verify rate limiting is working (50/hour per user)
   - Check if rate limit was bypassed
   - Review IP-based rate limiting
   - Consider lowering rate limit temporarily

4. **Contact Support**
   - Contact Modal support if costs are unexpected
   - Review Modal pricing/billing
   - Check for any billing errors

5. **Prevention**
   - Verify rate limiting is properly configured
   - Set up cost alerts (see cost tracking dashboard)
   - Monitor evaluation patterns
   - Review and adjust rate limits if needed

### Recovery
- Re-enable Qwen endpoint after investigation
- Adjust rate limits if needed
- Set up better monitoring/alerts
- Document incident and lessons learned

---

## 5. Data Breach / Security Incident

### Symptoms
- Unauthorized access detected
- Unusual access patterns in logs
- Reports of data exposure
- Suspicious activity in database

### Response Steps

1. **Immediate Actions (CRITICAL)**
   - Rotate Supabase keys immediately:
     - Generate new `SUPABASE_ANON_KEY`
     - Generate new `SUPABASE_SERVICE_ROLE_KEY` (if compromised)
     - Update environment variables in Render
     - Redeploy application
   - Disable affected user accounts if identified
   - Preserve logs for investigation

2. **Assess Scope**
   - Review audit logs (`audit_logs` table)
   - Check access patterns
   - Identify what data was accessed
   - Determine affected users/institutions

3. **Notify Stakeholders**
   - Notify affected instructors immediately
   - Contact institution IT/security if applicable
   - Document incident timeline
   - Prepare incident report

4. **Investigation**
   - Review access logs
   - Check for SQL injection or other attacks
   - Review RLS policies
   - Identify attack vector

5. **Remediation**
   - Fix security vulnerabilities
   - Update access controls
   - Strengthen authentication if needed
   - Review and update RLS policies

6. **Compliance**
   - Document incident per FERPA requirements
   - Notify affected parties as required
   - Report to institution if required
   - Update security procedures

### Prevention
- Regular security audits
- Monitor access logs
- Keep dependencies updated
- Review RLS policies regularly
- Use strong authentication

---

## 6. Video Upload Failures

### Symptoms
- Video uploads timeout
- Large videos fail to upload
- Render memory errors
- Storage upload errors

### Response Steps

1. **Check Storage Status**
   - Verify Supabase Storage is operational
   - Check `evaluation-media` bucket status
   - Review storage quota/limits

2. **Verify Direct Upload**
   - Check if direct upload endpoints are working
   - Test `/api/generate-upload-url` endpoint
   - Verify presigned URL generation

3. **Check Render Resources**
   - Review Render memory usage
   - Check if 512MB limit is being exceeded
   - Review Render logs for memory errors

4. **Temporary Workaround**
   - Instructors can compress videos before upload
   - Use smaller video files
   - Fallback to Supabase Storage direct upload (if not already using)

5. **Long-term Fix**
   - Ensure direct upload is implemented (bypasses Render)
   - Consider video compression on frontend
   - Monitor file sizes and set limits

### Recovery
- Verify direct upload is working
- Test with sample large video
- Monitor upload success rates
- Update documentation if needed

---

## 7. High Error Rate

### Symptoms
- Sentry shows spike in errors
- Many users reporting issues
- Application errors in logs
- Service degradation

### Response Steps

1. **Check Sentry Dashboard**
   - Review error types and frequency
   - Identify most common errors
   - Check error trends over time

2. **Review Application Logs**
   - Check Render logs for patterns
   - Identify root cause
   - Look for recent changes

3. **Check Dependencies**
   - Verify Supabase connection
   - Check Modal/Qwen API status
   - Review external service status

4. **Mitigation**
   - Fix critical errors immediately
   - Deploy hotfix if needed
   - Add error handling for common failures
   - Consider rolling back recent changes

5. **Communication**
   - Notify users if service is affected
   - Provide status updates
   - Set expectations for resolution

### Recovery
- Verify error rate returns to normal
- Monitor for recurring issues
- Update error handling
- Document lessons learned

---

## Emergency Contacts

- **Supabase Support**: https://supabase.com/support
- **Modal Support**: Check Modal dashboard for support contact
- **Render Support**: https://render.com/docs/support
- **Sentry Alerts**: Configured in Sentry dashboard

---

## Post-Incident Review

After resolving an incident:

1. **Document Timeline**
   - When incident started
   - When detected
   - Actions taken
   - Resolution time

2. **Root Cause Analysis**
   - What caused the incident?
   - Why did it happen?
   - What could prevent it?

3. **Improvements**
   - Update procedures
   - Add monitoring/alerts
   - Improve documentation
   - Update this runbook

4. **Communication**
   - Share lessons learned with team
   - Update stakeholders if needed
   - Document for future reference

---

## Testing Incident Procedures

Regularly test these procedures:

- [ ] Verify status page links work
- [ ] Test rollback procedure in staging
- [ ] Verify key rotation process
- [ ] Test notification channels
- [ ] Review and update runbook quarterly

---

**Last Updated**: 2026-02-XX  
**Next Review**: Quarterly or after major incidents
