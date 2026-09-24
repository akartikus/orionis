import logging
from decimal import Decimal
from typing import Any, Dict, List
import ccxt.async_support as ccxt
from config import settings
from database.client import db

logger = logging.getLogger(__name__)


class PortfolioCollector:
    """Collector responsible for synchronizing Bitvavo account balances with Supabase."""

    def __init__(self) -> None:
        self.exchange = ccxt.bitvavo(
            {
                "apiKey": settings.BITVAVO_API_KEY,
                "secret": settings.BITVAVO_API_SECRET,
                "enableRateLimit": True,
            }
        )

    async def _fetch_balances_and_prices(self) -> List[Dict[str, Any]]:
        """Fetch real-time balances and ticker prices from Bitvavo."""
        try:
            logger.info("Fetching balances from Bitvavo API...")
            balance_data = await self.exchange.fetch_balance()
            tickers = await self.exchange.fetch_tickers()

            items: List[Dict[str, Any]] = []
            total_balances = balance_data.get("total", {})

            for asset, total_amount in total_balances.items():
                quantity = Decimal(str(total_amount))
                if quantity <= Decimal("0"):
                    continue

                # Determine current market price in EUR
                if asset == "EUR":
                    current_price = Decimal("1.0")
                else:
                    symbol = f"{asset}/EUR"
                    price_val = tickers.get(symbol, {}).get("last", 0.0)
                    current_price = Decimal(str(price_val or 0.0))

                items.append(
                    {
                        "asset": asset,
                        "total_quantity": str(quantity),
                        "current_price": str(current_price),
                    }
                )

            return items
        except Exception as e:
            logger.error(f"Failed to fetch data from Bitvavo: {e}")
            raise e

    async def sync_global_portfolio(self) -> None:
        """Synchronize total Bitvavo balances into the 'portfolio' table."""
        items = await self._fetch_balances_and_prices()
        if not items:
            logger.warning("No non-zero balances found on Bitvavo.")
            return

        client = await db.connect()

        payloads = [
            {
                "asset": item["asset"],
                "total_quantity": item["total_quantity"],
                "current_price": item["current_price"],
            }
            for item in items
        ]
        await client.table("portfolio").upsert(
            payloads, on_conflict="asset"
        ).execute()

        logger.info(f"Successfully synced {len(items)} assets into 'portfolio' table.")

    async def sync_bot_managed_prices(self) -> None:
        """Update current asset prices in the 'bot_managed_assets' table."""
        client = await db.connect()
        response = await client.table("bot_managed_assets").select("asset").execute()
        managed_assets = response.data or []

        if not managed_assets:
            logger.info("No assets currently managed in 'bot_managed_assets'.")
            return

        try:
            tickers = await self.exchange.fetch_tickers()
            for record in managed_assets:
                asset = record["asset"]
                if asset == "EUR":
                    price = Decimal("1.0")
                else:
                    symbol = f"{asset}/EUR"
                    price = Decimal(str(tickers.get(symbol, {}).get("last", 0.0)))

                await client.table("bot_managed_assets").update(
                    {"current_price": str(price)}
                ).eq("asset", asset).execute()

            logger.info("Updated market prices for bot-managed assets.")
        except Exception as e:
            logger.error(f"Failed to update bot managed asset prices: {e}")

    async def close(self) -> None:
        """Close the underlying CCXT exchange HTTP session."""
        await self.exchange.close()


async def run_portfolio_sync() -> None:
    """Convenience runner function for portfolio synchronization."""
    collector = PortfolioCollector()
    try:
        await collector.sync_global_portfolio()
        await collector.sync_bot_managed_prices()
    finally:
        await collector.close()