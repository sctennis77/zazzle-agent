# Zazzle Agent Deployment Guide

This guide covers deploying the Zazzle Agent from scratch to production-ready status.

## 🔐 IMPORTANT: GitHub Secrets Setup Reminder

**If you're setting up GitHub secrets for the first time, follow these steps:**

### Step 1: Install GitHub CLI
```bash
# macOS
brew install gh

# Windows
winget install GitHub.cli

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### Step 2: Authenticate with GitHub
```bash
gh auth login
# Follow the prompts to authenticate
```

### Step 3: Set Up Repository Secrets
```bash
# Run the automated setup script (reads from your .env file)
./scripts/setup-github-secrets.sh
```

### Step 4: Verify Secrets
```bash
# List all secrets in your repository
gh secret list
```

**This will set up:**
- OPENAI_API_KEY
- REDDIT_CLIENT_ID
- REDDIT_CLIENT_SECRET
- REDDIT_USER_AGENT
- ZAZZLE_AFFILIATE_ID
- IMGUR_CLIENT_ID
- IMGUR_CLIENT_SECRET
- STRIPE_SECRET_KEY
- STRIPE_PUBLISHABLE_KEY
- STRIPE_WEBHOOK_SECRET

**Optional for advanced deployment:**
- DOCKER_USERNAME
- DOCKER_PASSWORD
- KUBE_CONFIG

---

## 💳 Stripe Integration: Local Dev to Production

### Step 1: Set Up Stripe Account

1. **Create Stripe Account**
   - Go to [stripe.com](https://stripe.com) and create an account
   - Complete account verification (business details, bank account)

2. **Get API Keys**
   - Navigate to Developers → API keys in Stripe Dashboard
   - Copy your **Publishable key** and **Secret key**
   - Note: Use test keys for development, live keys for production

### Step 2: Local Development Setup

1. **Add Stripe Keys to .env**
   ```bash
   # Copy environment template
   cp env.example .env
   
   # Edit .env and add your Stripe keys
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...  # We'll set this up next
   ```

2. **Set Up Stripe Webhook (Local)**
   ```bash
   # Install Stripe CLI
   # macOS
   brew install stripe/stripe-cli/stripe
   
   # Windows
   # Download from https://github.com/stripe/stripe-cli/releases
   
   # Linux
   # Download from https://github.com/stripe/stripe-cli/releases
   
   # Login to Stripe
   stripe login
   
   # Forward webhooks to local development
   stripe listen --forward-to localhost:8000/api/stripe/webhook
   
   # Copy the webhook secret from the output
   # Add it to your .env file as STRIPE_WEBHOOK_SECRET
   ```

3. **Test Local Integration**
   ```bash
   # Start the application
   make deploy
   
   # Test donation flow
   # 1. Open http://localhost:5173
   # 2. Click on a product
   # 3. Click "Support this Project"
   # 4. Use Stripe test card: 4242 4242 4242 4242
   ```

### Step 3: Production Deployment

1. **Switch to Live Stripe Keys**
   ```bash
   # Update .env with live keys
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_PUBLISHABLE_KEY=pk_live_...
   ```

2. **Set Up Production Webhook**
   - Go to Stripe Dashboard → Developers → Webhooks
   - Click "Add endpoint"
   - URL: `https://yourdomain.com/api/stripe/webhook`
   - Events to send: `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`
   - Copy the webhook secret and add to production environment

3. **Update GitHub Secrets**
   ```bash
   # Update secrets with production values
   gh secret set STRIPE_SECRET_KEY --body "sk_live_..."
   gh secret set STRIPE_PUBLISHABLE_KEY --body "pk_live_..."
   gh secret set STRIPE_WEBHOOK_SECRET --body "whsec_..."
   ```

4. **Deploy to Production**
   ```bash
   make deploy
   ```

### Step 4: Verify Production Integration

