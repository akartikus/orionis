import logging
from typing import Any, Dict
import ccxt.async_support as ccxt
from config import settings
from database.client import db

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Handles live order execution on Bitvavo using CCXT and logs transactions with origin='ORIONIS' in Supabase."""

    def __init__(self) -> None:
        self.exchange_id = "bitvavo"

    def _get_exchange_client(self) -> ccxt.bitvavo:
        """Instantiate CCXT Bitvavo client with API credentials."""
        return ccxt.bitvavo({
            "apiKey": settings.BITVAVO_API_KEY,
            "secret": settings.BITVAVO_API_SECRET,
            "enableRateLimit": True,
            "options": {"createMarketBuyOrderRequiresPrice": False},
        })

    async def execute_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
    ) -> Dict[str, Any]:
        """Execute a live market order (BUY or SELL) on Bitvavo and sync Supabase tables.

        Args:
            symbol: Pair symbol, e.g., 'BTC/EUR'.
            side: 'buy' or 'sell'.
            amount: Quantity of asset to trade.

        Returns:
            Dict containing execution details and order status.
        """
        side = side.lower()
        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid order side '{side}'. Must be 'buy' or 'sell'.")

        exchange = self._get_exchange_client()
        try:
            logger.info(f"🚀 Executing MARKET {side.upper()} order on Bitvavo: {amount} {symbol}")
            
            # 1. Place order on Bitvavo REST API
            order = await exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
            )
            
            bitvavo_order_id = str(order.get("id", ""))
            price = float(order.get("average") or order.get("price") or 0.0)
            cost = float(order.get("cost") or (amount * price))
            asset = symbol.split("/")[0]

            logger.info(f"✅ Order executed on Bitvavo. ID: {bitvavo_order_id} | Price: {price:.2f} EUR | Cost: {cost:.2f} EUR")

            # 2. Record execution in Supabase transactions_log with origin='ORIONIS'
            await self._log_transaction(
                symbol=symbol,
                side=side,
                order_type="market",
                amount=amount,
                price=price,
                cost=cost,
                bitvavo_order_id=bitvavo_order_id,
            )

            # 3. Update 'bot_managed_assets' sub-portfolio in Supabase
            await self._update_bot_managed_assets(
                asset=asset,
                side=side,
                amount=amount,
                price=price,
            )

            return {
                "status": "success",
                "bitvavo_order_id": bitvavo_order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "cost": cost,
                "origin": "ORIONIS",
            }

        except Exception as e:
            logger.error(f"❌ Order execution failed for {symbol}: {e}")
            raise e
        finally:
            await exchange.close()

    async def _log_transaction(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: float,
        cost: float,
        bitvavo_order_id: str,
    ) -> None:
        """Insert transaction log into Supabase with origin='ORIONIS'."""
        client = await db.connect()
        transaction_data = {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "amount": amount,
            "price": price,
            "cost": cost,
            "bitvavo_order_id": bitvavo_order_id,
            "origin": "ORIONIS",
        }
        await client.table("transactions_log").insert(transaction_data).execute()
        logger.info("📝 Transaction logged in Supabase with origin='ORIONIS'.")

    async def _update_bot_managed_assets(
        self,
        asset: str,
        side: str,
        amount: float,
        price: float,
    ) -> None:
        """Update or delete entries in 'bot_managed_assets' based on execution."""
        client = await db.connect()
        
        # Check if asset already exists in bot_managed_assets
        res = await client.table("bot_managed_assets").select("*").eq("asset", asset).execute()
        existing = res.data[0] if res.data else None

        if side == "buy":
            if existing:
                old_qty = float(existing["quantity"])
                old_avg_price = float(existing["avg_buy_price"])
                new_qty = old_qty + amount
                new_avg_price = ((old_qty * old_avg_price) + (amount * price)) / new_qty
                
                await client.table("bot_managed_assets").update({
                    "quantity": new_qty,
                    "avg_buy_price": new_avg_price,
                    "current_price": price,
                }).eq("asset", asset).execute()
            else:
                await client.table("bot_managed_assets").insert({
                    "asset": asset,
                    "quantity": amount,
                    "avg_buy_price": price,
                    "current_price": price,
                    "origin": "ORIONIS",
                }).execute()

        elif side == "sell":
            if existing:
                old_qty = float(existing["quantity"])
                new_qty = old_qty - amount
                
                if new_qty <= 1e-6:  # Position fully closed
                    await client.table("bot_managed_assets").delete().eq("asset", asset).execute()
                    logger.info(f"🗑️ Closed position for {asset} in bot_managed_assets.")
                else:
                    await client.table("bot_managed_assets").update({
                        "quantity": new_qty,
                        "current_price": price,
                    }).eq("asset", asset).execute()


# Instanciation globale de l'exécuteur
order_executor = OrderExecutor()