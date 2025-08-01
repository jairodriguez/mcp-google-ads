# Render Deployment Strategy

This document outlines the comprehensive deployment strategy for the MCP Google Ads API on Render, designed to handle the 2-5 minute deployment window with minimal downtime.

## 🚀 Deployment Overview

### Key Components
- **Health Checks**: Continuous monitoring during deployment
- **Rollback Plan**: Emergency procedures for failed deployments
- **Monitoring**: Real-time deployment progress tracking
- **Automated Scripts**: Streamlined deployment process

## 📋 Pre-Deployment Checklist

### 1. Environment Variables
Ensure all required environment variables are set in Render:
- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CREDENTIALS_JSON` (as secret)
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
- `GOOGLE_ADS_AUTH_TYPE` (set to "service_account")
- `TEST_CUSTOMER_ID` (set to "9197949842")

### 2. Health Check Endpoints
Verify these endpoints are accessible:
- `/` - Root endpoint
- `/health/keyword-ideas` - Keyword ideas health check
- `/test/keyword-ideas` - Regression test endpoint
- `/list-accounts` - Account listing endpoint

### 3. Code Review
- ✅ All tests pass locally
- ✅ Keyword ideas safeguards are in place
- ✅ Campaign creation validation is working
- ✅ Error handling is comprehensive

## 🏥 Health Check System

### Automatic Health Checks
Render will automatically check `/health/keyword-ideas` every 30 seconds during deployment.

### Manual Health Checks
Run health checks manually:
```bash
# Run health checks
python3 deployment_strategy.py --health-check

# Or use the shell script
./health_check.sh
```

### Health Check Criteria
- **Response Time**: < 10 seconds
- **Status Code**: 200 OK
- **Content**: Valid JSON response
- **Keyword Ideas**: Functional with test parameters

## 📊 Deployment Monitoring

### Start Monitoring
```bash
# Start deployment monitoring
python3 deployment_strategy.py --monitor
```

### Monitor Progress
The monitoring system will:
1. Check all critical endpoints every 30 seconds
2. Test keyword ideas functionality
3. Test campaign creation validation
4. Track deployment elapsed time
5. Generate comprehensive reports

### Deployment Timeline
- **0-60s**: Initial deployment phase
- **60-180s**: Health check phase
- **180-300s**: Final verification phase
- **300s+**: Deployment complete

## 🔄 Rollback Strategy

### Automatic Rollback Triggers
- Health check failure rate > 20%
- Response time > 30 seconds
- Critical endpoints unavailable
- Environment variable errors

### Manual Rollback Steps
1. **Immediate Actions**:
   ```bash
   # Stop deployment monitoring
   pkill -f deployment_strategy.py
   
   # Check current deployment status
   python3 deployment_strategy.py --health-check
   ```

2. **Render Dashboard**:
   - Navigate to Render dashboard
   - Check deployment logs
   - Verify environment variables
   - Review application logs

3. **Emergency Procedures**:
   - If deployment is still in progress, wait for completion
   - Verify previous version is accessible
   - Check all environment variables
   - Test critical endpoints manually

4. **Git Rollback** (if needed):
   ```bash
   # Revert to previous commit
   git revert HEAD
   git push origin main
   ```

### Rollback Verification
After rollback:
1. Run health checks: `python3 deployment_strategy.py --health-check`
2. Test keyword ideas endpoint
3. Verify campaign creation validation
4. Check all critical endpoints

## 📈 Deployment Reports

### Generate Report
```bash
python3 deployment_strategy.py --report
```

### Report Metrics
- **Deployment Status**: Successful/Failed
- **Success Rate**: Percentage of healthy checks
- **Deployment Duration**: Total time in seconds
- **Health Check Results**: Detailed endpoint status
- **Recommendations**: Action items based on results

### Sample Report
```json
{
  "deployment_status": "successful",
  "success_rate": 95.2,
  "total_health_checks": 10,
  "healthy_checks": 9,
  "deployment_duration_seconds": 245.3,
  "recommendations": []
}
```

## 🛠️ Deployment Scripts

### Automated Deployment
```bash
# Run full deployment process
./deploy.sh
```

### Health Check Script
```bash
# Quick health check
./health_check.sh
```

### Manual Deployment Steps
1. **Push to Git**:
   ```bash
   git add .
   git commit -m "Deploy with safeguards and health checks"
   git push origin main
   ```

2. **Start Monitoring**:
   ```bash
   python3 deployment_strategy.py --monitor
   ```

3. **Verify Deployment**:
   ```bash
   python3 deployment_strategy.py --health-check
   ```

4. **Generate Report**:
   ```bash
   python3 deployment_strategy.py --report
   ```

## 🔍 Troubleshooting

### Common Issues

#### 1. Health Check Failures
**Symptoms**: Endpoints returning 500 errors
**Solutions**:
- Check environment variables in Render
- Verify Google Ads credentials
- Review application logs
- Test locally first

#### 2. Deployment Timeout
**Symptoms**: Deployment taking > 5 minutes
**Solutions**:
- Check build logs for errors
- Verify requirements.txt is correct
- Ensure all dependencies are listed
- Check for large files in repository

#### 3. Environment Variable Issues
**Symptoms**: Authentication errors
**Solutions**:
- Verify all secrets are set in Render
- Check JSON format for credentials
- Ensure developer token is valid
- Test credentials locally

#### 4. Keyword Ideas Endpoint Issues
**Symptoms**: Keyword ideas not working after deployment
**Solutions**:
- Run regression tests: `python3 test_keyword_ideas_safeguards.py`
- Check isolated service class
- Verify API version compatibility
- Test with minimal parameters

### Debug Commands
```bash
# Check deployment status
curl -f https://mcp-google-ads-vtmp.onrender.com/health/keyword-ideas

