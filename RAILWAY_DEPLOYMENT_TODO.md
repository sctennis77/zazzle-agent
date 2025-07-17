# Railway Deployment TODO - Promoter Agent

## 🎯 Objective
Deploy the Clouvel Promoter Agent (u/clouvel) to Railway as a separate service that scans r/popular/hot every 30 minutes and promotes commission opportunities.

## ✅ Completed Steps
- [x] Created new Reddit account: u/clouvel
- [x] Created Reddit "script" application for u/clouvel
- [x] Implemented dedicated PROMOTER_AGENT_* credentials (no fallbacks)
- [x] Restructured promoter agent into `/promoter_agent/` subdirectory
- [x] Set default scanning interval to 30 minutes
- [x] Successfully tested locally with new credentials
- [x] Updated all documentation and environment templates
- [x] All backend tests passing
- [x] Code committed and pushed to main branch

## 🚀 Remaining Railway Deployment Steps

### 1. Create New Railway Service
- [ ] Go to Railway dashboard
- [ ] Create new service for promoter agent
- [ ] Connect to GitHub repo: `sctennis77/zazzle-agent`
- [ ] **CRITICAL**: Set **Root Directory** to `/promoter_agent`
- [ ] Verify Railway auto-detects `Dockerfile` and `railway.json`

### 2. Configure Environment Variables in Railway
Add these exact environment variables to the new Railway service:

#### Required Reddit Credentials (u/clouvel account)
- [ ] `PROMOTER_AGENT_CLIENT_ID` - Reddit app client ID from script app
- [ ] `PROMOTER_AGENT_CLIENT_SECRET` - Reddit app client secret from script app
- [ ] `PROMOTER_AGENT_USERNAME` - `clouvel`
- [ ] `PROMOTER_AGENT_PASSWORD` - Reddit account password for u/clouvel
- [ ] `PROMOTER_AGENT_USER_AGENT` - `"clouvel by u/clouvel"`

#### Promoter Configuration
- [ ] `PROMOTER_DRY_RUN` - `false` (for live production)
- [ ] `PROMOTER_DELAY_MINUTES` - `30` (scan every 30 minutes)
- [ ] `LOG_LEVEL` - `INFO`

#### OpenAI Integration
- [ ] `OPENAI_API_KEY` - Same OpenAI API key as main backend
- [ ] `OPENAI_COMMUNITY_AGENT_MODEL` - `gpt-4o-mini` (cost-optimized)

#### Backend API Integration
- [ ] `API_BASE_URL` - `https://backend-api-production-a9e0.up.railway.app`

### 3. Deploy and Initial Testing
- [ ] Deploy the service on Railway
- [ ] Monitor deployment logs for successful startup
- [ ] Verify no credential validation errors in logs
- [ ] Check that service starts without errors

### 4. Operational Verification
- [ ] Wait for first scan cycle (up to 30 minutes)
- [ ] Check backend database for new `agent_scanned_posts` entries
- [ ] Verify Reddit account u/clouvel shows recent activity
- [ ] Confirm promotional comments include [clouvel.ai](https://clouvel.ai) links
- [ ] Monitor for any authentication or rate limiting errors

### 5. Production Monitoring Setup
- [ ] Configure Railway service monitoring/alerts
- [ ] Set up health checks if needed
- [ ] Monitor Reddit API rate limits
- [ ] Track promotion success rates via backend API

## 📋 Environment Variables Reference

Copy these exact values to Railway:

```bash
# Reddit Credentials
PROMOTER_AGENT_CLIENT_ID=[from reddit script app]
PROMOTER_AGENT_CLIENT_SECRET=[from reddit script app]
PROMOTER_AGENT_USERNAME=clouvel
PROMOTER_AGENT_PASSWORD=[reddit password]
PROMOTER_AGENT_USER_AGENT=clouvel by u/clouvel

# Configuration
PROMOTER_DRY_RUN=false
PROMOTER_DELAY_MINUTES=30
LOG_LEVEL=INFO

# OpenAI
OPENAI_API_KEY=[same as backend]
OPENAI_COMMUNITY_AGENT_MODEL=gpt-4o-mini

# Backend Integration
API_BASE_URL=https://backend-api-production-a9e0.up.railway.app
```

## 🔍 Troubleshooting

### If deployment fails:
1. Check Railway logs for credential validation errors
2. Verify Root Directory is set to `/promoter_agent`
3. Confirm all 5 PROMOTER_AGENT_* variables are set
4. Test Reddit credentials manually if needed

### If agent doesn't scan:
1. Check logs for Reddit API errors
2. Verify PROMOTER_DRY_RUN=false
3. Wait full 30 minutes for first cycle
4. Check backend database for activity

### If comments aren't posting:
1. Verify Reddit app is configured as "script" type
2. Check for Reddit rate limiting
3. Confirm PROMOTER_DRY_RUN=false

## 📝 Success Criteria
- [ ] Service deploys without errors
- [ ] Agent scans r/popular/hot every 30 minutes
- [ ] Comments posted by u/clouvel include [clouvel.ai](https://clouvel.ai) links
- [ ] Database tracks scanned posts via backend API
- [ ] No authentication or credential errors in logs

## 🎉 Post-Deployment
Once successful, the promoter agent will:
- Run continuously 24/7
- Scan Reddit every 30 minutes
- Promote qualified posts with witty comments
- Track all activity in the main backend database
- Operate independently of the main backend service

---
**Next Session**: Continue from step 1 to deploy the Railway service.