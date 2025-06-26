#!/bin/bash

# Zazzle Agent Health Monitor
# This script monitors the health of all services and provides detailed status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Check Docker services
check_docker_services() {
    echo "🐳 Docker Services Status"
    echo "========================"
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose not found"
        return 1
    fi
    
    # Check if services are running
    if ! docker-compose ps -q | grep -q .; then
        error "No Docker services are running"
        echo ""
        echo "To start services:"
        echo "  make deploy"
        echo "  or"
        echo "  docker-compose up -d"
        return 1
    fi
    
    # Show service status
    docker-compose ps
    
    echo ""
    
    # Check each service individually
    local services=("api" "frontend" "pipeline" "interaction" "database")
    local all_healthy=true
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            if docker-compose ps "$service" | grep -q "healthy"; then
                success "$service: Running and Healthy"
            else
                warning "$service: Running but Health Check Pending"
                all_healthy=false
            fi
        else
            error "$service: Not Running"
            all_healthy=false
        fi
    done
    
    echo ""
    return $([ "$all_healthy" = true ] && echo 0 || echo 1)
}

# Check API endpoints
check_api_endpoints() {
    echo "🔌 API Endpoints Status"
    echo "======================="
    
    local endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8000/api/generated_products"
        "http://localhost:8000/docs"
    )
    
    local all_working=true
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null 2>&1; then
            success "$endpoint: Accessible"
        else
            error "$endpoint: Not Accessible"
            all_working=false
        fi
    done
    
    echo ""
    return $([ "$all_working" = true ] && echo 0 || echo 1)
}

# Check frontend
check_frontend() {
    echo "🌐 Frontend Status"
    echo "=================="
    
    if curl -f -s http://localhost:5173 > /dev/null 2>&1; then
        success "Frontend: Accessible at http://localhost:5173"
    else
        error "Frontend: Not Accessible"
        return 1
    fi
    
    echo ""
    return 0
}

# Check database
check_database() {
    echo "🗄️  Database Status"
    echo "=================="
    
    # Check if database file exists
    if [[ -f "data/zazzle_pipeline.db" ]]; then
        success "Database file exists"
        
        # Check database size
        local size=$(du -h data/zazzle_pipeline.db | cut -f1)
        info "Database size: $size"
        
        # Check if database is accessible from container
        if docker-compose exec -T database sqlite3 /app/data/zazzle_pipeline.db "SELECT COUNT(*) FROM reddit_posts;" 2>/dev/null; then
            success "Database is accessible from container"
        else
            warning "Database may not be accessible from container"
        fi
    else
        error "Database file not found"
        return 1
    fi
    
    echo ""
    return 0
}

# Check recent logs
check_recent_logs() {
    echo "📋 Recent Logs (Last 10 lines)"
    echo "=============================="
    
    # Show recent logs from all services
    docker-compose logs --tail=10
    
    echo ""
}

# Check resource usage
check_resource_usage() {
    echo "💾 Resource Usage"
    echo "================="
    
    # Check Docker resource usage
    echo "Docker containers:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    echo ""
    
    # Check disk usage
    echo "Disk usage:"
    df -h . | head -2
    
    echo ""
}

# Check environment variables
check_environment() {
    echo "🔧 Environment Check"
    echo "==================="
    
    if [[ ! -f .env ]]; then
        error ".env file not found"
        return 1
    fi
    
    success ".env file exists"
    
    # Check required environment variables
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
        if grep -q "^${var}=" .env; then
            local value=$(grep "^${var}=" .env | cut -d'=' -f2)
            if [[ "$value" == "your_*_here" || -z "$value" ]]; then
                warning "$var: Not configured (using placeholder)"
                missing_vars+=("$var")
            else
                success "$var: Configured"
            fi
        else
            error "$var: Missing"
            missing_vars+=("$var")
        fi
    done
    
    echo ""
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        warning "Some environment variables need attention"
        return 1
    fi
    
    return 0
}

