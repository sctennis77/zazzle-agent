#!/bin/bash

# Commission Workflow Test Script
# This script automates the setup and execution of the commission workflow test

set -e

echo "🚀 Starting Commission Workflow Test"
echo "====================================="

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

# Kill existing processes
print_status "Killing existing processes..."
pkill -f "python -m app.api" || true
pkill -f "npm run dev" || true
pkill -f "stripe listen" || true
sleep 2

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

# Create commission donation
print_status "Creating commission donation..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/donations/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{
    "subreddit": "hiking",
    "donation_type": "commission",
    "amount": 2500,
    "customer_name": "Test Hiker",
    "reddit_username": "testhiker",
    "commission_message": "Create a beautiful product from an amazing hiking post!",
    "is_anonymous": false
  }')

# Extract checkout URL
CHECKOUT_URL=$(echo $RESPONSE | jq -r '.checkout_url')

if [ "$CHECKOUT_URL" != "null" ] && [ "$CHECKOUT_URL" != "" ]; then
    print_success "Commission donation created successfully"
    echo ""
    echo "🎯 TEST SETUP COMPLETE"
    echo "======================"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Open this URL in your browser:"
    echo "   $CHECKOUT_URL"
    echo ""
    echo "2. Use these test card details:"
    echo "   Card: 4242 4242 4242 4242"
    echo "   Expiry: Any future date (MM/YY)"
    echo "   CVC: Any 3 digits"
    echo "   ZIP: Any 5 digits"
    echo ""
    echo "3. Complete the payment form"
    echo "4. Notify when payment is complete"
    echo ""
    echo "🔧 Services Running:"
    echo "   API: http://localhost:8000"
    echo "   Frontend: http://localhost:5173"
    echo "   Stripe Webhook: Listening on localhost:8000/api/donations/webhook"
    echo ""
    echo "💡 To stop all services, run: pkill -f 'python -m app.api' && pkill -f 'npm run dev' && pkill -f 'stripe listen'"
    echo ""
    
    # Wait for user input
    read -p "Press Enter when payment is complete to continue with task processing..."
    
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
    print_error "Failed to create commission donation"
    echo "Response: $RESPONSE"
    exit 1
fi

# Cleanup function
cleanup() {
    print_status "Cleaning up processes..."
    kill $API_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill $STRIPE_PID 2>/dev/null || true
    print_success "Cleanup complete"
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Keep script running to maintain background processes
print_status "Keeping services running. Press Ctrl+C to stop all services."
wait 