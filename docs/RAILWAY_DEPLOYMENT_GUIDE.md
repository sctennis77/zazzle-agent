# 🚂 Railway Deployment Guide for Clouvel

## Prerequisites

1. **Domain registered**: clouvel.ai (via Cloudflare)
2. **Railway account**: Sign up at [railway.app](https://railway.app)
3. **Environment variables**: `.env.production` file ready
4. **Railway CLI**: Will be installed automatically by script

## Quick Deployment

### 1. One-Command Deployment
```bash
./scripts/deploy-railway.sh
```

This script will:
- Install Railway CLI if needed
- Login to Railway
- Create project
- Set environment variables
- Deploy both API and frontend services
- Run health checks

### 2. Manual Deployment (if needed)

#### Install Railway CLI
```bash
npm install -g @railway/cli
```

#### Login to Railway
```bash
railway login
```

#### Create Project
```bash
railway project create clouvel
```

#### Set Environment Variables
```bash
railway variables set --file .env.production
```

#### Deploy Services
```bash
# Deploy API
railway up --service api

# Deploy frontend
cd frontend
railway up --service frontend
cd ..
```

## Environment Variables

Railway will automatically provide:
- `PORT` - Railway assigns this
- `DATABASE_URL` - If you add PostgreSQL plugin
- `REDIS_URL` - If you add Redis plugin

You need to set:
- All API keys (Stripe, OpenAI, Reddit, etc.)
- Security keys
- Email configuration
- CORS origins

## Database Setup

### Option 1: Railway PostgreSQL Plugin (Recommended)
1. Go to Railway dashboard
2. Add PostgreSQL plugin to your project
3. Railway will automatically set `DATABASE_URL`
4. Run migrations: `railway run alembic upgrade head`

### Option 2: External Database
- Set `DATABASE_URL` in environment variables
- Ensure database is accessible from Railway

## Redis Setup

### Option 1: Railway Redis Plugin
1. Add Redis plugin to your project
2. Railway will automatically set `REDIS_URL`

### Option 2: External Redis
- Set `REDIS_URL` in environment variables

## Custom Domain Setup

### 1. Configure in Railway
1. Go to Railway dashboard
2. Select your frontend service
3. Go to Settings → Domains
4. Add custom domain: `clouvel.ai`

### 2. Configure DNS (Cloudflare)
Add these records:
```
Type: CNAME
Name: @
Target: [Railway-provided URL]
```

```
Type: CNAME  
Name: www
Target: [Railway-provided URL]
```

### 3. SSL Certificate
- Railway automatically provisions SSL certificates
- Takes 5-10 minutes to activate

## Scheduler Configuration Management

### Setting Up Admin Access
The scheduler requires an admin secret for configuration management:

1. **Add ADMIN_SECRET Environment Variable**
   - Go to Railway dashboard → Your API service → Variables tab
   - Add: `ADMIN_SECRET=your-secure-secret-here`
   - **Note**: Keep this secret secure - it's found in Railway backend-api Variables UI

2. **Available Scheduler API Endpoints**
   ```bash
   # Check current scheduler status
   curl -H "X-Admin-Secret: [ADMIN_SECRET]" \
        https://your-api-url.railway.app/api/admin/scheduler/status
   
   # Update scheduler configuration
   curl -X POST \
        -H "X-Admin-Secret: [ADMIN_SECRET]" \
        "https://your-api-url.railway.app/api/admin/scheduler/config?enabled=true&interval_hours=1"
   ```

### Default Scheduler Configuration
- **Default interval**: 1 hour (creates commission every hour)
- **Default state**: Disabled (must be manually enabled)
- **Commission type**: Bronze tier random subreddit commissions

### Managing Scheduler Settings
```bash
# Enable hourly commissions
curl -X POST -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://your-api-url.railway.app/api/admin/scheduler/config?enabled=true&interval_hours=1"

# Change to daily commissions  
curl -X POST -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://your-api-url.railway.app/api/admin/scheduler/config?enabled=true&interval_hours=24"

# Disable scheduler (e.g., for overnight)
curl -X POST -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://your-api-url.railway.app/api/admin/scheduler/config?enabled=false&interval_hours=1"
```

### Quick Disable/Enable for Overnight
```bash
# To disable scheduler overnight (preserving current interval)
curl -X POST -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://backend-api-production-a9e0.up.railway.app/api/admin/scheduler/config?enabled=false&interval_hours=1"

# To re-enable in the morning
curl -X POST -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://backend-api-production-a9e0.up.railway.app/api/admin/scheduler/config?enabled=true&interval_hours=1"

# Check current status
curl -H "X-Admin-Secret: [ADMIN_SECRET]" \
     "https://backend-api-production-a9e0.up.railway.app/api/admin/scheduler/status"
```

### Scheduler Status Response
```json
{
  "scheduler": {
    "enabled": true,
    "interval_hours": 1,
    "last_run_at": "2025-07-15T20:30:00.000Z",
    "next_run_at": "2025-07-15T21:30:00.000Z"
  },
  "redis_healthy": true
}
```

## Monitoring & Health Checks

### Health Endpoints
- API: `https://your-api-url.railway.app/health`
- Frontend: `https://clouvel.ai/`
- Scheduler Status: `https://your-api-url.railway.app/api/admin/scheduler/status`

### Railway Dashboard
- Real-time logs
- Service metrics
- Deployment history
- Environment variables

## Troubleshooting

### Common Issues

#### Build Failures
```bash
# Check build logs
railway logs --service api

# Rebuild
railway up --service api
```

#### Environment Variables
```bash
# List all variables
railway variables

# Set individual variable
railway variables set KEY=value
```

#### Database Connection
```bash
# Test database connection
railway run python -c "from app.db.database import engine; print(engine.execute('SELECT 1').scalar())"
```

#### Service Not Starting
```bash
# Check service logs
railway logs --service api

# Restart service
railway service restart api
```

## Cost Optimization

### Railway Pricing
- **Free tier**: $5 credit/month
- **Pay-per-use**: Based on actual usage
- **Estimated cost**: $20-50/month for Clouvel

### Optimization Tips
1. Use smaller instances for development
2. Scale down during low usage
3. Monitor usage in Railway dashboard
4. Set up usage alerts

## Migration from Local

### Database Migration
```bash
# Export local data (if needed)
sqlite3 data/zazzle_pipeline.db ".dump" > backup.sql

# Import to Railway PostgreSQL
railway run psql $DATABASE_URL < backup.sql
```

### Environment Variables
```bash
# Export local environment
cat .env | grep -v "^#" > .env.production

# Edit .env.production with production values
# Then deploy to Railway
```

## Post-Deployment Checklist

- [ ] All services deployed successfully
- [ ] Health checks passing
- [ ] Custom domain configured
- [ ] SSL certificate active
- [ ] Database migrations run
- [ ] Environment variables set
- [ ] **ADMIN_SECRET environment variable configured**
- [ ] **Scheduler configuration verified and enabled**
- [ ] Commission workflow tested
- [ ] Stripe webhooks configured
- [ ] Monitoring alerts set up

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Railway Support**: [railway.app/support](https://railway.app/support)

---

**🎉 Ready to deploy! Run `./scripts/deploy-railway.sh` to get started!** 