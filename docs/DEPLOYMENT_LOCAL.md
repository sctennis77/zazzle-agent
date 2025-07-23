# Local Docker Deployment Guide

This guide will help you set up the Zazzle Agent application locally using Docker for testing the commission system and validation logic.

## Prerequisites

- Docker and Docker Compose installed
- API keys for required services (see Environment Setup below)

## Quick Start

1. **Clone and setup environment:**
   ```bash
   # Copy environment template
   cp env.example .env
   
   # Edit .env with your API keys
   nano .env
   ```

2. **Deploy the application:**
   ```bash
   make deploy
   ```

3. **Access the application:**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Environment Setup

Edit your `.env` file with the following required API keys:

### Required API Keys
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Reddit API Configuration
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=your_reddit_user_agent_here

# Zazzle Affiliate Configuration
ZAZZLE_AFFILIATE_ID=your_zazzle_affiliate_id_here

# Stripe Configuration (Required for donations/commissions)
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here
STRIPE_CLI_MODE=false  # Set to true for development with Stripe CLI

# Optional: Imgur API Configuration
IMGUR_CLIENT_ID=your_imgur_client_id_here
IMGUR_CLIENT_SECRET=your_imgur_client_secret_here
```

### Getting API Keys

1. **OpenAI API Key**: Get from https://platform.openai.com/api-keys
2. **Reddit API**: Create app at https://www.reddit.com/prefs/apps
3. **Stripe API**: Get from https://dashboard.stripe.com/apikeys
4. **Zazzle Affiliate ID**: Get from your Zazzle affiliate account
5. **Imgur API**: Get from https://api.imgur.com/oauth2/addclient

## Testing the Commission System

### 1. Frontend Testing
1. Open http://localhost:5173
2. Click the "Commission" button
3. Test the three commission type variants:
   - **Sponsor**: General sponsorship
   - **Random**: Random subreddit selection
   - **Specific**: Specific subreddit and post

### 2. API Testing
Test the commission validation endpoint:
```bash
curl -X POST http://localhost:8000/api/commissions/validate \
  -H "Content-Type: application/json" \
  -d '{
    "reddit_url": "https://www.reddit.com/r/test/comments/123/test_post/",
    "commission_type": "sponsor",
    "amount_usd": 50.00,
    "message": "Test commission message"
  }'
```

### 3. Manual API Testing
Test the commission validation endpoint:
```bash
curl -X POST http://localhost:8000/api/commissions/validate \
  -H "Content-Type: application/json" \
  -d '{
    "reddit_url": "https://www.reddit.com/r/test/comments/123/test_post/",
    "commission_type": "sponsor",
    "amount_usd": 50.00,
    "message": "Test commission message"
  }'
```

## Commission Types

### 1. Sponsor Commission
- **Purpose**: General sponsorship of the project
- **Validation**: Minimal validation, accepts any amount
- **Use Case**: General support without specific content requirements

### 2. Random Commission
- **Purpose**: Generate content from a random trending subreddit
- **Validation**: Validates subreddit exists and is active
- **Use Case**: Content discovery from popular communities

### 3. Specific Commission
- **Purpose**: Generate content from a specific Reddit post
- **Validation**: Validates both subreddit and post exist
- **Use Case**: Targeted content generation from specific posts

## Validation Logic

The commission validation system includes:

1. **URL Parsing**: Extracts subreddit and post ID from Reddit URLs
2. **Subreddit Validation**: Verifies subreddit exists and is accessible
3. **Post Validation**: Verifies post exists and is accessible
4. **Amount Validation**: Ensures donation amount meets minimum requirements
5. **Message Validation**: Validates commission message format and length

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database container
   docker-compose logs database
   
   # Restart database
   docker-compose restart database
   ```

2. **API Health Check Failures**
   ```bash
   # Check API logs
   docker-compose logs api
   
   # Restart API
   docker-compose restart api
   ```

