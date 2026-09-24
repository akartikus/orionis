import logging
from typing import Any, Dict, List
import discord
from discord import app_commands
from discord.ext import commands

from database.client import db

logger = logging.getLogger(__name__)


class PortfolioView(discord.ui.View):
    """Vue interactive Discord contenant les boutons de bascule de portefeuille."""

    def __init__(self, author_id: int):
        super().__init__(timeout=120)  # Désactive les boutons après 2 minutes
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """S'assure que seul l'auteur de la commande peut cliquer sur les boutons."""
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
        embed = await fetch_global_portfolio_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="🤖 Positions Orionis", style=discord.ButtonStyle.success, row=0)
    async def btn_orionis(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        embed = await fetch_orionis_portfolio_embed()
        await interaction.edit_original_response(embed=embed, view=self)


async def fetch_global_portfolio_embed() -> discord.Embed:
    """Génère l'embed du portefeuille global (table: portfolio)."""
    try:
        supabase = await db.connect()
        res = await supabase.table("portfolio").select("*").execute()
        items: List[Dict[str, Any]] = res.data or []

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
        embed.set_footer(text="Données synchronisées depuis Bitvavo")
        return embed

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du portfolio global: {e}")
        return discord.Embed(title="❌ Erreur", description="Impossible de lire le portefeuille global.", color=discord.Color.red())


async def fetch_orionis_portfolio_embed() -> discord.Embed:
    """Génère l'embed des positions gérées par le Bot (table: bot_managed_assets)."""
    try:
        supabase = await db.connect()
        res = await supabase.table("bot_managed_assets").select("*").execute()
        items: List[Dict[str, Any]] = res.data or []

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
        embed.set_footer(text="Uniquement les positions initiées avec provenance='ORIONIS'")
        return embed

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des positions Orionis: {e}")
        return discord.Embed(title="❌ Erreur", description="Impossible de lire les positions Orionis.", color=discord.Color.red())


class PortfolioCog(commands.Cog):
    """Cog principal pour l'affichage du portefeuille."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="portfolio",
        description="Affiche le portefeuille avec boutons de bascule (Global / Orionis).",
    )
    async def show_portfolio(self, interaction: discord.Interaction) -> None:
        """Commande Slash /portfolio."""
        # Une interaction expire après ~3s sans réponse initiale. Si le bot
        # était occupé (ex: setup_hook au démarrage), defer() peut échouer.
        try:
            await interaction.response.defer(thinking=True)
            responded = True
        except discord.NotFound:
            logger.warning(
                "Interaction /portfolio expirée avant defer (délai > 3s)."
            )
            responded = False

        # Affiche le portefeuille global par défaut
        embed = await fetch_global_portfolio_embed()
        view = PortfolioView(author_id=interaction.user.id)

        if responded:
            await interaction.followup.send(embed=embed, view=view)
        else:
            logger.error(
                "Impossible de répondre à /portfolio : interaction expirée. "
                "Réessayez la commande une fois le bot prêt."
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PortfolioCog(bot))