import asyncio
import sys
import time
from pathlib import Path

import schedule

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import find_and_register_for_ride
from src.logger import setup_logger

logger = setup_logger()

# Global debug flag
_debug_mode = False

async def run_once():
    """Run the agent once."""
    logger.info("=" * 50)
    logger.info("WCCC Ride Signup Agent - Starting")
    if _debug_mode:
        logger.info("Debug mode: ENABLED - Full AI responses will be logged")
    logger.info("=" * 50)

    try:
        result = await find_and_register_for_ride(debug=_debug_mode)
        logger.info("Agent run completed successfully")
        return result
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        raise

def scheduled_job():
    """Wrapper to run async agent in scheduler."""
    try:
        asyncio.run(run_once())
    except Exception as e:
        logger.error(f"Scheduled job failed: {e}")

def run_scheduler():
    """Run the agent on an hourly schedule."""
    logger.info("Starting scheduler - agent will run every hour")

    # Run immediately on start
    scheduled_job()

    # Schedule hourly runs
    schedule.every().hour.do(scheduled_job)

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="WCCC Ride Signup Agent - Automatically registers for cycling rides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main              Run once
  python -m src.main -d           Run once with debug logging
  python -m src.main --schedule   Run on hourly schedule
  python -m src.main -d -s        Run scheduled with debug logging
        """
    )
    parser.add_argument(
        "-s", "--schedule",
        action="store_true",
        help="Run on hourly schedule instead of once"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug mode - log full AI responses and tool calls"
    )
    args = parser.parse_args()

    # Set global debug mode
    _debug_mode = args.debug

    if args.schedule:
        run_scheduler()
    else:
        asyncio.run(run_once())
