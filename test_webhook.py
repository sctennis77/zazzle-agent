#!/usr/bin/env python3
"""
Test script to simulate a Stripe webhook event for successful checkout session completion.
"""

import json
import time

import requests

# Mock checkout session data
checkout_session_data = {
    "id": "cs_test_a1Y6K3x42wh7Dki9yuegAMJPa7V83kSNTtL2Nac39uQ84vZ3hnJdjZBikK",
    "object": "checkout.session",
    "amount_total": 1000,  # $10.00 in cents
    "payment_intent": "pi_test_1234567890",
    "customer_email": "test@example.com",
    "metadata": {
        "donation_type": "commission",
        "subreddit": "golf",
        "post_id": "",
        "commission_message": "Please create a new product from a cool golf post!",
        "message": "",
        "customer_name": "Test User",
        "reddit_username": "",
        "is_anonymous": "false",
    },
    "status": "complete",
}

# Mock webhook event
webhook_event = {
    "id": "evt_test_1234567890",
    "object": "event",
    "type": "checkout.session.completed",
    "data": {"object": checkout_session_data},
}


def test_webhook():
    """Test the webhook endpoint with a mock event."""
    url = "http://localhost:8000/api/donations/webhook"

    # For testing, we'll skip signature verification by commenting out the signature check
    # In production, you would need a proper signature

    headers = {
        "Content-Type": "application/json",
        "stripe-signature": "test_signature",  # Mock signature for testing
    }

    try:
        response = requests.post(url, json=webhook_event, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Testing webhook with mock checkout session completion...")
    success = test_webhook()
    if success:
        print("Webhook test successful!")
    else:
        print("Webhook test failed!")
