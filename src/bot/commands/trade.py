import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import httpx

from config import settings

logger = logging.getLogger(__name__)


class TradeConfirmView(discord.ui.View):
    """Vue de confirmation d'ordre avant envoi à l'API FastAPI."""

    def __init__(self, author_id: int, symbol: str, side: str, amount: float):
        super().__init__(timeout=60)  # L'ordre expire après 60 secondes sans action
        self.author_id = author_id
        self.symbol = symbol.upper()
        self.side = side.lower()
        self.amount = amount

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """S'assure que seul l'auteur de la commande peut valider ou annuler."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Vous n'êtes pas l'initiateur de cet ordre.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirmer l'ordre", style=discord.ButtonStyle.danger, row=0)
    async def confirm_trade(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()

        # Désactiver les boutons immédiatement après le clic
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        url = f"{settings.FASTAPI_BASE_URL}/api/v1/trade"
        payload = {
            "symbol": self.symbol,
            "side": self.side,
            "amount": self.amount,
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=15.0)
                
            if res.status_code == 200:
                data = res.json()
                embed = discord.Embed(
                    title="🚀 Ordre Exécuté avec Succès",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Paire", value=f"**{data['symbol']}**", inline=True)
                embed.add_field(name="Sens", value=f"**{data['side'].upper()}**", inline=True)
                embed.add_field(name="Quantité", value=f"**{data['amount']}**", inline=True)
                embed.add_field(name="Prix Moyen", value=f"**{data['price']:,.2f} €**", inline=True)
                embed.add_field(name="Coût Total", value=f"**{data['cost']:,.2f} €**", inline=True)
                embed.add_field(name="ID Bitvavo", value=f"`{data['bitvavo_order_id']}`", inline=False)
                embed.set_footer(text="Exécuté via Bitvavo • Marquage origin='ORIONIS'")

                await interaction.edit_original_response(embed=embed, view=self)
            else:
                detail = res.json().get("detail", "Erreur inconnue")
                embed = discord.Embed(
                    title="❌ Échec de l'exécution",
                    description=f"L'API a rejeté l'ordre :\n```{detail}```",
                    color=discord.Color.red(),
                )
                await interaction.edit_original_response(embed=embed, view=self)

        except Exception as e:
            logger.error(f"Erreur HTTP lors de l'exécution du trade : {e}")
            embed = discord.Embed(
                title="❌ Erreur Réseau",
                description="Impossible de contacter le serveur FastAPI.",
                color=discord.Color.red(),
            )
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.secondary, row=0)
    async def cancel_trade(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        embed = discord.Embed(
            title="🛑 Ordre Annulé",
            description="L'ordre a été abandonné par l'utilisateur.",
            color=discord.Color.greyple(),
        )
        await interaction.edit_original_response(embed=embed, view=self)


class TradeCog(commands.Cog):
    """Cog gérant les ordres de trading manuels depuis Discord."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="trade",
        description="Passe un ordre au marché sur Bitvavo (avec confirmation).",
    )
    @app_commands.describe(
        symbol="La paire de trading (ex: BTC/EUR, ETH/EUR, SOL/EUR)",
        side="Le sens de l'ordre : buy (achat) ou sell (vente)",
        amount="La quantité de l'actif à échanger (ex: 0.001 pour du BTC)",
    )
    @app_commands.choices(
        side=[
            app_commands.Choice(name="Achat (BUY)", value="buy"),
            app_commands.Choice(name="Vente (SELL)", value="sell"),
        ]
    )
    async def execute_trade(
        self,
        interaction: discord.Interaction,
        symbol: str,
        side: app_commands.Choice[str],
        amount: float,
    ) -> None:
        """Commande Slash /trade symbol side amount."""
        side_val = side.value
        symbol_formatted = symbol.upper().strip()

        if "/" not in symbol_formatted:
            symbol_formatted = f"{symbol_formatted}/EUR"

        # Embed de récapitulatif avant confirmation
        color = discord.Color.gold() if side_val == "buy" else discord.Color.orange()
        embed = discord.Embed(
            title="⚠️ Confirmation d'Ordre de Trading",
            description="Veuillez vérifier les détails de l'ordre avant de valider l'exécution sur Bitvavo.",
            color=color,
        )
        embed.add_field(name="Paire", value=f"**{symbol_formatted}**", inline=True)
        embed.add_field(name="Sens", value=f"**{side_val.upper()}**", inline=True)
        embed.add_field(name="Quantité", value=f"**{amount}**", inline=True)
        embed.set_footer(text="Cet ordre sera exécuté immédiatement au PRIX DU MARCHÉ.")

        view = TradeConfirmView(
            author_id=interaction.user.id,
            symbol=symbol_formatted,
            side=side_val,
            amount=amount,
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TradeCog(bot))
