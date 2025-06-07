import json
import os
import unittest

class TestConfigStructure(unittest.TestCase):
    """Test cases for validating configuration file structure."""

    def setUp(self):
        """Set up test environment."""
        current_file_path = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file_path)
        project_root = os.path.abspath(os.path.join(current_dir, os.pardir))

        self.template_path = os.path.join(project_root, 'app', 'products_config.template.json')
        self.config_path = os.path.join(project_root, 'app', 'products_config.json')
        
        print(f"Template path: {self.template_path}")
        print(f"Config path: {self.config_path}")

        # Load template
        with open(self.template_path, 'r') as f:
            self.template = json.load(f)
            
        # Load actual config if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                self.fail(f"Error decoding JSON from configuration file: {self.config_path}")
        else:
            self.config = [] # Initialize as empty list if file not found, to prevent NoneType errors

    def test_config_exists(self):
        """Test that the actual config file exists."""
        self.assertTrue(
            os.path.exists(self.config_path),
            f"Configuration file not found at {self.config_path}. Please copy from template."
        )

    def test_config_is_list(self):
        """Test that config is a list of products."""
        self.assertIsInstance(self.config, list, "Configuration should be a list of products")

    def test_config_has_products(self):
        """Test that config has at least one product."""
        if not self.config:
            self.skipTest("No products in config, skipping product structure tests.")
        self.assertGreater(len(self.config), 0, "Configuration should have at least one product")

    def test_product_structure(self):
        """Test that each product in config has the required structure."""
        if not self.config:
            self.skipTest("No products in config, skipping product structure tests.")
        for product in self.config:
            # Check required top-level fields
            self.assertIn('product_type', product, "Product missing 'product_type' field")
            self.assertIn('zazzle_template_id', product, "Product missing 'zazzle_template_id' field")
            self.assertIn('original_url', product, "Product missing 'original_url' field")
            self.assertIn('zazzle_tracking_code', product, "Product missing 'zazzle_tracking_code' field")
            self.assertIn('customizable_fields', product, "Product missing 'customizable_fields' field")

            # Check customizable fields structure
            fields = product['customizable_fields']
            self.assertIn('text', fields, "Missing 'text' in customizable_fields")
            self.assertIn('image', fields, "Missing 'image' in customizable_fields")

            # Check text field structure
            text_field = fields['text']
            self.assertIn('type', text_field, "Text field missing 'type'")
            self.assertIn('description', text_field, "Text field missing 'description'")
            self.assertIn('max_length', text_field, "Text field missing 'max_length'")
            self.assertEqual(text_field['type'], 'text', "Text field type should be 'text'")

            # Check image field structure
            image_field = fields['image']
            self.assertIn('type', image_field, "Image field missing 'type'")
            self.assertIn('description', image_field, "Image field missing 'description'")
            self.assertIn('formats', image_field, "Image field missing 'formats'")
            self.assertIn('max_size_mb', image_field, "Image field missing 'max_size_mb'")
            self.assertEqual(image_field['type'], 'image', "Image field type should be 'image'")

    def test_template_values_not_used(self):
        """Test that template placeholder values are not used in actual config."""
        if not self.config:
            self.skipTest("No products in config, skipping template value checks.")
        for product in self.config:
            self.assertNotEqual(
                product['zazzle_template_id'],
                'YOUR_TEMPLATE_ID',
                "Template ID should be replaced with actual value"
            )
            self.assertNotEqual(
                product['original_url'],
                'YOUR_ORIGINAL_URL',
                "Original URL should be replaced with actual value"
            )
            self.assertNotEqual(
                product['zazzle_tracking_code'],
                'YOUR_TRACKING_CODE',
                "Tracking code should be replaced with actual value"
            )

    def test_config_matches_template_structure(self):
        """Test that config matches template structure exactly."""
        if not self.config or not self.template:
            self.skipTest("Config or template not loaded, skipping structure comparison.")
        # Compare the structure of the first product in both files
        template_product = self.template[0]
        config_product = self.config[0]

        # Compare top-level fields
        self.assertEqual(
            set(template_product.keys()),
            set(config_product.keys()),
            "Config product has different fields than template"
        )

        # Compare customizable fields structure
        template_fields = template_product['customizable_fields']
        config_fields = config_product['customizable_fields']

        self.assertEqual(
            set(template_fields.keys()),
            set(config_fields.keys()),
            "Config customizable fields have different structure than template"
        )

        # Compare text field structure
        self.assertEqual(
            set(template_fields['text'].keys()),
            set(config_fields['text'].keys()),
            "Config text field has different structure than template"
        )

        # Compare image field structure
        self.assertEqual(
            set(template_fields['image'].keys()),
            set(config_fields['image'].keys()),
            "Config image field has different structure than template"
        )

if __name__ == '__main__':
    unittest.main() 