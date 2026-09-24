import asyncio
import logging

from config import settings
from database.client import db
from collectors.portfolio_collector import run_portfolio_sync
from collectors.market_collector import run_market_sync
from collectors.news_collector import run_news_sync


async def test_database_connection() -> bool:
    """Vérifie rapidement la connexion à Supabase."""
    print("🔌 Test de la connexion à Supabase...")
    try:
        await db.connect()
        print("  ✅ Connexion Supabase établie.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ Échec de connexion : {exc}")
        return False
    finally:
        await db.disconnect()


async def main() -> None:
    if not await test_database_connection():
        return

    print("\n📊 Test du PortfolioCollector...")
    await run_portfolio_sync()

    print("\n📈 Test du MarketCollector...")
    await run_market_sync(["BTC", "ETH"])

    print("\n📰 Test du NewsCollector...")
    await run_news_sync()

    print("\n🚀 Terminé !")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    asyncio.run(main())