#!/bin/bash

# Production Deployment Script for Clouvel
# Choose your platform and uncomment the relevant section

set -e

echo "🚀 Starting Clouvel Production Deployment..."

# Configuration
PROJECT_NAME="clouvel"
DOMAIN="clouvel.ai"
REGISTRY_URL=""  # Set based on platform

# Environment check
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "Please create .env.production with your production environment variables"
    exit 1
fi

# Build images
echo "📦 Building Docker images..."
docker build -f Dockerfile.api -t ${PROJECT_NAME}-api:latest .
docker build -f frontend/Dockerfile.frontend -t ${PROJECT_NAME}-frontend:latest ./frontend

# Tag for registry
echo "🏷️  Tagging images for registry..."
docker tag ${PROJECT_NAME}-api:latest ${REGISTRY_URL}/${PROJECT_NAME}-api:latest
docker tag ${PROJECT_NAME}-frontend:latest ${REGISTRY_URL}/${PROJECT_NAME}-frontend:latest

# Push to registry
echo "⬆️  Pushing images to registry..."
docker push ${REGISTRY_URL}/${PROJECT_NAME}-api:latest
docker push ${REGISTRY_URL}/${PROJECT_NAME}-frontend:latest

echo "✅ Images pushed successfully!"

# Platform-specific deployment
echo "🌐 Choose your deployment platform:"
echo "1) Railway (simplest)"
echo "2) DigitalOcean (balanced)"
echo "3) Google Cloud Platform (enterprise)"
echo "4) AWS (comprehensive)"

read -p "Enter your choice (1-4): " PLATFORM

case $PLATFORM in
    1)
        echo "🚂 Deploying to Railway..."
        # Railway deployment
        # railway login
        # railway up
        echo "⚠️  Railway deployment requires manual setup in Railway dashboard"
        echo "1. Connect your GitHub repo"
        # 2. Set environment variables
        # 3. Deploy
        ;;
    2)
        echo "🌊 Deploying to DigitalOcean..."
        # DigitalOcean deployment
        # doctl kubernetes cluster kubeconfig save ${PROJECT_NAME}-cluster
        # kubectl apply -f k8s/
        echo "⚠️  DigitalOcean deployment requires:"
        echo "1. doctl CLI installed and authenticated"
        echo "2. Kubernetes cluster created"
        echo "3. Container registry configured"
        ;;
    3)
        echo "☁️  Deploying to Google Cloud Platform..."
        # GCP deployment
        # gcloud container clusters get-credentials ${PROJECT_NAME}-cluster
        # kubectl apply -f k8s/
        echo "⚠️  GCP deployment requires:"
        echo "1. gcloud CLI installed and authenticated"
        echo "2. GKE cluster created"
        echo "3. Artifact Registry configured"
        ;;
    4)
        echo "☁️  Deploying to AWS..."
        # AWS deployment
        # aws eks update-kubeconfig --name ${PROJECT_NAME}-cluster
        # kubectl apply -f k8s/
        echo "⚠️  AWS deployment requires:"
        echo "1. AWS CLI installed and configured"
        echo "2. EKS cluster created"
        echo "3. ECR repository configured"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo "🎉 Deployment initiated!"
echo "📋 Next steps:"
echo "1. Configure domain DNS"
echo "2. Set up SSL certificate"
echo "3. Configure monitoring"
echo "4. Test commission workflow"
echo "5. Go live!"

echo "🔗 Your app will be available at: https://${DOMAIN}" 