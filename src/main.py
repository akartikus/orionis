import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure 'src' is in sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from collectors.market_collector import run_market_sync
from collectors.news_collector import run_news_sync
from collectors.portfolio_collector import run_portfolio_sync
from config import settings
from database.client import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("orionis.api")

# Initialize Async Scheduler for periodic jobs
scheduler = AsyncIOScheduler()


async def scheduled_portfolio_sync() -> None:
    """Task: Periodic synchronization of global portfolio from Bitvavo."""
    try:
        logger.info("⏰ [Scheduled Task] Starting portfolio synchronization...")
        await run_portfolio_sync()
    except Exception as e:
        logger.error(f"❌ [Scheduled Task Error] Portfolio sync failed: {e}")


async def scheduled_market_sync() -> None:
    """Task: Periodic synchronization of market indicators."""
    try:
        assets = settings.market_assets_list
        logger.info(f"⏰ [Scheduled Task] Starting market data synchronization for {assets}...")
        await run_market_sync(assets=assets)
    except Exception as e:
        logger.error(f"❌ [Scheduled Task Error] Market sync failed: {e}")


async def scheduled_news_sync() -> None:
    """Task: Periodic collection of crypto news and sentiment analysis."""
    try:
        logger.info("⏰ [Scheduled Task] Starting news synchronization...")
        await run_news_sync()
    except Exception as e:
        logger.error(f"❌ [Scheduled Task Error] News sync failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application Lifespan: Manage database setup and background scheduler lifecycle."""
    logger.info("🚀 Initializing ORIONIS FastAPI application...")
    
    # Initialize Supabase client
    await db.connect()

    # Configure background schedules
    scheduler.add_job(
        scheduled_portfolio_sync,
        "interval",
        minutes=settings.SCHEDULER_PORTFOLIO_INTERVAL_MINUTES,
        id="portfolio_sync",
    )
    scheduler.add_job(
        scheduled_market_sync,
        "interval",
        minutes=settings.SCHEDULER_MARKET_INTERVAL_MINUTES,
        id="market_sync",
    )
    scheduler.add_job(
        scheduled_news_sync,
        "interval",
        minutes=settings.SCHEDULER_NEWS_INTERVAL_MINUTES,
        id="news_sync",
    )

    logger.info(
        "📋 Scheduler configuré — portfolio: %d min, market: %d min, news: %d min",
        settings.SCHEDULER_PORTFOLIO_INTERVAL_MINUTES,
        settings.SCHEDULER_MARKET_INTERVAL_MINUTES,
        settings.SCHEDULER_NEWS_INTERVAL_MINUTES,
    )
    
    scheduler.start()
    logger.info("⏱️ APScheduler started with active background jobs.")

    yield  # Application runs here

    logger.info("🛑 Shutting down ORIONIS application...")
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="ORIONIS AI Portfolio API",
    description="Autonomous crypto portfolio management & execution server for Bitvavo.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================================================================
# API ROUTES
# ====================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint to verify backend status."""
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "scheduler_running": scheduler.running,
    }


@app.get("/api/v1/portfolio", tags=["Portfolio"])
async def get_portfolio(managed_only: bool = False) -> Dict[str, Any]:
    """Retrieve current portfolio state from Supabase.
    
    - `managed_only=False`: Returns global Bitvavo portfolio (`portfolio` table).
    - `managed_only=True`: Returns bot-managed sub-portfolio (`bot_managed_assets` table).
    """
    try:
        client = await db.connect()
        table_name = "bot_managed_assets" if managed_only else "portfolio"
        response = await client.table(table_name).select("*").execute()
        
        return {
            "table": table_name,
            "count": len(response.data or []),
            "items": response.data or [],
        }
    except Exception as e:
        logger.error(f"Error fetching portfolio data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portfolio state.",
        )


@app.post("/api/v1/sync/portfolio", tags=["Sync Operations"])
async def trigger_portfolio_sync(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Manually trigger an asynchronous global portfolio sync from Bitvavo."""
    background_tasks.add_task(run_portfolio_sync)
    return {"message": "Portfolio synchronization triggered in background."}


@app.post("/api/v1/sync/market", tags=["Sync Operations"])
async def trigger_market_sync(
    background_tasks: BackgroundTasks,
    assets: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Manually trigger an asynchronous market data sync."""
    target_assets = assets or settings.market_assets_list
    background_tasks.add_task(run_market_sync, target_assets)
    return {"message": f"Market sync triggered for assets: {target_assets}"}


@app.post("/api/v1/sync/news", tags=["Sync Operations"])
async def trigger_news_sync(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Manually trigger an asynchronous news & sentiment sync."""
    background_tasks.add_task(run_news_sync)
    return {"message": "News synchronization triggered in background."}