1. **Test Production Donation Flow**
   - Use real credit card (small amount)
   - Verify payment appears in Stripe Dashboard
   - Check webhook events in Stripe Dashboard

2. **Monitor Webhook Events**
   ```bash
   # Check webhook delivery status in Stripe Dashboard
   # Developers → Webhooks → Your endpoint → Events
   ```

---

## 🎨 Next Steps: UI/UX Improvements

### Current State
- ✅ Basic donation modal implemented
- ✅ Stripe payment processing working
- ✅ Database storage for donations

### Planned Improvements

#### 1. Enhanced Payment Modal
**Current Issues:**
- Basic styling, not visually appealing
- Limited payment method options
- No progress indicators

**Planned Enhancements:**
- Modern, branded design matching the app theme
- Multiple payment method support (cards, Apple Pay, Google Pay)
- Real-time payment status indicators
- Better error handling and user feedback
- Mobile-optimized responsive design

#### 2. Fundraising Goal Bar
**Features to Add:**
- Visual progress bar showing donation goal progress
- Current total raised vs. target amount
- Recent donors list (with privacy controls)
- Goal milestones and achievements
- Social sharing capabilities

**Implementation Plan:**
```typescript
// Example component structure
interface FundraisingGoal {
  currentAmount: number;
  targetAmount: number;
  recentDonors: Donor[];
  milestones: Milestone[];
}

// Gallery view integration
<ProductGrid>
  <FundraisingBar goal={fundraisingGoal} />
  <ProductCards />
</ProductGrid>
```

#### 3. Donation Analytics Dashboard
- Real-time donation tracking
- Donor insights and trends
- Goal progress analytics
- Export capabilities for accounting

---

## Quick Start (One Command)

For a complete deployment from scratch:

```bash
make deploy
```

This single command will:
1. ✅ Validate prerequisites (Docker, Docker Compose)
2. ✅ Validate environment variables
3. ✅ Clean up existing resources
4. ✅ Build all Docker images
5. ✅ Start all services
6. ✅ Wait for health checks
7. ✅ Run database migrations
8. ✅ Test the deployment
9. ✅ Run initial pipeline
10. ✅ Display deployment information

## Prerequisites

- Docker and Docker Compose installed
- Environment variables configured (see `env.example`)
- Stripe account and API keys (for donation features)

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and fill in your API keys:
   - OpenAI API key
   - Reddit API credentials
   - Zazzle affiliate ID
   - Imgur API credentials
   - **Stripe API keys (for donations)**

## GitHub Secrets Management

For automated deployment with GitHub Actions, you can manage secrets securely:

### Option 1: Automated Setup (Recommended)

```bash
# Install GitHub CLI first: https://cli.github.com/
gh auth login

# Run the automated setup script
./scripts/setup-github-secrets.sh
```

This script will:
- ✅ Read secrets from your `.env` file
- ✅ Validate all required secrets are present
- ✅ Set them as GitHub repository secrets
- ✅ Handle optional secrets (Docker Hub, Kubernetes)

### Option 2: Manual Setup

1. Go to your GitHub repository: Settings → Secrets and variables → Actions
2. Add the following secrets:
   ```
   OPENAI_API_KEY=your_openai_api_key
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USER_AGENT=your_reddit_user_agent
   ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id
   IMGUR_CLIENT_ID=your_imgur_client_id
   IMGUR_CLIENT_SECRET=your_imgur_client_secret
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
   STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
   ```

### Optional Secrets for Advanced Deployment

For Docker Hub and Kubernetes deployment, also add:
```
DOCKER_USERNAME=your_docker_username
DOCKER_PASSWORD=your_docker_password
KUBE_CONFIG=base64_encoded_kubeconfig
```

## Deployment Options

### Standard Deployment
```bash
make deploy
```

### Clean Deployment (removes old images)
```bash
make deploy-clean
```

### Quick Deployment (skips initial pipeline)
```bash
make deploy-quick
```

