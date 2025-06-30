#!/bin/bash

# Commission Workflow Test Script
# This script automates the setup and execution of the commission workflow test
# 
# Usage:
#   ./scripts/test_commission_workflow.sh                    # Random post commission
#   ./scripts/test_commission_workflow.sh --post-id abc123   # Specific post commission
#   ./scripts/test_commission_workflow.sh --post-url "https://reddit.com/r/golf/comments/abc123/..." # Specific post via URL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
POST_ID=""
COMMISSION_TYPE="random"
SUBREDDIT="hiking"
AMOUNT="25"
CUSTOMER_NAME="Test Hiker"
REDDIT_USERNAME="testhiker"
COMMISSION_MESSAGE="Create a beautiful product from an amazing hiking post!"
IS_ANONYMOUS="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --post-id)
      POST_ID="$2"
      COMMISSION_TYPE="specific"
      shift 2
      ;;
    --post-url)
      POST_URL="$2"
      COMMISSION_TYPE="specific"
      shift 2
      ;;
    --subreddit)
      SUBREDDIT="$2"
      shift 2
      ;;
    --amount)
      AMOUNT="$2"
      shift 2
      ;;
    --customer-name)
      CUSTOMER_NAME="$2"
      shift 2
      ;;
    --reddit-username)
      REDDIT_USERNAME="$2"
      shift 2
      ;;
    --commission-message)
      COMMISSION_MESSAGE="$2"
      shift 2
      ;;
    --anonymous)
      IS_ANONYMOUS="true"
      shift
      ;;
    --cleanup)
      print_status "Manual cleanup mode - stopping all related services..."
      manual_cleanup
      exit 0
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --post-id ID              Commission a specific post by ID"
      echo "  --post-url URL            Commission a specific post by URL"
      echo "  --subreddit NAME          Subreddit to commission from (default: hiking)"
      echo "  --amount AMOUNT           Commission amount in USD (default: 25)"
      echo "  --customer-name NAME      Customer name (default: Test Hiker)"
      echo "  --reddit-username USER    Reddit username (default: testhiker)"
      echo "  --commission-message MSG  Commission message"
      echo "  --anonymous               Make donation anonymous"
      echo "  --cleanup                 Manually clean up all related services"
      echo "  --help                    Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                                    # Random post commission"
      echo "  $0 --post-id abc123                   # Specific post by ID"
      echo "  $0 --post-url \"https://reddit.com/r/golf/comments/abc123/...\"  # Specific post by URL"
      echo "  $0 --subreddit golf --amount 50       # Golf subreddit, $50 commission"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to check if services are already running
check_existing_services() {
    local services_running=false
    
    if pgrep -f "python -m app.api" > /dev/null; then
        print_warning "API server is already running"
        services_running=true
    fi
    
    if pgrep -f "npm run dev" > /dev/null; then
        print_warning "Frontend is already running"
        services_running=true
    fi
    
    if pgrep -f "stripe listen" > /dev/null; then
        print_warning "Stripe webhook listener is already running"
        services_running=true
    fi
    
    if lsof -i :8000 > /dev/null 2>&1; then
        print_warning "Port 8000 is in use"
        services_running=true
    fi
    
    if lsof -i :5173 > /dev/null 2>&1; then
        print_warning "Port 5173 is in use"
        services_running=true
    fi
    
    if [ "$services_running" = true ]; then
        echo ""
        print_warning "Some services appear to be already running."
        echo "The test will stop these services and start fresh."
        echo ""
        read -p "Press Enter to continue (or Ctrl+C to cancel)..."
        echo ""
    fi
}

