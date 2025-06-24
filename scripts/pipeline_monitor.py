#!/usr/bin/env python3
"""
Pipeline Monitor Script

This script provides real-time monitoring of pipeline runs and their status.
It can be used to track pipeline progress and identify issues.
"""

import sys
import time
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import ErrorLog, PipelineRun, ProductInfo, RedditPost
from app.pipeline_status import PipelineStatus


def format_duration(start_time, end_time=None):
    """Format duration between two times."""
    if not start_time:
        return "N/A"

    if not end_time:
        end_time = datetime.utcnow()

    duration = end_time - start_time
    if duration.total_seconds() < 60:
        return f"{duration.total_seconds():.1f}s"
    elif duration.total_seconds() < 3600:
        return f"{duration.total_seconds() / 60:.1f}m"
    else:
        return f"{duration.total_seconds() / 3600:.1f}h"


def get_status_emoji(status):
    """Get emoji for pipeline status."""
    status_emojis = {
        PipelineStatus.STARTED.value: "🟡",
        PipelineStatus.COMPLETED.value: "🟢",
        PipelineStatus.FAILED.value: "🔴",
        PipelineStatus.CANCELLED.value: "⚫",
    }
    return status_emojis.get(status, "❓")


def monitor_pipeline():
    """Monitor pipeline runs in real-time."""
    print("🚀 Pipeline Monitor Started")
    print("Press Ctrl+C to stop monitoring")
    print("=" * 80)

    try:
        while True:
            session = SessionLocal()
            try:
                # Get recent pipeline runs
                runs = (
                    session.query(PipelineRun)
                    .order_by(PipelineRun.start_time.desc())
                    .limit(10)
                    .all()
                )

                print(
                    f"\n📊 Pipeline Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print("-" * 80)

                if not runs:
                    print("No pipeline runs found.")
                else:
                    for run in runs:
                        emoji = get_status_emoji(run.status)
                        duration = format_duration(run.start_time, run.end_time)

                        print(f"{emoji} Run #{run.id}: {run.status.upper()}")
                        print(
                            f"   📅 Started: {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        print(f"   ⏱️  Duration: {duration}")

                        if run.end_time:
                            print(
                                f"   ✅ Finished: {run.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )

                        if run.last_error:
                            print(f"   ❌ Error: {run.last_error[:100]}...")

                        # Get associated data
                        reddit_posts = (
                            session.query(RedditPost)
                            .filter_by(pipeline_run_id=run.id)
                            .all()
                        )
                        products = (
                            session.query(ProductInfo)
                            .filter_by(pipeline_run_id=run.id)
                            .all()
                        )
                        errors = (
                            session.query(ErrorLog)
                            .filter_by(pipeline_run_id=run.id)
                            .all()
                        )

                        print(f"   📝 Reddit Posts: {len(reddit_posts)}")
                        print(f"   🛍️  Products: {len(products)}")
                        print(f"   ⚠️  Errors: {len(errors)}")

                        if products:
                            for product in products:
                                print(
                                    f"      • {product.theme} ({product.product_type})"
                                )

                        print()

                # Show summary statistics
                total_runs = session.query(PipelineRun).count()
                completed_runs = (
                    session.query(PipelineRun)
                    .filter_by(status=PipelineStatus.COMPLETED.value)
                    .count()
                )
                failed_runs = (
                    session.query(PipelineRun)
                    .filter_by(status=PipelineStatus.FAILED.value)
                    .count()
                )
                running_runs = (
                    session.query(PipelineRun)
                    .filter_by(status=PipelineStatus.STARTED.value)
                    .count()
                )

                print(
                    f"📈 Summary: {total_runs} total runs | {completed_runs} completed | {failed_runs} failed | {running_runs} running"
                )

            finally:
                session.close()

            time.sleep(30)  # Update every 30 seconds

    except KeyboardInterrupt:
        print("\n\n👋 Pipeline monitor stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error in pipeline monitor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    monitor_pipeline()
