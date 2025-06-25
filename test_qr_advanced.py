#!/usr/bin/env python3
"""
Test script for advanced QR code styling with logo integration.
"""

import os
from PIL import Image
from app.services.image_processor import ImageProcessor
from app.db.database import get_db
from app.db.models import ProductInfo

def test_qr_styling():
    """Test the advanced QR code styling functionality."""
    print("Testing advanced QR code styling...")
    
    # Initialize the image processor
    processor = ImageProcessor()
    
    # Get a sample product from the database
    db = next(get_db())
    try:
        products = db.query(ProductInfo).limit(3).all()
        
        if not products:
            print("No products found in database. Creating test image...")
            # Create a test image if no products exist
            test_image = Image.new("RGB", (1024, 1024), color="lightblue")
            test_url = "/redirect/test_image_20250625124000_1024x1024.png"
            
            try:
                # Test the new QR code styling
                stamped_image = processor.logo_to_qr(test_image, test_url)
                stamped_image.save("test_qr_advanced_output.png")
                print("✅ Advanced QR code styling test completed successfully!")
                print("📁 Saved as: test_qr_advanced_output.png")
                
                # Test variants
                variants = processor.create_qr_variants(test_image, test_url)
                for variant_name, variant_image in variants.items():
                    variant_image.save(f"test_qr_variant_{variant_name}.png")
                    print(f"📁 Saved variant: test_qr_variant_{variant_name}.png")
                
            except Exception as e:
                print(f"❌ Error testing QR styling: {e}")
                return False
        else:
            print(f"Found {len(products)} products in database. Testing with real data...")
            
            for i, product in enumerate(products):
                # Print product info for context
                display_title = product.image_title or product.theme or product.id
                print(f"\n--- Testing Product {i+1}: {display_title} ---")
                
                # Load the product image
                # Use image_url to get the filename
                if product.image_url:
                    image_filename = os.path.basename(product.image_url)
                    image_path = f"outputs/generated_products/{image_filename}"
                else:
                    print(f"⚠️  No image_url for product {i+1}")
                    continue
                
                if os.path.exists(image_path):
                    try:
                        # Load the original image
                        original_image = Image.open(image_path)
                        
                        # Create QR code URL
                        qr_url = f"/redirect/{product.image_filename}"
                        if product.affiliate_link:
                            qr_url = product.affiliate_link
                        
                        print(f"🔗 QR URL: {qr_url}")
                        
                        # Apply advanced QR styling
                        stamped_image = processor.logo_to_qr(original_image, qr_url)
                        
                        # Save the result
                        output_path = f"test_qr_product_{i+1}.png"
                        stamped_image.save(output_path)
                        print(f"✅ Saved: {output_path}")
                        
                        # Create variants for comparison
                        variants = processor.create_qr_variants(original_image, qr_url)
                        for variant_name, variant_image in variants.items():
                            variant_path = f"test_qr_product_{i+1}_{variant_name}.png"
                            variant_image.save(variant_path)
                            print(f"📁 Variant: {variant_path}")
                        
                    except Exception as e:
                        print(f"❌ Error processing product {i+1}: {e}")
                else:
                    print(f"⚠️  Image file not found: {image_path}")
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = test_qr_styling()
    if success:
        print("\n🎉 All QR code styling tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Check the output above.") 