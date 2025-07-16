#!/usr/bin/env python3
"""
Script to trigger a manual scheduled commission run for local testing.

This script:
1. Checks scheduler status
2. Enables scheduler if disabled 
3. Triggers a manual commission run
4. Shows the results

Usage: python scripts/trigger_manual_commission.py
"""

import json
import os
from typing import Any, Dict

import requests


def get_admin_secret() -> str:
    """Get admin secret from environment or use local default."""
    return os.getenv("ADMIN_SECRET", "test-admin-secret")


def get_base_url() -> str:
    """Get API base URL."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


def make_admin_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make an authenticated admin request."""
    headers = {"Content-Type": "application/json", "X-Admin-Secret": get_admin_secret()}

    if "headers" in kwargs:
        kwargs["headers"].update(headers)
    else:
        kwargs["headers"] = headers

    url = f"{get_base_url()}{endpoint}"
    response = requests.request(method, url, **kwargs)

    return response


def print_response(title: str, response: requests.Response) -> None:
    """Print formatted response."""
    print(f"\n=== {title} ===")
    print(f"Status: {response.status_code}")

    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except json.JSONDecodeError:
        print(f"Response: {response.text}")


def check_scheduler_status() -> Dict[str, Any]:
    """Check current scheduler status."""
    print("Checking scheduler status...")
    response = make_admin_request("GET", "/api/admin/scheduler/status")
    print_response("Scheduler Status", response)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get scheduler status: {response.text}")


def enable_scheduler() -> None:
    """Enable the scheduler with 24-hour interval."""
    print("Enabling scheduler...")
    response = make_admin_request(
        "POST", "/api/admin/scheduler/config?enabled=true&interval_hours=24"
    )
    print_response("Enable Scheduler", response)

    if response.status_code != 200:
        raise Exception(f"Failed to enable scheduler: {response.text}")


def trigger_manual_run() -> Dict[str, Any]:
    """Trigger a manual commission run."""
    print("Triggering manual commission run...")
    response = make_admin_request("POST", "/api/admin/scheduler/run-now")
    print_response("Manual Commission Run", response)

    if response.status_code == 200:
        return response.json()
    else:
        # For 500 errors, still try to parse the JSON for error details
        try:
            error_data = response.json()
            return {"error": error_data.get("detail", response.text)}
        except:
            return {"error": response.text}


def main():
    """Main script execution."""
    try:
        print("🚀 Testing Manual Commission Trigger")
        print(f"API Base URL: {get_base_url()}")
        print(f"Admin Secret: {get_admin_secret()}")

        # Step 1: Check scheduler status
        status_data = check_scheduler_status()
        scheduler_enabled = status_data.get("scheduler", {}).get("enabled", False)

        # Step 2: Enable scheduler if disabled
        if not scheduler_enabled:
            print("\n⚠️  Scheduler is disabled, enabling it...")
            enable_scheduler()
        else:
            print("\n✅ Scheduler is already enabled")

        # Step 3: Trigger manual run
        print("\n🎯 Triggering manual commission run...")
        result = trigger_manual_run()

        # Step 4: Analyze results
        print("\n" + "=" * 50)
        if "error" in result:
            print("❌ Manual commission failed:")
            print(f"   Error: {result['error']}")
            if "validation failed" in result["error"].lower():
                print(
                    "\n💡 This is normal - means no suitable trending posts were found"
                )
                print("   in the randomly selected subreddit. Try running again for a")
                print("   different random subreddit.")
        elif result.get("status") == "scheduled commission created":
            print("✅ Manual commission created successfully!")
            commission = result.get("commission", {})
            print(f"   Subreddit: r/{commission.get('subreddit')}")
            print(f"   Amount: ${commission.get('amount_usd')}")
            print(f"   Task ID: {commission.get('task_id')}")
            print(f"   Donation ID: {commission.get('donation_id')}")
        elif result.get("status") == "scheduled commission skipped":
            print("⏭️  Manual commission was skipped:")
            print(f"   Reason: {result.get('reason')}")
        else:
            print("🤔 Unexpected response:")
            print(f"   {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
