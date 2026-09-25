import logging
from typing import Any, Dict, List
import discord
from discord import app_commands
from discord.ext import commands
import httpx

from config import settings

logger = logging.getLogger(__name__)


class PortfolioView(discord.ui.View):
    """Vue interactive Discord avec boutons pour basculer entre Global et Orionis."""

    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Seule la personne ayant exécuté la commande peut interagir.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="🌐 Portefeuille Global", style=discord.ButtonStyle.primary, row=0)
    async def btn_global(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        embed = await fetch_portfolio_embed(managed_only=False)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="🤖 Positions Orionis", style=discord.ButtonStyle.success, row=0)
    async def btn_orionis(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        embed = await fetch_portfolio_embed(managed_only=True)
        await interaction.edit_original_response(embed=embed, view=self)


async def fetch_portfolio_embed(managed_only: bool = False) -> discord.Embed:
    """Interroge l'API FastAPI (GET /api/v1/portfolio) et construit l'Embed Discord."""
    url = f"{settings.FASTAPI_BASE_URL}/api/v1/portfolio"
    params = {"managed_only": managed_only}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        items: List[Dict[str, Any]] = data.get("items", [])

        if not managed_only:
            # --- VUE PORTEFEUILLE GLOBAL ---
            embed = discord.Embed(
                title="🌐 Portefeuille Crypto Global (Bitvavo)",
                color=discord.Color.blue(),
            )
            if not items:
                embed.description = "Aucun actif trouvé dans le portefeuille global."
                return embed

            total_val = 0.0
            rows = []
            for item in items:
                asset = item["asset"]
                qty = float(item["total_quantity"])
                price = float(item.get("current_price") or 0.0)
                if asset in ["EUR", "USDT", "USDC"] and price == 0.0:
                    price = 1.0
                val = qty * price
                total_val += val
                rows.append({"asset": asset, "qty": qty, "price": price, "val": val})

            rows.sort(key=lambda x: x["val"], reverse=True)

            embed.add_field(
                name="💰 Valeur Totale",
                value=f"**{total_val:,.2f} €**".replace(",", " "),
                inline=False,
            )

            lines = [
                f"**{r['asset']}** : {r['qty']:,.4f} × {r['price']:,.2f} € = **{r['val']:,.2f} €** *({(r['val']/total_val*100 if total_val else 0):.1f}%)*"
                for r in rows[:12]
            ]
            embed.add_field(
                name="📈 Actifs principaux",
                value="\n".join(lines) if lines else "Aucune donnée.",
                inline=False,
            )
            embed.set_footer(text="Données fournies via FastAPI • Source Bitvavo")
            return embed

        else:
            # --- VUE POSITIONS ORIONIS ---
            embed = discord.Embed(
                title="🤖 Positions gérées par le Bot Orionis",
                color=discord.Color.green(),
            )
            if not items:
                embed.description = "Aucune position active n'est actuellement gérée par Orionis."
                embed.add_field(
                    name="ℹ️ Statut",
                    value="Le bot n'a exécuté aucun ordre d'achat automatique pour le moment.",
                    inline=False,
                )
                return embed

            total_val = 0.0
            lines = []
            for item in items:
                asset = item["asset"]
                qty = float(item["quantity"])
                buy_price = float(item["avg_buy_price"])
                current_price = float(item.get("current_price") or buy_price)
                val = qty * current_price
                total_val += val
                
                pnl_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0
                pnl_icon = "🟢" if pnl_pct >= 0 else "🔴"

                lines.append(
                    f"**{asset}** : {qty:,.4f} | Achat: {buy_price:,.2f} € | Actuel: {current_price:,.2f} € | {pnl_icon} **{pnl_pct:+.2f}%**"
                )

            embed.add_field(name="💰 Valeur Totale Orionis", value=f"**{total_val:,.2f} €**".replace(",", " "), inline=False)
            embed.add_field(name="📊 Positions Ouvertes", value="\n".join(lines), inline=False)
            embed.set_footer(text="Données fournies via FastAPI • Provenance ORIONIS")
            return embed

    except httpx.HTTPError as err:
        logger.error(f"Erreur HTTP lors de la connexion à l'API FastAPI: {err}")
        return discord.Embed(
            title="❌ API Indisponible",
            description="Impossible de contacter le serveur FastAPI. Vérifie qu'il est bien démarré sur `http://localhost:8000`.",
            color=discord.Color.red(),
        )


class PortfolioCog(commands.Cog):
    """Cog Discord interrogeant l'API FastAPI."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="portfolio",
        description="Affiche le portefeuille (Global / Orionis) via l'API FastAPI.",
    )
    async def show_portfolio(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        embed = await fetch_portfolio_embed(managed_only=False)
        view = PortfolioView(author_id=interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PortfolioCog(bot))