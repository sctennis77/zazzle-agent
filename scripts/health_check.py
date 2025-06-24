#!/usr/bin/env python3
"""
Health Check Script

This script performs a comprehensive health check of the Zazzle Agent system,
verifying that all components are working properly.
"""

import os
import subprocess
import sys
from datetime import datetime

import requests

from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost
from app.pipeline_status import PipelineStatus


def check_python_environment():
    """Check Python environment and dependencies."""
    print("🐍 Python Environment Check")
    print("-" * 40)

    try:
        import sys

        print(f"✅ Python version: {sys.version}")

        # Check key dependencies
        dependencies = [
            "fastapi",
            "sqlalchemy",
            "pandas",
            "requests",
            "openai",
            "PIL",
            "uvicorn",
            "alembic",
        ]

        for dep in dependencies:
            try:
                __import__(dep)
                print(f"✅ {dep}: OK")
            except ImportError:
                print(f"❌ {dep}: MISSING")
                return False

        return True
    except Exception as e:
        print(f"❌ Python environment check failed: {e}")
        return False


def check_database():
    """Check database connectivity and structure."""
    print("\n🗄️  Database Check")
    print("-" * 40)

    try:
        # Check if database file exists
        if os.path.exists("zazzle_pipeline.db"):
            print("✅ Database file exists")
        else:
            print("⚠️  Database file not found")
            return False

        # Test database connection
        session = SessionLocal()
        try:
            # Test basic queries
            pipeline_count = session.query(PipelineRun).count()
            product_count = session.query(ProductInfo).count()
            reddit_count = session.query(RedditPost).count()

            print(f"✅ Database connection: OK")
            print(f"✅ Pipeline runs: {pipeline_count}")
            print(f"✅ Products: {product_count}")
            print(f"✅ Reddit posts: {reddit_count}")

            # Check for recent activity
            recent_runs = (
                session.query(PipelineRun)
                .order_by(PipelineRun.start_time.desc())
                .limit(1)
                .all()
            )
            if recent_runs:
                last_run = recent_runs[0]
                print(
                    f"✅ Last pipeline run: {last_run.start_time.strftime('%Y-%m-%d %H:%M:%S')} ({last_run.status})"
                )
            else:
                print("⚠️  No pipeline runs found")

            return True
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False


def check_api_server():
    """Check if API server is running and responding."""
    print("\n🌐 API Server Check")
    print("-" * 40)

    try:
        # Check if port 8000 is in use
        result = subprocess.run(["lsof", "-i", ":8000"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ API server is running on port 8000")

            # Test API endpoint
            try:
                response = requests.get(
                    "http://localhost:8000/api/generated_products", timeout=5
                )
                if response.status_code == 200:
                    print("✅ API endpoint responding correctly")
                    data = response.json()
                    print(f"✅ API returned {len(data)} products")
                    return True
                else:
                    print(f"⚠️  API returned status code: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"⚠️  API endpoint test failed: {e}")
                return False
        else:
            print("❌ API server is not running")
            return False
    except Exception as e:
        print(f"❌ API server check failed: {e}")
        return False


def check_environment_variables():
    """Check required environment variables."""
    print("\n🔧 Environment Variables Check")
    print("-" * 40)

    required_vars = ["OPENAI_API_KEY", "ZAZZLE_AFFILIATE_ID", "ZAZZLE_TRACKING_CODE"]

    optional_vars = ["IMGUR_CLIENT_ID", "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]

    all_good = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(
                f"✅ {var}: Set ({value[:5]}...{value[-5:] if len(value) > 10 else ''})"
            )
        else:
            print(f"❌ {var}: MISSING")
            all_good = False

    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Not set (optional)")

    return all_good


def check_file_structure():
    """Check if required files and directories exist."""
    print("\n📁 File Structure Check")
    print("-" * 40)

    required_files = [
        "requirements.txt",
        "Makefile",
        "app/main.py",
        "app/pipeline.py",
        "app/api.py",
    ]

    required_dirs = ["app", "tests", "scripts", "frontend"]

    all_good = True

    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}: OK")
        else:
            print(f"❌ {file_path}: MISSING")
            all_good = False

    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✅ {dir_path}/: OK")
        else:
            print(f"❌ {dir_path}/: MISSING")
            all_good = False

    return all_good


def check_frontend():
    """Check frontend status."""
    print("\n🎨 Frontend Check")
    print("-" * 40)

    try:
        if os.path.isdir("frontend"):
            if os.path.exists("frontend/node_modules"):
                print("✅ Frontend dependencies installed")

                # Check if package.json exists
                if os.path.exists("frontend/package.json"):
                    print("✅ Frontend package.json found")
                else:
                    print("⚠️  Frontend package.json not found")
                    return False

                return True
            else:
                print("⚠️  Frontend dependencies not installed")
                print("   Run: make frontend-install")
                return False
        else:
            print("❌ Frontend directory not found")
            return False
    except Exception as e:
        print(f"❌ Frontend check failed: {e}")
        return False


def run_health_check():
    """Run the complete health check."""
    print("🏥 Zazzle Agent Health Check")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    checks = [
        ("Python Environment", check_python_environment),
        ("File Structure", check_file_structure),
        ("Environment Variables", check_environment_variables),
        ("Database", check_database),
        ("API Server", check_api_server),
        ("Frontend", check_frontend),
    ]

    results = []

    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed with exception: {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📋 Health Check Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")

    print(f"\nOverall Status: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All systems are healthy!")
        return 0
    else:
        print("⚠️  Some issues detected. Please review the failed checks above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_health_check())
