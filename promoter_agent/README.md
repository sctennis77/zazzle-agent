# Clouvel Promoter Agent

This service scans r/popular/hot for trending content and promotes Clouvel commission opportunities by posting engaging comments with links to [clouvel.ai](https://clouvel.ai).

## Architecture

- **Service Type**: Background worker (continuous operation)
- **Platform**: Railway deployment 
- **Language**: Python 3.12
- **Dependencies**: Managed via Poetry

## Environment Variables

Required environment variables for Railway deployment:

```
# Promoter Agent Settings
PROMOTER_DRY_RUN=false                    # Set to 'true' for testing, 'false' for live

# Reddit Credentials (u/clouvel account)
PROMOTER_AGENT_CLIENT_ID=...              # Reddit app client ID for u/clouvel
PROMOTER_AGENT_CLIENT_SECRET=...          # Reddit app client secret
PROMOTER_AGENT_USERNAME=clouvel           # Reddit username
PROMOTER_AGENT_PASSWORD=...               # Reddit password
PROMOTER_AGENT_USER_AGENT=...             # User agent string (e.g., "clouvel by u/clouvel")

# OpenAI Settings
OPENAI_API_KEY=sk-...                     # OpenAI API key
OPENAI_COMMUNITY_AGENT_MODEL=gpt-4o-mini  # Cost-optimized model

# API Integration
API_BASE_URL=https://backend-api-production-a9e0.up.railway.app
LOG_LEVEL=INFO
```

## Deployment

1. Create new Railway service
2. Connect to GitHub repo `sctennis77/zazzle-agent`
3. Set **Root Directory** to `/promoter_agent`
4. Railway will auto-detect `Dockerfile` and `railway.json`
5. Configure environment variables
6. Deploy

## Operation

- Scans Reddit every 15 minutes
- Analyzes posts for artistic potential using OpenAI
- Posts promotional comments with clouvel.ai links
- Tracks activity in database via API calls
- Includes health checks and auto-restart on failure