### Manual Step-by-Step
```bash
# 1. Build images
docker-compose build --parallel

# 2. Start services
docker-compose up -d

# 3. Wait for health checks
docker-compose ps

# 4. Run pipeline manually
docker-compose exec pipeline python app/main.py --mode full
```

## Service Management

### Check Status
```bash
make deployment-status
```

### View Logs
```bash
# All services
make show-logs

# Specific service
make show-logs-api
make show-logs-pipeline
make show-logs-frontend
```

### Run Pipeline Manually
```bash
make run-pipeline
```

### Validate Deployment
```bash
make validate-deployment
```

### Stop Services
```bash
docker-compose down
```

## Service URLs

After deployment, access:

- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Production Considerations

### Environment Variables
Ensure all required environment variables are set:
- `OPENAI_API_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `ZAZZLE_AFFILIATE_ID`
- `IMGUR_CLIENT_ID`
- `IMGUR_CLIENT_SECRET`

### Logging
Logs are automatically rotated:
- Max file size: 10MB
- Max files: 3 per service
- Location: Docker logs

### Health Checks
All services include health checks:
- Database: SQLite connectivity
- API: HTTP health endpoint
- Frontend: HTTP accessibility
- Pipeline/Interaction: Container status

### Scheduling
- Pipeline runs every 6 hours by default
- Interaction agent runs every 2 hours by default
- Schedules can be modified in `.env`

### Data Persistence
- Database is persisted in `./data/`
- Generated images are stored in containers
- Consider backing up the `data/` directory

## Troubleshooting

### Common Issues

1. **Environment variables missing**
   ```bash
   # Check if .env exists and has all required variables
   cat .env
   ```

2. **Services not starting**
   ```bash
   # Check logs
   docker-compose logs
   
   # Check status
   docker-compose ps
   ```

3. **Health checks failing**
   ```bash
   # Wait longer for services to start
   # Check individual service logs
   docker-compose logs api
   ```

4. **Pipeline not running**
   ```bash
   # Run manually to see errors
   docker-compose exec pipeline python app/main.py --mode full
   ```

### Debug Commands

```bash
# Check container status
docker-compose ps

# View recent logs
docker-compose logs --tail=50

# Execute commands in containers
docker-compose exec api python -c "import app; print('API OK')"
docker-compose exec pipeline python -c "import app; print('Pipeline OK')"

# Check database
docker-compose exec database sqlite3 /app/data/zazzle_pipeline.db ".tables"
```

## Monitoring

### Health Monitoring
```bash
# Check all services
make validate-deployment

# Monitor logs in real-time
make show-logs
```

### Performance Monitoring
- API response times via health endpoint
- Pipeline execution logs
- Database size and performance
- Docker resource usage

## Backup and Recovery

### Database Backup
```bash
# Create backup
cp data/zazzle_pipeline.db data/zazzle_pipeline.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore backup
cp data/zazzle_pipeline.db.backup.20241201_120000 data/zazzle_pipeline.db
```

### Full Backup
```bash
# Backup entire data directory
tar -czf backup-$(date +%Y%m%d_%H%M%S).tar.gz data/
```

## Scaling

### Horizontal Scaling
For production, consider:
- Using PostgreSQL instead of SQLite
- Adding load balancers
- Using Kubernetes for orchestration
- Implementing proper monitoring and alerting

### Resource Limits
Monitor and adjust:
- CPU and memory limits in Docker Compose
- Database connection pools
- API rate limits
- OpenAI API quotas

## Security

### Best Practices
- Use strong, unique API keys
- Rotate credentials regularly
- Monitor API usage
- Implement proper logging
- Use HTTPS in production
- Restrict network access

### Environment Security
- Never commit `.env` files
- Use secrets management in production
- Implement proper access controls
- Monitor for suspicious activity

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Validate environment configuration
4. Test individual components
5. Check service health status 