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

async def run_once():
    """Run the agent once."""
    logger.info("=" * 50)
    logger.info("WCCC Ride Signup Agent - Starting")
    logger.info("=" * 50)

    try:
        result = await find_and_register_for_ride()
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

    parser = argparse.ArgumentParser(description="WCCC Ride Signup Agent")
    parser.add_argument("--schedule", action="store_true", help="Run on hourly schedule")
    args = parser.parse_args()

    if args.schedule:
        run_scheduler()
    else:
        asyncio.run(run_once())
