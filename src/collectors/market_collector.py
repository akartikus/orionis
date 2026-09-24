import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
import ccxt.async_support as ccxt
from config import settings
from database.client import db

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Utility class to calculate technical analysis indicators from OHLCV data."""

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average (SMA)."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average (EMA)."""
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Initial SMA seed
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index (RSI)."""
        if len(prices) < period + 1:
            return None

        gains: List[float] = []
        losses: List[float] = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change >= 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(abs(change))
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    @classmethod
    def calculate_macd(
        cls, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, Optional[float]]:
        """Calculate Moving Average Convergence Divergence (MACD)."""
        if len(prices) < slow + signal:
            return {"macd": None, "signal": None, "histogram": None}

        macd_line: List[float] = []
        multiplier_fast = 2 / (fast + 1)
        multiplier_slow = 2 / (slow + 1)

        ema_fast = sum(prices[:fast]) / fast
        ema_slow = sum(prices[:slow]) / slow

        for i in range(max(fast, slow), len(prices)):
            ema_fast = (prices[i] - ema_fast) * multiplier_fast + ema_fast
            ema_slow = (prices[i] - ema_slow) * multiplier_slow + ema_slow
            macd_line.append(ema_fast - ema_slow)

        if len(macd_line) < signal:
            return {"macd": None, "signal": None, "histogram": None}

        signal_line = sum(macd_line[:signal]) / signal
        multiplier_signal = 2 / (signal + 1)
        for val in macd_line[signal:]:
            signal_line = (val - signal_line) * multiplier_signal + signal_line

        latest_macd = macd_line[-1]
        histogram = latest_macd - signal_line

        return {
            "macd": round(latest_macd, 4),
            "signal": round(signal_line, 4),
            "histogram": round(histogram, 4),
        }


class MarketCollector:
    """Collector responsible for fetching tickers, candles, and storing market snapshots."""

    def __init__(self) -> None:
        self.exchange = ccxt.bitvavo(
            {
                "apiKey": settings.BITVAVO_API_KEY,
                "secret": settings.BITVAVO_API_SECRET,
                "enableRateLimit": True,
            }
        )

    async def fetch_and_store_snapshot(
        self, asset: str, timeframe: str = "1h", limit: int = 250
    ) -> None:
        """Fetch market data and indicators for a specific asset and store a snapshot."""
        symbol = f"{asset}/EUR"
        try:
            logger.info(f"Fetching market ticker and candles for {symbol}...")
            
            # Fetch current ticker
            ticker = await self.exchange.fetch_ticker(symbol)
            price = Decimal(str(ticker.get("last", 0.0)))
            volume_24h = Decimal(str(ticker.get("baseVolume", 0.0)))

            # Fetch OHLCV candles
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            close_prices = [candle[4] for candle in ohlcv]

            # Calculate technical indicators
            rsi = TechnicalIndicators.calculate_rsi(close_prices, period=14)
            macd_data = TechnicalIndicators.calculate_macd(close_prices)
            ema_20 = TechnicalIndicators.calculate_ema(close_prices, period=20)
            sma_50 = TechnicalIndicators.calculate_sma(close_prices, period=50)
            sma_200 = TechnicalIndicators.calculate_sma(close_prices, period=200)

            indicators: Dict[str, Any] = {
                "timeframe": timeframe,
                "rsi": rsi,
                "macd": macd_data["macd"],
                "macd_signal": macd_data["signal"],
                "macd_histogram": macd_data["histogram"],
                "ema_20": round(ema_20, 4) if ema_20 else None,
                "sma_50": round(sma_50, 4) if sma_50 else None,
                "sma_200": round(sma_200, 4) if sma_200 else None,
            }

            client = await db.connect()
            snapshot_payload = {
                "asset": asset,
                "price": str(price),
                "volume_24h": str(volume_24h),
                "market_cap": None,  # Can be populated via CoinGecko if needed
                "indicators": indicators,
            }

            await client.table("market_snapshots").insert(snapshot_payload).execute()
            logger.info(f"Successfully saved market snapshot for {asset} (RSI: {rsi}).")

        except Exception as e:
            logger.error(f"Failed to fetch market snapshot for {asset}: {e}")
            raise e

    async def close(self) -> None:
        """Close CCXT exchange HTTP session."""
        await self.exchange.close()


async def run_market_sync(assets: List[str]) -> None:
        """Convenience runner function to fetch snapshots for a list of assets."""
        collector = MarketCollector()
        try:
            for asset in assets:
                if asset == "EUR":
                    continue
                await collector.fetch_and_store_snapshot(asset)
        finally:
            await collector.close()