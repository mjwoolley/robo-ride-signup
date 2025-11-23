import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import navigate_to_wccc
from src.logger import setup_logger

logger = setup_logger()

async def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("WCCC Ride Signup Agent - Starting")
    logger.info("=" * 50)

    try:
        result = await navigate_to_wccc()
        logger.info("Agent run completed successfully")
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
