#!/usr/bin/env python3
"""
Test script to debug message saving in donation form
"""

import requests
import json

# Test the donation API endpoints
BASE_URL = "http://localhost:8000"

def test_create_payment_intent_with_message():
    """Test creating a payment intent with a message"""
    url = f"{BASE_URL}/api/donations/create-payment-intent"
    
    payload = {
        "amount_usd": "5.00",
        "subreddit": "golf",
        "donation_type": "support",
        "post_id": "1lojucl",
        "message": "This is a test message from the debug script",
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "reddit_username": "testuser",
        "is_anonymous": False
    }
    
    print("Creating payment intent with message...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Payment intent created: {data['payment_intent_id']}")
        return data['payment_intent_id']
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_update_payment_intent_with_message(payment_intent_id):
    """Test updating a payment intent with a new message"""
    url = f"{BASE_URL}/api/donations/payment-intent/{payment_intent_id}/update"
    
    payload = {
        "amount_usd": "5.00",
        "subreddit": "golf",
        "donation_type": "support",
        "post_id": "1lojucl",
        "message": "This is an updated test message from the debug script",
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "reddit_username": "testuser",
        "is_anonymous": False
    }
    
    print(f"\nUpdating payment intent {payment_intent_id} with new message...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.put(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Payment intent updated: {data['payment_intent_id']}")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_get_donation_by_payment_intent(payment_intent_id):
    """Test getting donation data by payment intent ID"""
    url = f"{BASE_URL}/api/donations/{payment_intent_id}"
    
    print(f"\nGetting donation data for {payment_intent_id}...")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Donation data:")
        print(f"  Message: '{data.get('message', 'None')}'")
        print(f"  Reddit Username: '{data.get('reddit_username', 'None')}'")
        print(f"  Is Anonymous: {data.get('is_anonymous', 'None')}")
        print(f"  Customer Email: '{data.get('customer_email', 'None')}'")
        print(f"  Customer Name: '{data.get('customer_name', 'None')}'")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    print("🧪 Testing donation message saving functionality...\n")
    
    # Test 1: Create payment intent with message
    payment_intent_id = test_create_payment_intent_with_message()
    
    if payment_intent_id:
        # Test 2: Update payment intent with new message
        test_update_payment_intent_with_message(payment_intent_id)
        
        # Test 3: Get donation data to verify message was saved
        test_get_donation_by_payment_intent(payment_intent_id)
    
    print("\n🏁 Test completed!") 