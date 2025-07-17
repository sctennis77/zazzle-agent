#!/usr/bin/env python3
"""
Run the Clouvel Promoter Agent

Queen Clouvel's promotional agent for scanning r/popular/hot and promoting
commission opportunities through witty, engaging comments.
"""

import argparse
import logging
import os
import sys
import time
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.agents.clouvel_promoter_agent import ClouvelPromoterAgent
from app.utils.logging_config import setup_logging


def main():
    """Main entry point for the promoter agent"""
    parser = argparse.ArgumentParser(
        description="Run Queen Clouvel's Promoter Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in dry-run mode (recommended for testing)
  python run_promoter_agent.py --dry-run

  # Run single cycle in dry-run mode
  python run_promoter_agent.py --dry-run --single-cycle

  # Run with custom subreddit
  python run_promoter_agent.py --subreddit askreddit --dry-run

  # Run continuously (production mode - NOT dry-run)
  python run_promoter_agent.py --continuous

  # Check agent status
  python run_promoter_agent.py --status-only
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("PROMOTER_DRY_RUN", "true").lower() == "true",
        help="Run in dry-run mode (analyze but don't post/vote)"
    )

    parser.add_argument(
        "--subreddit",
        type=str,
        default=os.getenv("PROMOTER_SUBREDDIT", "popular"),
        help="Target subreddit (default: popular)"
    )

    parser.add_argument(
        "--single-cycle",
        action="store_true",
        help="Run only one cycle instead of continuous operation"
    )

    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously with delay between cycles"
    )

    parser.add_argument(
        "--delay-minutes",
        type=int,
        default=int(os.getenv("PROMOTER_DELAY_MINUTES", "10")),
        help="Minutes to wait between cycles in continuous mode (default: 10)"
    )

    parser.add_argument(
        "--max-cycles",
        type=int,
        help="Maximum number of cycles to run (for testing)"
    )

    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Only check and display agent status"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.continuous and args.single_cycle:
        print("Error: Cannot use both --continuous and --single-cycle", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and not args.continuous and not args.single_cycle and not args.status_only:
        print("Warning: Running without --dry-run. This will perform actual Reddit actions!")
        print("Consider using --dry-run for testing first.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(0)

    # Setup logging
    setup_logging(log_level=args.log_level)
    logger = logging.getLogger(__name__)

    # Initialize agent
    try:
        agent = ClouvelPromoterAgent(
            subreddit_name=args.subreddit,
            dry_run=args.dry_run
        )
        logger.info(f"Initialized ClouvelPromoterAgent for r/{args.subreddit} (dry_run={args.dry_run})")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        sys.exit(1)

    # Status-only mode
    if args.status_only:
        try:
            status = agent.get_status()
            print("\n" + "="*50)
            print("🏛️  QUEEN CLOUVEL'S PROMOTER AGENT STATUS")
            print("="*50)
            print(f"Agent Type: {status.get('agent_type', 'Unknown')}")
            print(f"Dry Run Mode: {status.get('dry_run', 'Unknown')}")
            print(f"Total Scanned: {status.get('total_scanned', 0)}")
            print(f"Total Promoted: {status.get('total_promoted', 0)}")
            print(f"Total Rejected: {status.get('total_rejected', 0)}")
            print(f"Promotion Rate: {status.get('promotion_rate', 0):.1f}%")
            
            recent = status.get('recent_activity', [])
            if recent:
                print(f"\nRecent Activity ({len(recent)} posts):")
                for post in recent[:5]:  # Show last 5
                    action = "✅ Promoted" if post.get('promoted') else "❌ Rejected"
                    title = post.get('post_title', 'No title')[:40]
                    print(f"  {action}: {title}... (r/{post.get('subreddit', '?')})")
            
            print("="*50)
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            sys.exit(1)
        return

    # Single cycle mode
    if args.single_cycle or not args.continuous:
        logger.info("Running single cycle...")
        try:
            result = agent.run_single_cycle()
            
            print("\n" + "="*50)
            print("🏛️  SINGLE CYCLE RESULTS")
            print("="*50)
            
            if result.get("processed"):
                action = result.get("action", "unknown")
                post_id = result.get("post_id", "unknown")
                print(f"✅ Successfully {action} post: {post_id}")
            elif result.get("error"):
                print(f"❌ Error: {result['error']}")
            else:
                print("ℹ️  No posts processed (no novel posts found)")
            
            print("="*50)
        except Exception as e:
            logger.error(f"Error in single cycle: {e}")
            sys.exit(1)
        return

    # Continuous mode
    if args.continuous:
        logger.info(f"Starting continuous operation (delay: {args.delay_minutes} minutes)")
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                logger.info(f"Starting cycle {cycle_count}")
                
                try:
                    result = agent.run_single_cycle()
                    
                    if result.get("processed"):
                        action = result.get("action", "unknown")
                        post_id = result.get("post_id", "unknown")
                        logger.info(f"Cycle {cycle_count}: {action} post {post_id}")
                    elif result.get("error"):
                        logger.warning(f"Cycle {cycle_count}: Error - {result['error']}")
                    else:
                        logger.info(f"Cycle {cycle_count}: No novel posts found")
                        
                except Exception as e:
                    logger.error(f"Error in cycle {cycle_count}: {e}")
                
                # Check max cycles
                if args.max_cycles and cycle_count >= args.max_cycles:
                    logger.info(f"Reached maximum cycles ({args.max_cycles}), stopping")
                    break
                
                # Wait before next cycle
                delay_seconds = args.delay_minutes * 60
                logger.info(f"Waiting {args.delay_minutes} minutes before next cycle...")
                time.sleep(delay_seconds)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping gracefully...")
        except Exception as e:
            logger.error(f"Unexpected error in continuous mode: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()