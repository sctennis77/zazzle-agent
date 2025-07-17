# Promoter Agent Railway Deployment Checklist

## Pre-Deployment Setup

### 1. Reddit Account & App Configuration ✅
- [x] Created new Reddit account: u/clouvel
- [x] Created Reddit "script" application for u/clouvel
- [x] Obtained client ID and client secret
- [x] Verified script app authentication works locally

### 2. Code Implementation ✅
- [x] Updated promoter agent to use dedicated PROMOTER_AGENT_* credentials
- [x] Added validation for all 5 required environment variables
- [x] Removed fallback to REDDIT_* variables
- [x] Updated documentation files
- [x] Successfully tested locally with new credentials

## Railway Deployment Steps

### 3. Create New Railway Service
- [ ] Create new Railway service for promoter agent
- [ ] Connect to GitHub repo: `sctennis77/zazzle-agent`
- [ ] Set **Root Directory** to `/promoter_agent`
- [ ] Verify Railway auto-detects `Dockerfile` and `railway.json`

### 4. Configure Environment Variables
Add the following environment variables to the new Railway service:

#### Required Reddit Credentials (u/clouvel account)
- [ ] `PROMOTER_AGENT_CLIENT_ID` - Reddit app client ID
- [ ] `PROMOTER_AGENT_CLIENT_SECRET` - Reddit app client secret  
- [ ] `PROMOTER_AGENT_USERNAME` - `clouvel`
- [ ] `PROMOTER_AGENT_PASSWORD` - Reddit account password
- [ ] `PROMOTER_AGENT_USER_AGENT` - e.g., `"clouvel by u/clouvel"`

#### Promoter Settings
- [ ] `PROMOTER_DRY_RUN` - `false` (for production)
- [ ] `PROMOTER_DELAY_MINUTES` - `30` (minutes between scanning cycles)
- [ ] `LOG_LEVEL` - `INFO`

#### OpenAI Configuration
- [ ] `OPENAI_API_KEY` - OpenAI API key
- [ ] `OPENAI_COMMUNITY_AGENT_MODEL` - `gpt-4o-mini` (cost-optimized)

#### API Integration
- [ ] `API_BASE_URL` - `https://backend-api-production-a9e0.up.railway.app`

### 5. Deploy & Test
- [ ] Deploy the service on Railway
- [ ] Monitor deployment logs for successful startup
- [ ] Verify no credential validation errors
- [ ] Check database for new scanned posts
- [ ] Monitor Reddit account for promotional comments

### 6. Service Configuration
- [ ] Configure auto-restart on failure
- [ ] Set up health checks if needed
- [ ] Configure resource limits if necessary

## Verification Steps

### 7. Operational Testing
- [ ] Verify agent scans r/popular/hot successfully
- [ ] Confirm promotional comments include [clouvel.ai](https://clouvel.ai) links
- [ ] Check database tracking via backend API
- [ ] Monitor for authentication errors
- [ ] Verify dry-run mode disabled in production

### 8. Monitoring Setup
- [ ] Set up Railway service monitoring
- [ ] Configure alerting for service failures
- [ ] Monitor Reddit rate limits and API usage
- [ ] Track promotion success rates

## Notes
- The promoter agent runs continuously, scanning Reddit every 15 minutes
- All promotional comments will be posted by u/clouvel account
- Service includes health checks and auto-restart capabilities
- Database activity is tracked via the main backend API