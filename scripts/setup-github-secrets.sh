#!/bin/bash

# GitHub Secrets Setup Script for Zazzle Agent
# This script helps you set up GitHub repository secrets for automated deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if gh CLI is installed
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed."
        echo "Please install it first: https://cli.github.com/"
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gh auth status &> /dev/null; then
        error "You are not authenticated with GitHub CLI."
        echo "Please run: gh auth login"
        exit 1
    fi
    
    success "GitHub CLI is ready"
}

# Get repository name
get_repo_name() {
    if [ -d .git ]; then
        REPO_NAME=$(git remote get-url origin | sed 's/.*github.com[:/]\([^/]*\/[^/]*\).*/\1/' | sed 's/\.git$//')
        echo "Detected repository: $REPO_NAME"
    else
        error "Not in a git repository. Please run this script from your project root."
        exit 1
    fi
}

# Read secrets from .env file
read_env_secrets() {
    if [ ! -f .env ]; then
        error ".env file not found. Please create one first using env.example"
        exit 1
    fi
    
    log "Reading secrets from .env file..."
    
    # Source the .env file
    set -a
    source .env
    set +a
    
    # Check if all required secrets are present
    local required_vars=(
        "OPENAI_API_KEY"
        "REDDIT_CLIENT_ID"
        "REDDIT_CLIENT_SECRET"
        "REDDIT_USER_AGENT"
        "ZAZZLE_AFFILIATE_ID"
        "IMGUR_CLIENT_ID"
        "IMGUR_CLIENT_SECRET"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables in .env:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please add these to your .env file and try again."
        exit 1
    fi
    
    success "All required secrets found in .env"
}

# Set GitHub secrets
set_github_secrets() {
    log "Setting GitHub repository secrets..."
    
    # Set each secret
    gh secret set OPENAI_API_KEY --body "$OPENAI_API_KEY" --repo "$REPO_NAME"
    gh secret set REDDIT_CLIENT_ID --body "$REDDIT_CLIENT_ID" --repo "$REPO_NAME"
    gh secret set REDDIT_CLIENT_SECRET --body "$REDDIT_CLIENT_SECRET" --repo "$REPO_NAME"
    gh secret set REDDIT_USER_AGENT --body "$REDDIT_USER_AGENT" --repo "$REPO_NAME"
    gh secret set ZAZZLE_AFFILIATE_ID --body "$ZAZZLE_AFFILIATE_ID" --repo "$REPO_NAME"
    gh secret set IMGUR_CLIENT_ID --body "$IMGUR_CLIENT_ID" --repo "$REPO_NAME"
    gh secret set IMGUR_CLIENT_SECRET --body "$IMGUR_CLIENT_SECRET" --repo "$REPO_NAME"
    
    success "All secrets set successfully"
}

# Set optional secrets
set_optional_secrets() {
    log "Setting optional secrets..."
    
    # Docker Hub credentials (if provided)
    if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
        gh secret set DOCKER_USERNAME --body "$DOCKER_USERNAME" --repo "$REPO_NAME"
        gh secret set DOCKER_PASSWORD --body "$DOCKER_PASSWORD" --repo "$REPO_NAME"
        success "Docker Hub secrets set"
    else
        warning "DOCKER_USERNAME and DOCKER_PASSWORD not found in .env"
        echo "Add these to .env if you want to push to Docker Hub:"
        echo "DOCKER_USERNAME=your_docker_username"
        echo "DOCKER_PASSWORD=your_docker_password"
    fi
    
    # Kubernetes config (if provided)
    if [ -n "$KUBE_CONFIG" ]; then
        gh secret set KUBE_CONFIG --body "$KUBE_CONFIG" --repo "$REPO_NAME"
        success "Kubernetes config set"
    else
        warning "KUBE_CONFIG not found in .env"
        echo "Add this to .env if you want to deploy to Kubernetes:"
        echo "KUBE_CONFIG=$(kubectl config view --raw | base64 -w 0)"
    fi
}

# List current secrets
list_secrets() {
    log "Current GitHub secrets:"
    gh secret list --repo "$REPO_NAME"
}

# Main function
main() {
    echo "🔐 GitHub Secrets Setup for Zazzle Agent"
    echo "========================================="
    echo ""
    
    check_gh_cli
    get_repo_name
    read_env_secrets
    
    echo ""
    echo "This will set the following secrets in repository: $REPO_NAME"
    echo "  • OPENAI_API_KEY"
    echo "  • REDDIT_CLIENT_ID"
    echo "  • REDDIT_CLIENT_SECRET"
    echo "  • REDDIT_USER_AGENT"
    echo "  • ZAZZLE_AFFILIATE_ID"
    echo "  • IMGUR_CLIENT_ID"
    echo "  • IMGUR_CLIENT_SECRET"
    echo ""
    
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    
    set_github_secrets
    set_optional_secrets
    
    echo ""
    success "GitHub secrets setup completed!"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Push your code to trigger the GitHub Actions workflow"
    echo "  2. Go to Actions tab to monitor deployment"
    echo "  3. Use 'workflow_dispatch' to manually trigger deployments"
    echo ""
    echo "🔍 To verify secrets:"
    list_secrets
}

# Run main function
main "$@" 