3. **Frontend Not Loading**
   ```bash
   # Check frontend logs
   docker-compose logs frontend
   
   # Restart frontend
   docker-compose restart frontend
   ```

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f task-runner

# Check service status
docker-compose ps

# Restart all services
docker-compose restart

# Stop all services
docker-compose down

# Clean up and restart
docker-compose down -v
./deploy-local.sh
```

## Architecture

The local deployment includes:

- **Database**: SQLite with persistent storage
- **API**: FastAPI backend with Stripe integration
- **Frontend**: React application with commission interface
- **Task Runner**: Processes commission requests and pipeline tasks
- **Stripe CLI**: For local webhook testing and development

## Development Notes

- Pipeline scheduling is disabled for local testing
- Stripe webhook handling is configured for local development
- Stripe CLI automatically forwards webhooks to the API for testing
- Database migrations run automatically on startup
- All services include health checks and logging

## Stripe CLI Testing

The Stripe CLI is included in the Docker setup and will:

1. **Automatically forward webhooks** from Stripe to your local API
2. **Listen for events**: `checkout.session.completed`, `payment_intent.succeeded`, `payment_intent.payment_failed`
3. **Print webhook events** to logs for debugging

To test webhooks locally:

1. **Start the application**: `make deploy`
2. **View Stripe CLI logs**: `docker-compose logs -f stripe-cli`
3. **Test payments** in the frontend - webhooks will be automatically forwarded
4. **Monitor webhook processing** in the API logs: `docker-compose logs -f api`

## Next Steps

After testing the commission system:

1. Verify all three commission types work correctly
2. Test validation logic with various inputs
3. Verify Stripe payment processing
4. Test the complete donation workflow
5. Check that pipeline tasks are created correctly

For production deployment, see the main README.md for Kubernetes deployment instructions.

## Updated Setup Steps (July 2025)

### 1. Clean Docker Deployment
- Stop all containers: `docker-compose down`
- Remove old images/volumes if needed
- Build and start: `make deploy` or `docker-compose up -d --build`

### 2. Stripe CLI Integration
- Ensure the `stripe-cli` service is running:
  ```sh
  docker-compose up -d stripe-cli
  ```
- Stripe CLI must be running for webhooks to be delivered to the API.
- If you do not see webhook events in logs, restart the container and check logs:
  ```sh
  docker-compose logs -f stripe-cli
  ```

### 3. Database Access & Troubleshooting
- The SQLite database is at `/app/data/zazzle_pipeline.db` inside containers.
- To inspect tables:
  ```sh
  docker-compose exec database apk add --no-cache sqlite
  docker-compose exec database sqlite3 /app/data/zazzle_pipeline.db ".tables"
  docker-compose exec database sqlite3 /app/data/zazzle_pipeline.db "SELECT * FROM donations;"
  docker-compose exec database sqlite3 /app/data/zazzle_pipeline.db "SELECT * FROM pipeline_tasks;"
  ```

### 4. Task Runner
- The `task-runner` service must be running to process commissions:
  ```sh
  docker-compose up -d task-runner
  ```
- If tasks are not being processed, restart the container:
  ```sh
  docker-compose restart task-runner
  ```
- To trigger the pipeline manually:
  ```sh
  docker-compose exec task-runner python -m app.main --mode full
  ```
- Monitor logs:
  ```sh
  docker-compose logs -f task-runner
  ```

### 5. Troubleshooting Checklist
- **No Stripe webhooks:** Ensure `stripe-cli` is running and forwarding to the correct API endpoint.
- **No donation in DB:** Check API logs for errors, ensure Stripe webhook is received.
- **Task not processed:** Restart `task-runner` and check logs.
- **Database not accessible:** Confirm correct path and permissions inside containers.

---

## Summary of Changes
- Stripe CLI must be running for commission/donation processing.
- Database and task runner troubleshooting steps added.
- Use correct table names (`donations`, `pipeline_tasks`).
- Restart containers as needed to resolve stuck services. 