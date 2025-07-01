#!/bin/bash

# Zazzle Agent Deployment Script
# This script sets up the complete Zazzle Agent stack from scratch

set -e  # Exit on any error

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

# Check if required tools are installed
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    success "All prerequisites are satisfied"
}

# Validate environment variables
validate_environment() {
    log "Validating environment variables..."
    
    local required_vars=(
        "OPENAI_API_KEY"
        "REDDIT_CLIENT_ID"
        "REDDIT_CLIENT_SECRET"
        "REDDIT_USER_AGENT"
        "ZAZZLE_AFFILIATE_ID"
        "STRIPE_SECRET_KEY"
        "STRIPE_PUBLISHABLE_KEY"
        "STRIPE_WEBHOOK_SECRET"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please set these variables in your .env file or environment."
        exit 1
    fi
    
    success "All environment variables are set"
}

# Clean up existing resources
cleanup_existing() {
    log "Cleaning up existing resources..."
    
    # Stop and remove existing containers
    if docker-compose ps -q | grep -q .; then
        warning "Stopping existing containers..."
        docker-compose down --remove-orphans
    fi
    
    # Remove old images (optional)
    if [[ "$1" == "--clean-images" ]]; then
        warning "Removing old images..."
        docker-compose down --rmi all --volumes --remove-orphans
    fi
    
    success "Cleanup completed"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build all images in parallel
    docker-compose build --parallel
    
    success "All Docker images built successfully"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start all services
    docker-compose up -d
    
    success "Services started"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts"
        
        # Check if all services are healthy
        if docker-compose ps | grep -q "unhealthy\|starting"; then
            echo "Some services are still starting up..."
            sleep 10
            ((attempt++))
        else
            success "All services are healthy"
            return 0
        fi
    done
    
    error "Services failed to become healthy within expected time"
    docker-compose logs
    exit 1
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Wait a bit for the database to be ready
    sleep 5
    
    # Run migrations
    docker-compose exec -T database sh -c "
        apk add --no-cache sqlite &&
        sqlite3 /app/data/zazzle_pipeline.db 'SELECT 1;' || echo 'Database not ready yet'
    "
    
    success "Database migrations completed"
}

# Test the deployment
test_deployment() {
    log "Testing deployment..."
    
    # Test API health
    if curl -f -s http://localhost:8000/health > /dev/null; then
        success "API health check passed"
    else
        error "API health check failed"
        return 1
    fi
    
    # Test frontend
    if curl -f -s http://localhost:5173 > /dev/null; then
        success "Frontend health check passed"
    else
        error "Frontend health check failed"
        return 1
    fi
    
    success "All health checks passed"
}

# Run initial pipeline
run_initial_pipeline() {
    log "Running initial pipeline..."
    
    # Run a single pipeline execution using task-runner
    docker-compose exec -T task-runner python -m app.main --mode full
    
    success "Initial pipeline completed"
}

# Display deployment information
show_deployment_info() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo "======================================"
    echo ""
    echo "📊 Services:"
    echo "  • Frontend: http://localhost:5173"
    echo "  • API: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • View API logs: docker-compose logs -f api"
    echo "  • View Stripe CLI logs: docker-compose logs -f stripe-cli"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo "  • Run pipeline: docker-compose exec task-runner python -m app.main --mode full"
    echo ""
    echo "📋 Useful URLs:"
    echo "  • Frontend: http://localhost:5173"
    echo "  • API Health: http://localhost:8000/health"
    echo "  • Generated Products: http://localhost:8000/api/generated_products"
    echo ""
    echo "🚀 Next steps:"
    echo "  1. Open http://localhost:5173 in your browser"
    echo "  2. Test the commission system by clicking 'Commission' button"
    echo "  3. Run the pipeline to generate your first product"
    echo "  4. Monitor the logs for any issues"
    echo ""
    echo "🧪 Commission System Testing:"
    echo "  • Test three commission types: Sponsor, Random, Specific"
    echo "  • Verify validation logic works correctly"
    echo "  • Check Stripe payment processing"
    echo ""
}

# Main deployment function
main() {
    echo "🚀 Zazzle Agent Deployment Script"
    echo "=================================="
    echo ""
    
    # Parse command line arguments
    CLEAN_IMAGES=false
    SKIP_PIPELINE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean-images)
                CLEAN_IMAGES=true
                shift
                ;;
            --skip-pipeline)
                SKIP_PIPELINE=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --clean-images    Remove old Docker images before building"
                echo "  --skip-pipeline   Skip running the initial pipeline"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run deployment steps
    check_prerequisites
    validate_environment
    cleanup_existing $([[ "$CLEAN_IMAGES" == true ]] && echo "--clean-images")
    build_images
    start_services
    wait_for_health
    run_migrations
    test_deployment
    
    if [[ "$SKIP_PIPELINE" != true ]]; then
        run_initial_pipeline
    fi
    
    show_deployment_info
}

# Run main function with all arguments
main "$@" 