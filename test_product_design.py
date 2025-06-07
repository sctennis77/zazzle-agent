import os
from dotenv import load_dotenv
from app.product_designer import ZazzleProductDesigner
from app.models import Product
import json

def test_product_design():
    # Load environment variables
    load_dotenv()
    
    # Initialize product designer
    designer = ZazzleProductDesigner()
    
    # Load product configuration
    with open('app/products_config.json', 'r') as f:
        config = json.load(f)
    
    # Get the sticker product configuration
    sticker_config = config[0]  # We know it's the first product
    
    # Create test product info
    product_info = {
        'text': 'FIRE THE CANNONS!',
        'image_url': 'https://example.com/test_image.png',
        'image_iid': '4b2bbb87-ee28-47a3-9de9-5ddb045ec8bc',  # Using the IID from the original URL
        'theme': 'golf',
        'color': 'white',
        'quantity': 1
    }
    
    # Create the product
    result = designer.create_product(product_info)
    
    # Print results
    print("\nProduct Design Test Results:")
    print("----------------------------")
    print(f"Configuration loaded: {sticker_config['product_type']} with template ID {sticker_config['zazzle_template_id']}")
    print(f"Tracking code: {sticker_config.get('zazzle_tracking_code', 'Not set')}")
    print("\nProduct Creation Result:")
    if result:
        print("✅ Product created successfully!")
        print(f"Product URL: {result['product_url']}")
        print(f"Text: {result['text']}")
        print(f"Theme: {result['theme']}")
    else:
        print("❌ Product creation failed!")
    
    return result

if __name__ == '__main__':
    test_product_design() 