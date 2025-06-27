#!/usr/bin/env python3
"""
End-to-end test script that:
1. Starts the API server
2. Creates a donation via curl
3. Replays the webhook to trigger the full pipeline
4. Verifies the results
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.db.models import PipelineTask, ProductInfo
from app.utils.logging_config import setup_logging

# Set up logging
setup_logging(log_level="INFO", console_output=True)
logger = logging.getLogger(__name__)


class EndToEndTester:
    """Class to handle end-to-end testing of the pipeline."""
    
    def __init__(self):
        self.api_process = None
        self.webhook_data = None
        
    def start_api_server(self):
        """Start the API server in the background."""
        logger.info("Starting API server...")
        
        # Kill any existing API processes
        try:
            subprocess.run(["pkill", "-f", "python.*app.api"], check=False)
            time.sleep(2)
        except Exception:
            pass
        
        # Start the API server
        self.api_process = subprocess.Popen(
            ["poetry", "run", "python", "-m", "app.api"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for API to start
        logger.info("Waiting for API server to start...")
        time.sleep(5)
        
        # Check if API is running
        try:
            response = subprocess.run(
                ["curl", "-s", "http://localhost:8000/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if response.returncode == 0:
                logger.info("✅ API server started successfully")
                return True
            else:
                logger.error("❌ API server failed to start")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking API server: {e}")
            return False
    
    def create_donation(self):
        """Create a donation via curl."""
        logger.info("Creating donation via API...")
        
        try:
            response = subprocess.run(
                [
                    "curl", "-s", "-X", "POST", 
                    "http://localhost:8000/api/donations/create-checkout-session",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps({
                        "amount": 25.0,
                        "subreddit": "golf",
                        "donation_type": "commission"
                    })
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if response.returncode == 0:
                result = json.loads(response.stdout)
                if "checkout_url" in result:
                    logger.info(f"✅ Created donation with checkout URL: {result['checkout_url']}")
                    return result
                else:
                    logger.error(f"❌ Unexpected response: {result}")
                    return None
            else:
                logger.error(f"❌ Failed to create donation: {response.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating donation: {e}")
            return None
    
    def replay_webhook(self, checkout_session_id: str):
        """Replay the webhook using the saved webhook data."""
        logger.info(f"Replaying webhook for session: {checkout_session_id}")
        
        # Load webhook data from file
        webhook_file = Path("custom_webhook.json")
        if not webhook_file.exists():
            logger.error("❌ Webhook file not found: custom_webhook.json")
            return False
        
        try:
            with open(webhook_file, 'r') as f:
                webhook_data = json.load(f)
            
            # Update the session ID in the webhook data
            if "data" in webhook_data and "object" in webhook_data["data"]:
                webhook_data["data"]["object"]["id"] = checkout_session_id
            
            # Send webhook to API
            response = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    "http://localhost:8000/api/donations/webhook",
                    "-H", "Content-Type: application/json",
                    "-H", "Stripe-Signature: test_signature",
                    "-d", json.dumps(webhook_data)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if response.returncode == 0:
                logger.info("✅ Webhook replayed successfully")
                return True
            else:
                logger.error(f"❌ Failed to replay webhook: {response.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error replaying webhook: {e}")
            return False
    
    def wait_for_task_completion(self, timeout: int = 300):
        """Wait for task completion and check results."""
        logger.info(f"Waiting up to {timeout} seconds for task completion...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            session = SessionLocal()
            try:
                # Check for completed tasks
                completed_tasks = session.query(PipelineTask).filter(
                    PipelineTask.status == "completed"
                ).all()
                
                if completed_tasks:
                    logger.info(f"✅ Found {len(completed_tasks)} completed tasks")
                    
                    # Check for generated products
                    products = session.query(ProductInfo).all()
                    if products:
                        logger.info(f"✅ Generated {len(products)} products")
                        for product in products:
                            logger.info(f"  - Product {product.id}: {product.name}")
                        return True
                    else:
                        logger.info("No products generated yet, waiting...")
                
                time.sleep(10)
                
            finally:
                session.close()
        
        logger.error("❌ Timeout waiting for task completion")
        return False
    
    def verify_results(self):
        """Verify the end-to-end results."""
        logger.info("Verifying end-to-end results...")
        
        session = SessionLocal()
        try:
            # Check tasks
            tasks = session.query(PipelineTask).all()
            logger.info(f"Total tasks: {len(tasks)}")
            
            for task in tasks:
                logger.info(f"  Task {task.id}: {task.status} - {task.type}")
            
            # Check products
            products = session.query(ProductInfo).all()
            logger.info(f"Total products: {len(products)}")
            
            for product in products:
                logger.info(f"  Product {product.id}: {product.name}")
                if product.image_url:
                    logger.info(f"    Image: {product.image_url}")
                if product.zazzle_url:
                    logger.info(f"    Zazzle: {product.zazzle_url}")
            
            return len(products) > 0
            
        finally:
            session.close()
    
    def cleanup(self):
        """Clean up resources."""
        if self.api_process:
            logger.info("Stopping API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.api_process.kill()
            logger.info("API server stopped")


async def run_end_to_end_test():
    """Run the full end-to-end test."""
    tester = EndToEndTester()
    
    try:
        # Step 1: Start API server
        if not tester.start_api_server():
            return False
        
        # Step 2: Create donation
        donation_result = tester.create_donation()
        if not donation_result:
            return False
        
        # Extract checkout session ID from the URL
        checkout_url = donation_result["checkout_url"]
        session_id = checkout_url.split("/")[-1]
        logger.info(f"Checkout session ID: {session_id}")
        
        # Step 3: Replay webhook
        if not tester.replay_webhook(session_id):
            return False
        
        # Step 4: Wait for task completion
        if not tester.wait_for_task_completion():
            return False
        
        # Step 5: Verify results
        if not tester.verify_results():
            return False
        
        logger.info("✅ End-to-end test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in end-to-end test: {e}", exc_info=True)
        return False
    finally:
        tester.cleanup()


def main():
    """Main function to run the end-to-end test."""
    logger.info("🚀 Starting end-to-end pipeline test...")
    
    # Check if webhook file exists
    if not Path("custom_webhook.json").exists():
        logger.error("❌ custom_webhook.json not found. Please run a webhook first to capture the data.")
        sys.exit(1)
    
    # Run the test
    success = asyncio.run(run_end_to_end_test())
    
    if success:
        logger.info("🎉 End-to-end test PASSED!")
        sys.exit(0)
    else:
        logger.error("💥 End-to-end test FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main() 