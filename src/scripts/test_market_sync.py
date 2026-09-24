import asyncio
import logging
import sys
from pathlib import Path

# Add project root directory to sys.path to resolve internal module imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from collectors.market_collector import MarketCollector, run_market_sync

# Configure clean logging output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("test_market_sync")


async def main() -> None:
    """Run market data synchronization test for BTC and ETH."""
    assets = ["BTC", "ETH"]
    logger.info(f"🚀 Starting MarketCollector test for assets: {assets}...")

    try:
        # Run sync pipeline
        await run_market_sync(assets=assets)
        logger.info("✅ Market sync completed successfully.")
    except Exception as e:
        logger.error(f"❌ Market sync failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())