# Check pipeline status
check_pipeline_status() {
    echo "🚀 Pipeline Status"
    echo "=================="
    
    # Check if pipeline has run recently
    if docker-compose exec -T database sqlite3 /app/data/zazzle_pipeline.db "SELECT COUNT(*) FROM pipeline_runs WHERE created_at > datetime('now', '-1 hour');" 2>/dev/null; then
        local recent_runs=$(docker-compose exec -T database sqlite3 /app/data/zazzle_pipeline.db "SELECT COUNT(*) FROM pipeline_runs WHERE created_at > datetime('now', '-1 hour');" 2>/dev/null)
        if [[ "$recent_runs" -gt 0 ]]; then
            success "Pipeline has run recently ($recent_runs runs in last hour)"
        else
            warning "No pipeline runs in the last hour"
        fi
    else
        warning "Could not check pipeline status"
    fi
    
    # Check last pipeline run
    local last_run=$(docker-compose exec -T database sqlite3 /app/data/zazzle_pipeline.db "SELECT created_at FROM pipeline_runs ORDER BY created_at DESC LIMIT 1;" 2>/dev/null)
    if [[ -n "$last_run" ]]; then
        info "Last pipeline run: $last_run"
    else
        warning "No pipeline runs found"
    fi
    
    echo ""
}

# Generate summary report
generate_summary() {
    echo "📊 Health Summary"
    echo "================"
    
    local issues=0
    local warnings=0
    
    # Count issues from previous checks
    if ! check_docker_services > /dev/null 2>&1; then
        ((issues++))
    fi
    
    if ! check_api_endpoints > /dev/null 2>&1; then
        ((issues++))
    fi
    
    if ! check_frontend > /dev/null 2>&1; then
        ((issues++))
    fi
    
    if ! check_database > /dev/null 2>&1; then
        ((issues++))
    fi
    
    if ! check_environment > /dev/null 2>&1; then
        ((warnings++))
    fi
    
    if [[ $issues -eq 0 && $warnings -eq 0 ]]; then
        success "All systems operational"
        echo ""
        echo "🎉 Your Zazzle Agent is running perfectly!"
        echo ""
        echo "Quick access:"
        echo "  • Frontend: http://localhost:5173"
        echo "  • API: http://localhost:8000"
        echo "  • API Docs: http://localhost:8000/docs"
        echo ""
    elif [[ $issues -eq 0 ]]; then
        warning "System operational with minor issues"
        echo ""
        echo "⚠️  Some configuration issues detected"
        echo ""
    else
        error "System has issues that need attention"
        echo ""
        echo "❌ $issues critical issues detected"
        echo "⚠️  $warnings warnings"
        echo ""
        echo "Recommended actions:"
        echo "  1. Check logs: make show-logs"
        echo "  2. Restart services: docker-compose restart"
        echo "  3. Redeploy: make deploy"
        echo ""
    fi
}

# Main function
main() {
    echo "🏥 Zazzle Agent Health Monitor"
    echo "=============================="
    echo ""
    
    # Parse command line arguments
    SHOW_LOGS=false
    SHOW_RESOURCES=false
    QUICK_CHECK=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --logs)
                SHOW_LOGS=true
                shift
                ;;
            --resources)
                SHOW_RESOURCES=true
                shift
                ;;
            --quick)
                QUICK_CHECK=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --logs       Show recent logs"
                echo "  --resources  Show resource usage"
                echo "  --quick      Quick health check only"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run health checks
    check_docker_services
    check_api_endpoints
    check_frontend
    check_database
    check_environment
    check_pipeline_status
    
    if [[ "$SHOW_RESOURCES" == true ]]; then
        check_resource_usage
    fi
    
    if [[ "$SHOW_LOGS" == true ]]; then
        check_recent_logs
    fi
    
    # Generate summary
    generate_summary
}

# Run main function with all arguments
main "$@" 