# Function to extract post ID from Reddit URL (same logic as frontend)
extract_post_id() {
    local input="$1"
    
    # Handle various Reddit URL formats
    if [[ $input =~ reddit\.com/r/[^/]+/comments/([a-zA-Z0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ $input =~ reddit\.com/comments/([a-zA-Z0-9]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ $input =~ ^[a-zA-Z0-9]+$ ]]; then
        echo "$input"  # Just the post ID
    else
        echo "$input"  # Return as-is if no pattern matches
    fi
}

# Extract post ID if URL was provided
if [[ -n "$POST_URL" ]]; then
    POST_ID=$(extract_post_id "$POST_URL")
    echo "Extracted post ID: $POST_ID from URL: $POST_URL"
fi

echo "🚀 Starting Commission Workflow Test"
echo "====================================="
echo "Commission Type: $COMMISSION_TYPE"
echo "Subreddit: r/$SUBREDDIT"
echo "Amount: \$$AMOUNT"
echo "Customer: $CUSTOMER_NAME"
echo "Reddit Username: $REDDIT_USERNAME"
if [[ "$COMMISSION_TYPE" == "specific" ]]; then
    echo "Post ID: $POST_ID"
fi
echo "Anonymous: $IS_ANONYMOUS"
echo ""

# Check for existing services before starting
check_existing_services

# Kill existing processes
print_status "Stopping any existing services..."
print_status "Killing API server processes..."
pkill -f "python -m app.api" || true
pkill -f "uvicorn.*app.api" || true
pkill -f "python.*app/api" || true

print_status "Killing frontend processes..."
pkill -f "npm run dev" || true
pkill -f "vite" || true
pkill -f "node.*frontend" || true

print_status "Killing Stripe webhook listener..."
pkill -f "stripe listen" || true

print_status "Killing any other related processes..."
pkill -f "task_runner" || true
pkill -f "pipeline" || true

# Wait for processes to fully stop
print_status "Waiting for processes to stop..."
sleep 3

# Double-check that ports are free
print_status "Checking if ports are available..."
if lsof -i :8000 > /dev/null 2>&1; then
    print_warning "Port 8000 still in use, forcing cleanup..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -i :5173 > /dev/null 2>&1; then
    print_warning "Port 5173 still in use, forcing cleanup..."
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
fi

# Wait a bit more to ensure ports are free
sleep 2

print_success "Service cleanup completed"

# Reset database
print_status "Resetting database..."
make reset-db
print_success "Database reset complete"

# Start API server in background
print_status "Starting API server..."
poetry run python -m app.api &
API_PID=$!
sleep 5

# Check if API is running
if curl -s http://localhost:8000/health > /dev/null; then
    print_success "API server started successfully"
else
    print_error "API server failed to start"
    exit 1
fi

# Start frontend in background
print_status "Starting frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..
sleep 3

# Check if frontend is running
if curl -s http://localhost:5173 > /dev/null; then
    print_success "Frontend started successfully"
else
    print_warning "Frontend may not be ready yet (this is normal)"
fi

# Start Stripe webhook listener in background
print_status "Starting Stripe webhook listener..."
stripe listen --forward-to localhost:8000/api/donations/webhook &
STRIPE_PID=$!
sleep 3

# Build the request payload (following the same pattern as the frontend)
print_status "Creating commission donation using UI API pattern..."

# Create the request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "amount_usd": "$AMOUNT",
  "subreddit": "$SUBREDDIT",
  "donation_type": "commission",
  "post_id": "$POST_ID",
  "commission_message": "$COMMISSION_MESSAGE",
  "customer_name": "$CUSTOMER_NAME",
  "reddit_username": "$REDDIT_USERNAME",
  "is_anonymous": $IS_ANONYMOUS
}
EOF
)

print_status "Request payload:"
echo "$REQUEST_PAYLOAD" | jq .

# Create commission donation using the same endpoint as the frontend
RESPONSE=$(curl -s -X POST http://localhost:8000/api/donations/create-payment-intent \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD")

# Check if the request was successful
if echo "$RESPONSE" | jq -e '.client_secret' > /dev/null; then
    print_success "Payment intent created successfully"
    
    # Extract client secret and payment intent ID
    CLIENT_SECRET=$(echo "$RESPONSE" | jq -r '.client_secret')
    PAYMENT_INTENT_ID=$(echo "$RESPONSE" | jq -r '.payment_intent_id')
    
    print_status "Payment Intent ID: $PAYMENT_INTENT_ID"
    print_status "Client Secret: $CLIENT_SECRET"
    
    echo ""
    echo "🎯 TEST SETUP COMPLETE"
    echo "======================"
    echo ""
    echo "📋 Commission Details:"
    echo "   Type: $COMMISSION_TYPE"
    echo "   Subreddit: r/$SUBREDDIT"
    echo "   Amount: \$$AMOUNT"
    echo "   Customer: $CUSTOMER_NAME"
    if [[ "$COMMISSION_TYPE" == "specific" ]]; then
        echo "   Post ID: $POST_ID"
    fi
    echo "   Client Secret: $CLIENT_SECRET"
    echo ""
    echo "🔧 Services Running:"
    echo "   API: http://localhost:8000"
    echo "   Frontend: http://localhost:5173"
    echo "   Stripe Webhook: Listening on localhost:8000/api/donations/webhook"
    echo ""
    echo "💡 To complete the payment, open the frontend in your browser and use the commission form."
    echo "   (If the form allows, pre-fill with the above parameters.)"
    echo "   Complete the payment using the Express Checkout Element (Apple Pay, Google Pay, PayPal, or card)."
    echo ""
    echo "⚠️  NOTE: Do NOT close this terminal."
    echo "   After you complete the payment in the browser, press Enter below to continue."
    echo ""
    read -p "Press Enter after you have completed the payment in the frontend..."
    
    # Process the task
    print_status "Processing commission task..."
    poetry run python -m app.task_runner
    
    print_success "Task processing complete!"
    echo ""
    echo "🎉 COMMISSION WORKFLOW TEST COMPLETE"
    echo "===================================="
    echo ""
    echo "📊 Check Results:"
    echo "   API Products: http://localhost:8000/api/generated_products"
    echo "   Frontend: http://localhost:5173"
    echo ""
    echo "🗄️  Database Records:"
    echo "   Donations: sqlite3 data/zazzle_pipeline.db 'SELECT * FROM donations;'"
    echo "   Tasks: sqlite3 data/zazzle_pipeline.db 'SELECT * FROM pipeline_tasks;'"
    echo ""
    
else
    print_error "Failed to create payment intent"
    echo "Response: $RESPONSE"
    exit 1
fi

# Cleanup function
cleanup() {
    print_status "Cleaning up processes..."
    
    # Kill the specific processes we started
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        print_status "Stopped API server (PID: $API_PID)"
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_status "Stopped frontend (PID: $FRONTEND_PID)"
    fi
    
    if [ -n "$STRIPE_PID" ]; then
        kill $STRIPE_PID 2>/dev/null || true
        print_status "Stopped Stripe webhook listener (PID: $STRIPE_PID)"
    fi
    
    # Also kill any related processes that might still be running
    print_status "Cleaning up any remaining related processes..."
    pkill -f "python -m app.api" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "stripe listen" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    # Force kill processes on ports if needed
    if lsof -i :8000 > /dev/null 2>&1; then
        print_warning "Port 8000 still in use, forcing cleanup..."
        lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    fi
    
    if lsof -i :5173 > /dev/null 2>&1; then
        print_warning "Port 5173 still in use, forcing cleanup..."
        lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    fi
    
    print_success "Cleanup complete"
}

# Manual cleanup function (can be called separately)
manual_cleanup() {
    print_status "Manual cleanup - stopping all related services..."
    pkill -f "python -m app.api" 2>/dev/null || true
    pkill -f "uvicorn.*app.api" 2>/dev/null || true
    pkill -f "python.*app/api" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "node.*frontend" 2>/dev/null || true
    pkill -f "stripe listen" 2>/dev/null || true
    pkill -f "task_runner" 2>/dev/null || true
    pkill -f "pipeline" 2>/dev/null || true
    
    # Force kill processes on ports
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    
    print_success "Manual cleanup completed"
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Keep script running to maintain background processes
print_status "Keeping services running. Press Ctrl+C to stop all services."
print_status "To manually stop all services, run: ./scripts/test_commission_workflow.sh --cleanup"
wait 