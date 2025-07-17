#!/bin/bash

# Railway Deployment Script for Clouvel
set -e

echo "🚂 Starting Railway Deployment for Clouvel..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Check if logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
fi

# Create project if it doesn't exist
if ! railway project &> /dev/null; then
    echo "📁 Creating new Railway project..."
    railway project create clouvel
fi

# Set up environment variables
echo "🔧 Setting up environment variables..."
if [ -f ".env.production" ]; then
    echo "📝 Loading environment variables from .env.production..."
    railway variables set --file .env.production
else
    echo "⚠️  .env.production not found. Please create it first!"
    echo "Copy env.production.template to .env.production and fill in your values."
    exit 1
fi

# Deploy API service
echo "🚀 Deploying API service..."
railway up --service api

# Deploy frontend service
echo "🎨 Deploying frontend service..."
cd frontend
railway up --service frontend
cd ..

# Deploy promoter agent service
echo "👑 Deploying promoter agent service..."
railway up --service promoter-agent

# Get deployment URLs
echo "🔗 Getting deployment URLs..."
API_URL=$(railway status --service api --json | jq -r '.url')
FRONTEND_URL=$(railway status --service frontend --json | jq -r '.url')

echo "✅ Deployment complete!"
echo "🔗 API URL: $API_URL"
echo "🔗 Frontend URL: $FRONTEND_URL"

# Health check
echo "🏥 Running health checks..."
sleep 10
curl -f "$API_URL/health" || echo "⚠️  API health check failed"
curl -f "$FRONTEND_URL" || echo "⚠️  Frontend health check failed"

echo "🎉 Railway deployment successful!"
echo "📋 Next steps:"
echo "1. Configure custom domain (clouvel.ai) in Railway dashboard"
echo "2. Update DNS records to point to Railway"
echo "3. Test commission workflow"
echo "4. Switch Stripe to live mode" 