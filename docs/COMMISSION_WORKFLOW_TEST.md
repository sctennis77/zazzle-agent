# Commission Workflow End-to-End Test Documentation

## Test Overview
This document outlines the successful end-to-end test of the commission workflow for the Zazzle Agent system. The test simulates a real user donating to commission a product from a specific subreddit.

## Test Environment Setup

### Prerequisites
- Fresh database (reset before test)
- API server running on port 8000
- Frontend running on port 5173
- Stripe CLI webhook listener running
- Poetry environment with all dependencies installed

### Environment Variables
- `STRIPE_SECRET_KEY`: Test Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Webhook signing secret from Stripe CLI
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`: Reddit API credentials
- `OPENAI_API_KEY`: OpenAI API key for content generation
- `IMGUR_CLIENT_ID`: Imgur API credentials
- `ZAZZLE_AFFILIATE_ID`: Zazzle affiliate ID

## Test Execution Steps

### 1. Environment Preparation
```bash
# Kill any existing processes
pkill -f "python -m app.api"
pkill -f "npm run dev"
pkill -f "stripe listen"

# Reset database
make reset-db

# Start API server
poetry run python -m app.api

# Start frontend (in separate terminal)
cd frontend && npm run dev

# Start Stripe webhook listener (in separate terminal)
stripe listen --forward-to localhost:8000/api/donations/webhook
```

### 2. Commission Donation Creation
- API endpoint: `POST /api/donations/create-checkout-session`
- Request payload:
```json
{
  "subreddit": "hiking",
  "donation_type": "commission",
  "amount": 2500,
  "customer_name": "Test Hiker",
  "reddit_username": "testhiker",
  "commission_message": "Create a beautiful product from an amazing hiking post!",
  "is_anonymous": false
}
```

### 3. Stripe Checkout Session
- System creates Stripe checkout session
- Returns checkout URL: `https://checkout.stripe.com/pay/cs_test_...`
- User completes payment using test card details:
  - Card: 4242 4242 4242 4242
  - Expiry: Any future date
  - CVC: Any 3 digits
  - ZIP: Any 5 digits

### 4. Webhook Processing
When payment is completed, Stripe sends webhook events:
- `charge.succeeded`
- `payment_intent.succeeded`
- `checkout.session.completed`
- `payment_intent.created`
- `charge.updated`

The `checkout.session.completed` event triggers the main processing:
- Creates donation record in database
- Creates sponsor record with "Silver Supporter" tier
- Creates commission task in pipeline_tasks table
- Processes subreddit tier goals

### 5. Task Processing
Run the task runner to process the commission:
```bash
poetry run python -m app.task_runner
```

This triggers:
- Reddit post selection (in dry-run mode)
- Product idea generation using OpenAI
- Image generation using DALL-E 3
- Image upload to Imgur
- Zazzle product creation with affiliate link

## Database Records Created

### Donations Table
```sql
INSERT INTO donations (
  payment_intent_id,
  amount_cents,
  amount_dollars,
  currency,
  status,
  customer_email,
  customer_name,
  reddit_username,
  metadata,
  created_at,
  updated_at,
  commission_type,
  commission_message
) VALUES (
  'pi_3ReRWzQ9k35tku6l2LnoAuGO',
  2500,
  25,
  'usd',
  'succeeded',
  'test@example.com',
  'Test Hiker',
  'testhiker',
  '{"subreddit": "hiking", "donation_type": "commission", ...}',
  '2025-06-27 01:56:48.289404',
  '2025-06-27 01:56:48.299764',
  'commission',
  'Create a beautiful product from an amazing hiking post!'
);
```

### Pipeline Tasks Table
```sql
INSERT INTO pipeline_tasks (
  task_type,
  subreddit_id,
  sponsor_id,
  status,
  priority,
  created_at,
  metadata
) VALUES (
  'SUBREDDIT_POST',
  1,
  1,
  'pending',
  10,
  '2025-06-27 01:56:48.319213',
  '{"donation_id": 1, "donation_amount": 25.0, "sponsor_tier": "Silver Supporter", ...}'
);
```

### Sponsors Table
```sql
INSERT INTO sponsors (
  donation_id,
  tier_name,
  created_at
) VALUES (
  1,
  'Silver Supporter',
  '2025-06-27 01:56:48.316000'
);
```

## Test Results

### Success Criteria Met
✅ Payment processing completed successfully
✅ Webhook events processed correctly
✅ Database records created properly
✅ Commission task generated
✅ Task runner processes task successfully
✅ Product generated and available in API
✅ Frontend displays generated products

### API Endpoints Verified
- `GET /api/generated_products` - Returns generated products
- `GET /api/products/{id}/donations` - Returns product donation info
- `POST /api/donations/create-checkout-session` - Creates checkout session
- `POST /api/donations/webhook` - Processes Stripe webhooks

### Frontend Integration
- Products display correctly in UI
- Product details and donation information accessible
- Responsive design working properly

## Manual Testing Process

For future testing, the workflow is:

1. **Setup Environment**: Reset DB, start services, start webhook listener
2. **Create Commission**: Use API to create checkout session
3. **Manual Payment**: Provide user with Stripe checkout URL and test card details
4. **User Completion**: User completes payment form and notifies when done
5. **Process Task**: Run task runner to generate product
6. **Verify Results**: Check API endpoints and frontend display

## Test Card Information
- **Card Number**: 4242 4242 4242 4242
- **Expiry**: Any future date (MM/YY)
- **CVC**: Any 3 digits
- **ZIP**: Any 5 digits
- **Name**: Any name

## Troubleshooting Notes

### Common Issues
1. **Port conflicts**: Ensure no other services are using ports 8000, 5173
2. **Database permissions**: Ensure SQLite database is writable
3. **Environment variables**: Verify all required API keys are set
4. **Webhook signature**: Ensure Stripe webhook secret is correct

### Debug Commands
```bash
# Check database state
sqlite3 data/zazzle_pipeline.db "SELECT * FROM donations;"
sqlite3 data/zazzle_pipeline.db "SELECT * FROM pipeline_tasks;"

# Check API health
curl http://localhost:8000/health

# Check generated products
curl http://localhost:8000/api/generated_products
```

## Conclusion

The commission workflow test was successful, demonstrating that:
- Stripe payment processing works correctly
- Webhook handling is robust
- Database operations are reliable
- Task processing generates products as expected
- API and frontend integration is functional

This provides a solid foundation for production deployment and further feature development. 