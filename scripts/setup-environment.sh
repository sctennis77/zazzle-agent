#!/bin/bash

# Zazzle Agent Environment Setup Script
# This script helps set up the environment for the Zazzle Agent

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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

# Check if .env file exists
check_env_file() {
    if [[ ! -f .env ]]; then
        warning ".env file not found. Creating from template..."
        cp env.example .env
        success ".env file created from template"
        echo ""
        echo "📝 Please edit .env file with your actual API keys:"
        echo "   nano .env"
        echo ""
        echo "Required variables:"
        echo "  • OPENAI_API_KEY"
        echo "  • REDDIT_CLIENT_ID"
        echo "  • REDDIT_CLIENT_SECRET"
        echo "  • REDDIT_USER_AGENT"
        echo "  • ZAZZLE_AFFILIATE_ID"
        echo "  • IMGUR_CLIENT_ID"
        echo "  • IMGUR_CLIENT_SECRET"
        echo ""
        return 1
    else
        success ".env file exists"
        return 0
    fi
}

# Validate environment variables
validate_env_vars() {
    log "Validating environment variables..."
    
    # Source the .env file
    if [[ -f .env ]]; then
        export $(grep -v '^#' .env | xargs)
    fi
    
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
    local invalid_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        elif [[ "${!var}" == "your_*_here" ]]; then
            invalid_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  • $var"
        done
        return 1
    fi
    
    if [[ ${#invalid_vars[@]} -gt 0 ]]; then
        error "Invalid environment variables (still using placeholder values):"
        for var in "${invalid_vars[@]}"; do
            echo "  • $var"
        done
        return 1
    fi
    
    success "All environment variables are properly configured"
    return 0
}

# Test API connections
test_api_connections() {
    log "Testing API connections..."
    
    # Source the .env file
    if [[ -f .env ]]; then
        export $(grep -v '^#' .env | xargs)
    fi
    
    # Test OpenAI API
    log "Testing OpenAI API..."
    if curl -s -H "Authorization: Bearer $OPENAI_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}]}' \
        https://api.openai.com/v1/chat/completions > /dev/null 2>&1; then
        success "OpenAI API connection successful"
    else
        error "OpenAI API connection failed"
        return 1
    fi
    
    # Test Reddit API
    log "Testing Reddit API..."
    if curl -s -H "User-Agent: $REDDIT_USER_AGENT" \
        https://www.reddit.com/api/v1/access_token \
        -d grant_type=client_credentials \
        -u "$REDDIT_CLIENT_ID:$REDDIT_CLIENT_SECRET" > /dev/null 2>&1; then
        success "Reddit API connection successful"
    else
        error "Reddit API connection failed"
        return 1
    fi
    
    success "All API connections successful"
    return 0
}

# Setup development environment
setup_dev_environment() {
    log "Setting up development environment..."
    
    # Check if Poetry is installed
    if ! command -v poetry &> /dev/null; then
        warning "Poetry not found. Installing..."
        curl -sSL https://install.python-poetry.org | python3 -
        success "Poetry installed"
    else
        success "Poetry is already installed"
    fi
    
    # Install dependencies
    log "Installing Python dependencies..."
    poetry install
    success "Python dependencies installed"
    
    # Install frontend dependencies
    log "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    success "Frontend dependencies installed"
    
    # Create data directory
    mkdir -p data
    success "Data directory created"
}

# Setup production environment
setup_production_environment() {
    log "Setting up production environment..."
    
    # Create data directory
    mkdir -p data
    success "Data directory created"
    
    # Set proper permissions
    chmod 755 data
    success "Permissions set"
}

# Main function
main() {
    echo "🔧 Zazzle Agent Environment Setup"
    echo "=================================="
    echo ""
    
    # Parse command line arguments
    SETUP_TYPE="dev"
    SKIP_TESTS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --production)
                SETUP_TYPE="production"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --production    Setup for production environment"
                echo "  --skip-tests    Skip API connection tests"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run setup steps
    if ! check_env_file; then
        echo ""
        echo "Please edit the .env file with your API keys and run this script again."
        exit 1
    fi
    
    if ! validate_env_vars; then
        echo ""
        echo "Please fix the environment variables and run this script again."
        exit 1
    fi
    
    if [[ "$SKIP_TESTS" != true ]]; then
        if ! test_api_connections; then
            echo ""
            echo "Please check your API keys and network connection."
            exit 1
        fi
    fi
    
    if [[ "$SETUP_TYPE" == "production" ]]; then
        setup_production_environment
    else
        setup_dev_environment
    fi
    
    echo ""
    success "Environment setup completed successfully!"
    echo ""
    echo "🚀 Next steps:"
    if [[ "$SETUP_TYPE" == "production" ]]; then
        echo "  1. Run: make deploy"
        echo "  2. Monitor: make deployment-status"
        echo "  3. View logs: make show-logs"
    else
        echo "  1. Run tests: make test"
        echo "  2. Start API: make run-api"
        echo "  3. Start frontend: make frontend-dev"
        echo "  4. Or deploy with Docker: make deploy"
    fi
    echo ""
}

# Run main function with all arguments
main "$@" 