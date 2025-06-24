#!/usr/bin/env python3
"""
Simple script to test OpenAI API quota and rate limits.
"""

import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_openai_quota():
    """Test OpenAI API quota and rate limits."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    print(f"🔑 API Key loaded: {api_key[:5]}...{api_key[-5:]}")
    
    client = OpenAI(api_key=api_key)
    
    # Test 1: Simple chat completion
    print("\n🧪 Testing GPT-3.5-turbo chat completion...")
    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello, world!'"}],
            max_tokens=10
        )
        end_time = time.time()
        
        print(f"✅ Success! Response: {response.choices[0].message.content}")
        print(f"⏱️  Response time: {(end_time - start_time)*1000:.2f}ms")
        
        if hasattr(response, 'usage') and response.usage:
            print(f"📊 Tokens used: {response.usage.total_tokens}")
        
        # Check rate limit headers
        if hasattr(response, '_headers'):
            headers = response._headers
            if 'x-ratelimit-remaining-requests' in headers:
                print(f"🔄 Rate limit remaining: {headers['x-ratelimit-remaining-requests']}")
            if 'x-ratelimit-reset-requests' in headers:
                print(f"🕐 Rate limit reset: {headers['x-ratelimit-reset-requests']}")
        
    except Exception as e:
        print(f"❌ Chat completion failed: {e}")
        return False
    
    # Test 2: DALL-E image generation
    print("\n🎨 Testing DALL-E-3 image generation...")
    try:
        start_time = time.time()
        response = client.images.generate(
            model="dall-e-3",
            prompt="A simple red circle on a white background",
            size="1024x1024",
            n=1,
            response_format="url"
        )
        end_time = time.time()
        
        print(f"✅ Success! Image URL: {response.data[0].url}")
        print(f"⏱️  Response time: {(end_time - start_time)*1000:.2f}ms")
        
        # Check rate limit headers
        if hasattr(response, '_headers'):
            headers = response._headers
            if 'x-ratelimit-remaining-requests' in headers:
                print(f"🔄 Rate limit remaining: {headers['x-ratelimit-remaining-requests']}")
            if 'x-ratelimit-reset-requests' in headers:
                print(f"🕐 Rate limit reset: {headers['x-ratelimit-reset-requests']}")
        
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Your OpenAI API is working correctly.")
    return True

if __name__ == "__main__":
    test_openai_quota() 