# Test keyword ideas
curl "https://mcp-google-ads-vtmp.onrender.com/keyword-ideas?customer_id=9197949842&q=test&geo=2484&lang=1003&limit=1"

# Test campaign creation validation
curl -X POST "https://mcp-google-ads-vtmp.onrender.com/create-campaign" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"123","campaign_name":"","budget_amount":-10}'
```

## 📞 Emergency Contacts

### Render Dashboard
- **URL**: https://dashboard.render.com
- **Purpose**: Check deployment status, logs, and environment variables

### Application Logs
- **Location**: Render dashboard → Service → Logs
- **Purpose**: Debug application errors and issues

### Environment Variables
- **Location**: Render dashboard → Service → Environment
- **Purpose**: Verify all required variables are set

## 🎯 Success Criteria

### Deployment Success
- ✅ All health checks pass
- ✅ Keyword ideas endpoint functional
- ✅ Campaign creation validation working
- ✅ Response times < 10 seconds
- ✅ No critical errors in logs

### Monitoring Success
- ✅ Deployment monitoring active
- ✅ Health checks running every 30s
- ✅ Rollback plan ready
- ✅ Emergency procedures documented

### Rollback Success
- ✅ Previous version accessible
- ✅ All critical endpoints working
- ✅ No data loss
- ✅ Service restored within 5 minutes

## 📝 Deployment Checklist

### Before Deployment
- [ ] All tests pass locally
- [ ] Environment variables configured
- [ ] Health check endpoints working
- [ ] Rollback plan ready
- [ ] Monitoring scripts prepared

### During Deployment
- [ ] Start monitoring immediately
- [ ] Watch health check results
- [ ] Monitor deployment logs
- [ ] Track elapsed time
- [ ] Be ready for rollback

### After Deployment
- [ ] Verify all endpoints
- [ ] Run comprehensive tests
- [ ] Generate deployment report
- [ ] Document any issues
- [ ] Update monitoring if needed

## 🔄 Continuous Improvement

### Post-Deployment Review
1. **Analyze Results**: Review deployment report
2. **Identify Issues**: Note any problems encountered
3. **Update Procedures**: Improve deployment strategy
4. **Document Lessons**: Share learnings with team
5. **Plan Improvements**: Enhance monitoring and automation

### Metrics to Track
- Deployment success rate
- Average deployment time
- Health check pass rate
- Rollback frequency
- Response time improvements

---

**Last Updated**: 2025-08-01
**Version**: 1.0
**Status**: Production Ready 