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

**Optional for advanced deployment:**
- DOCKER_USERNAME
- DOCKER_PASSWORD
- KUBE_CONFIG

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