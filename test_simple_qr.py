#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.image_processor import ImageProcessor
from PIL import Image

def test_qr_modes():
    """Test both simple_qr and logo_to_qr functions"""
    try:
        # Initialize the image processor
        processor = ImageProcessor()
        
        # Test URL
        test_url = "https://example.com/test"
        
        print("Testing QR code generation modes...")
        
        # Test simple QR mode (default)
        print("1. Testing simple_qr function...")
        simple_qr_image = processor.simple_qr(None, test_url)
        print(f"   Simple QR generated successfully!")
        print(f"   Image size: {simple_qr_image.size}")
        print(f"   Image mode: {simple_qr_image.mode}")
        
        # Save simple QR
        simple_qr_image.save("test_simple_qr_output.png")
        print("   Saved as: test_simple_qr_output.png")
        
        # Test logo QR mode
        print("\n2. Testing logo_to_qr function...")
        logo_qr_image = processor.logo_to_qr(None, test_url)
        print(f"   Logo QR generated successfully!")
        print(f"   Image size: {logo_qr_image.size}")
        print(f"   Image mode: {logo_qr_image.mode}")
        
        # Save logo QR
        logo_qr_image.save("test_logo_qr_output.png")
        print("   Saved as: test_logo_qr_output.png")
        
        # Test stamping with simple mode (default)
        print("\n3. Testing stamping with simple mode (default)...")
        blank_image = Image.new('RGB', (1024, 1024), (255, 255, 255))
        stamped_simple = processor.stamp_image_with_logo(blank_image, test_url)
        print(f"   Simple stamping successful!")
        print(f"   Stamped image size: {stamped_simple.size}")
        print(f"   Stamped image mode: {stamped_simple.mode}")
        
        # Save stamped image
        stamped_simple.save("test_stamped_simple.png")
        print("   Saved as: test_stamped_simple.png")
        
        # Test stamping with logo mode
        print("\n4. Testing stamping with logo mode...")
        stamped_logo = processor.stamp_image_with_logo(blank_image, test_url, use_logo=True)
        print(f"   Logo stamping successful!")
        print(f"   Stamped image size: {stamped_logo.size}")
        print(f"   Stamped image mode: {stamped_logo.mode}")
        
        # Save stamped image
        stamped_logo.save("test_stamped_logo.png")
        print("   Saved as: test_stamped_logo.png")
        
        print("\n✅ All tests completed successfully!")
        print("\nGenerated files:")
        print("- test_simple_qr_output.png (simple QR code)")
        print("- test_logo_qr_output.png (logo QR code)")
        print("- test_stamped_simple.png (stamped with simple QR)")
        print("- test_stamped_logo.png (stamped with logo QR)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qr_modes() 