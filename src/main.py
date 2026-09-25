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
from apscheduler.triggers.cron import CronTrigger
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from collectors.market_collector import run_market_sync
from collectors.news_collector import run_news_sync
from collectors.portfolio_collector import run_portfolio_sync
from config import settings
from core.orionis_core import orionis_core
from database.client import db
from database.models.transaction import TradeRequest

from execution.order_executor import order_executor

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

    # Job quotidien — analyse complète via Orionis Core (cron 08h00)
    scheduler.add_job(
        orionis_core.run_daily_analysis,
        CronTrigger(
            hour=settings.DAILY_ANALYSIS_HOUR,
            minute=settings.DAILY_ANALYSIS_MINUTE,
        ),
        id="daily_analysis",
        replace_existing=True,
    )
    logger.info(
        "📋 Daily analysis job scheduled at %02d:%02d.",
        settings.DAILY_ANALYSIS_HOUR,
        settings.DAILY_ANALYSIS_MINUTE,
    )

    # Démarrer Orionis Core (EventBus + WorkflowEngine)
    await orionis_core.start()

    yield  # Application runs here

    logger.info("🛑 Shutting down ORIONIS application...")
    await orionis_core.stop()
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
        "orionis_core_status": orionis_core.status,
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

@app.post("/api/v1/trade", tags=["Execution"])
async def execute_trade(request: TradeRequest) -> Dict[str, Any]:
    """Execute a live trade on Bitvavo and tag origin='ORIONIS' in Supabase."""
    try:
        result = await order_executor.execute_market_order(
            symbol=request.symbol,
            side=request.side,
            amount=request.amount,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trade execution failed: {str(e)}",
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


# ====================================================================
# ORIONIS CORE — Workflows & Orchestration
# ====================================================================


class UrgentAnalysisRequest(BaseModel):
    """Request body for triggering an urgent analysis workflow."""

    asset: str = Field(..., examples=["BTC"], description="Asset ticker to analyze")
    reason: str = Field(default="Manual trigger", description="Reason for the urgent analysis")


@app.post("/api/v1/orionis/daily-analysis", tags=["Orionis Core"])
async def trigger_daily_analysis(
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """Manually trigger the daily analysis workflow in background."""
    background_tasks.add_task(orionis_core.run_daily_analysis)
    return {"message": "Daily analysis workflow triggered in background."}


@app.post("/api/v1/orionis/urgent-analysis", tags=["Orionis Core"])
async def trigger_urgent_analysis(
    request: UrgentAnalysisRequest,
) -> Dict[str, Any]:
    """Trigger an urgent analysis workflow for a specific asset."""
    try:
        result = await orionis_core.run_urgent_analysis(
            asset=request.asset, reason=request.reason
        )
        return {
            "workflow": result.workflow_name,
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
        }
    except Exception as e:
        logger.error(f"Urgent analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Urgent analysis failed: {str(e)}",
        )


@app.get("/api/v1/orionis/logs", tags=["Orionis Core"])
async def get_orchestration_logs(limit: int = 20) -> Dict[str, Any]:
    """Retrieve recent orchestration logs from Supabase."""
    try:
        client = await db.connect()
        response = await (
            client.table("orchestration_logs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {
            "count": len(response.data or []),
            "items": response.data or [],
        }
    except Exception as e:
        logger.error(f"Error fetching orchestration logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orchestration logs.",
        )