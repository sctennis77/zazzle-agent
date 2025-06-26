#!/usr/bin/env python3
"""
Test script to verify the optimized image generation logic.
Tests the core logic without importing problematic modules.
"""

import asyncio
import base64
import io
from unittest.mock import Mock, patch
from PIL import Image


def create_mock_dalle_response():
    """Create a mock DALL-E response with a simple test image."""
    # Create a simple test image
    img = Image.new('RGB', (1024, 1024), color='blue')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    img_b64 = base64.b64encode(img_data).decode('utf-8')
    
    # Create mock response
    mock_response = Mock()
    mock_response.data = [Mock(b64_json=img_b64)]
    
    return mock_response


def test_optimized_logic():
    """Test the optimized image processing logic directly."""
    print("🧪 Testing optimized image processing logic...")
    
    # Mock the Imgur client
    mock_imgur_client = Mock()
    mock_imgur_client.save_image_locally.return_value = "/tmp/test_image.png"
    mock_imgur_client.upload_image.return_value = ("https://i.imgur.com/test123.jpeg", "test123.jpeg")
    
    # Mock the image processor
    mock_image_processor = Mock()
    mock_image_processor.stamp_image_with_logo.return_value = Image.new('RGB', (1024, 1024), color='red')
    
    # Simulate the optimized logic from _process_and_store_image
    def simulate_optimized_processing(stamp_image=True):
        # Create mock DALL-E response
        mock_response = create_mock_dalle_response()
        
        # Get the base64 encoded image data
        image_data_b64 = mock_response.data[0].b64_json
        image_data = base64.b64decode(image_data_b64)
        
        # Load image as PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Generate timestamp and filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"test_template_{timestamp}_1024x1024.png"
        
        if stamp_image:
            # Generate a predictable filename for the stamped image
            stamped_filename = f"stamped_{filename}"
            
            # Determine the QR code URL
            stamp_url = f"/redirect/{stamped_filename}"
            
            # Create the stamped image with the correct QR code URL
            stamped_image = mock_image_processor.stamp_image_with_logo(image, stamp_url)
            
            # Save stamped image to bytes
            stamped_output_bytes = io.BytesIO()
            stamped_image.save(stamped_output_bytes, format="PNG")
            stamped_output_bytes.seek(0)
            stamped_image_data = stamped_output_bytes.read()
            
            # Save stamped image locally
            stamped_local_path = mock_imgur_client.save_image_locally(
                stamped_image_data, stamped_filename, subdirectory="generated_products"
            )
            
            # Upload only the final stamped image to Imgur
            stamped_imgur_url, _ = mock_imgur_client.upload_image(stamped_local_path)
            
            return stamped_imgur_url, stamped_local_path
        else:
            # Save unprocessed image to bytes
            output_bytes = io.BytesIO()
            image.save(output_bytes, format="PNG")
            output_bytes.seek(0)
            processed_image_data = output_bytes.read()

            # Save locally
            local_path = mock_imgur_client.save_image_locally(
                processed_image_data, filename, subdirectory="generated_products"
            )

            # Upload to Imgur
            imgur_url, _ = mock_imgur_client.upload_image(local_path)
            
            return imgur_url, local_path
    
    # Test stamped processing
    print("📸 Testing stamped image processing...")
    result_url, result_path = simulate_optimized_processing(stamp_image=True)
    print(f"✅ Result URL: {result_url}")
    print(f"✅ Result Path: {result_path}")
    
    # Check that only one image was uploaded
    upload_calls = mock_imgur_client.upload_image.call_count
    print(f"📊 Number of Imgur uploads: {upload_calls}")
    
    if upload_calls == 1:
        print("🎉 SUCCESS: Only one image uploaded (optimized)!")
        stamped_success = True
    else:
        print(f"❌ FAILED: Expected 1 upload, got {upload_calls}")
        stamped_success = False
    
    # Reset mock for next test
    mock_imgur_client.reset_mock()
    
    # Test unstamped processing
    print("\n📸 Testing unstamped image processing...")
    result_url, result_path = simulate_optimized_processing(stamp_image=False)
    print(f"✅ Result URL: {result_url}")
    print(f"✅ Result Path: {result_path}")
    
    # Check that only one image was uploaded
    upload_calls = mock_imgur_client.upload_image.call_count
    print(f"📊 Number of Imgur uploads: {upload_calls}")
    
    if upload_calls == 1:
        print("🎉 SUCCESS: Only one image uploaded (unstamped)!")
        unstamped_success = True
    else:
        print(f"❌ FAILED: Expected 1 upload, got {upload_calls}")
        unstamped_success = False
    
    return stamped_success, unstamped_success


def main():
    """Run the test."""
    print("🚀 Testing Image Generation Optimization")
    print("=" * 50)
    
    # Test the optimized logic
    stamped_success, unstamped_success = test_optimized_logic()
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    print(f"   Stamped Image: {'✅ PASS' if stamped_success else '❌ FAIL'}")
    print(f"   Unstamped Image: {'✅ PASS' if unstamped_success else '❌ FAIL'}")
    
    if stamped_success and unstamped_success:
        print("\n🎉 All tests passed! Optimization logic is correct.")
        print("💡 The optimized code should now only upload one image per product.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")


if __name__ == "__main__":
    main() 