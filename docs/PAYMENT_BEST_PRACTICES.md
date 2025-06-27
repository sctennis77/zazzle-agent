# Stripe Payment Integration Best Practices

This document outlines the secure payment integration implemented in the Zazzle Agent project, following Stripe's recommended best practices.

## Security Overview

### ✅ Implemented Best Practices

1. **Client-Side Payment Intent Creation**: Payment intents are created on the client side using Stripe.js
2. **Server-Side Validation**: All payment confirmations are validated on the server
3. **No Secret Keys in Frontend**: Only publishable keys are used in the browser
4. **Webhook Verification**: Payment status is verified through Stripe webhooks
5. **Amount Validation**: Payment amounts are validated server-side before processing
6. **Error Handling**: Comprehensive error handling for all payment scenarios

## Architecture

### Payment Flow

```
1. Client creates payment intent via Stripe.js
2. Client confirms payment with card details
3. Server validates payment intent and amount
4. Server saves donation to database
5. Server processes donation (creates tasks, etc.)
6. Webhook confirms payment status
```

### API Endpoints

#### `/api/donations/create-payment-intent` (POST)
- **Purpose**: Create a payment intent for client-side processing
- **Security**: Server-side creation with immediate client-side confirmation
- **Response**: Returns client secret for Stripe.js

#### `/api/donations/confirm-payment` (POST)
- **Purpose**: Validate and save confirmed payments
- **Security**: Validates payment intent status and amount
- **Response**: Confirms donation was saved successfully

#### `/api/donations/webhook` (POST)
- **Purpose**: Handle Stripe webhook events
- **Security**: Verifies webhook signatures
- **Actions**: Updates donation status, creates tasks

## Frontend Implementation

### Stripe Elements Integration

The frontend uses Stripe Elements for secure card input:

```typescript
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);
```

### Payment Flow

1. **Form Validation**: Client validates all required fields
2. **Payment Intent Creation**: Creates payment intent via API
3. **Card Confirmation**: Uses Stripe.js to confirm payment
4. **Server Confirmation**: Sends payment intent ID to server for validation
5. **Success Handling**: Shows success message and closes modal

## Backend Implementation

### Payment Intent Creation

```python
def create_payment_intent(self, donation_request: DonationRequest) -> Dict:
    """Create a payment intent with proper metadata."""
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(donation_request.amount_usd) * 100),
            currency="usd",
            metadata={
                "donation_type": donation_request.donation_type,
                "subreddit": donation_request.subreddit,
                "customer_email": donation_request.customer_email,
            },
            automatic_payment_methods={"enabled": True},
        )
        return {
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "amount_cents": payment_intent.amount,
            "amount_usd": donation_request.amount_usd,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {str(e)}")
        raise
```

### Payment Validation

```python
def confirm_donation_payment(self, payment_intent_id: str, donation_request: DonationRequest):
    """Validate payment intent and save donation."""
    # Retrieve payment intent from Stripe
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    
    # Validate status
    if payment_intent.status != "succeeded":
        raise HTTPException(status_code=400, detail="Payment not confirmed")
    
    # Validate amount
    amount_cents = payment_intent.amount
    expected_amount_cents = int(float(donation_request.amount_usd) * 100)
    if amount_cents != expected_amount_cents:
        raise HTTPException(status_code=400, detail="Amount mismatch")
    
    # Save donation
    donation = self.save_donation_to_db(db, payment_intent_data, donation_request)
    return donation
```

## Security Measures

### 1. Environment Variables

```bash
# Frontend (.env)
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Backend (.env)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. Webhook Verification

```python
def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature to prevent replay attacks."""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        return True
    except ValueError:
        return False
    except stripe.error.SignatureVerificationError:
        return False
```

### 3. Amount Validation

- Server validates payment amount against donation request
- Prevents client-side manipulation of amounts
- Uses cents to avoid floating-point precision issues

### 4. Payment Intent Status Validation

- Only processes payments with "succeeded" status
- Prevents processing of failed or pending payments
- Validates payment intent exists and is valid

## Error Handling

### Frontend Errors

```typescript
try {
  const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
    payment_method: { card: elements.getElement(CardElement)! }
  });
  
  if (error) {
    setError(error.message);
    return;
  }
} catch (err) {
  setError('An unexpected error occurred');
}
```

### Backend Errors

```python
try:
    # Payment processing logic
    pass
except stripe.error.StripeError as e:
    logger.error(f"Stripe error: {str(e)}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## Testing

### Test Cards

Use Stripe's test cards for development:

- **Success**: `4242424242424242`
- **Decline**: `4000000000000002`
- **3D Secure**: `4000002500003155`

### Test Environment

```bash
# Set test keys
export STRIPE_SECRET_KEY=sk_test_...
export VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

## Production Considerations

### 1. Webhook Endpoints

- Use HTTPS in production
- Implement webhook signature verification
- Handle webhook failures gracefully

### 2. Error Monitoring

- Log all payment errors
- Monitor failed payment rates
- Set up alerts for payment issues

### 3. PCI Compliance

- Never store card data
- Use Stripe Elements for card input
- Follow PCI DSS guidelines

### 4. Rate Limiting

- Implement rate limiting on payment endpoints
- Prevent abuse and fraud
- Monitor for suspicious activity

## Monitoring and Logging

### Payment Logs

```python
logger.info(f"Payment intent created: {payment_intent_id}")
logger.info(f"Payment confirmed: {payment_intent_id}")
logger.error(f"Payment failed: {payment_intent_id} - {error}")
```

### Metrics to Track

- Payment success rate
- Average donation amount
- Failed payment reasons
- Webhook delivery success

## Troubleshooting

### Common Issues

1. **Payment Intent Not Found**: Check payment intent ID validity
2. **Amount Mismatch**: Verify amount conversion to cents
3. **Webhook Failures**: Check webhook endpoint and signature
4. **Client Secret Issues**: Ensure proper client secret handling

### Debug Mode

Enable Stripe debug logging:

```python
import logging
logging.getLogger('stripe').setLevel(logging.DEBUG)
```

## Conclusion

This implementation follows Stripe's security best practices and provides a robust, secure payment system for donations. The client-side payment flow ensures security while providing a smooth user experience.

For more information, see:
- [Stripe Security Best Practices](https://stripe.com/docs/security)
- [Stripe Elements Documentation](https://stripe.com/docs/stripe-js)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks) 