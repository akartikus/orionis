"""Factory de création du bot Discord Orionis.

Expose ``create_bot`` qui instancie un ``commands.Bot`` configuré et
charge automatiquement les extensions (cogs) définies dans ``bot.commands``.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import settings

logger = logging.getLogger(__name__)

# Cogs à charger automatiquement au démarrage du bot.
INITIAL_EXTENSIONS: tuple[str, ...] = (
    "bot.commands.portfolio",
)


class OrionisBot(commands.Bot):
    """Bot Orionis basé sur ``discord.ext.commands.Bot``.

    Le chargement des extensions et la synchronisation des commandes slash
    sont effectués dans ``setup_hook``, déclenché automatiquement par
    ``Client.start()`` (et donc par le ``async with bot:`` utilisé dans
    ``run_bot.py``).
    """

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
        )

        # Handler d'erreur global pour les commandes slash.
        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError,
        ) -> None:
            logger.error(f"Erreur commande slash : {error!r}")
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        "❌ Une erreur est survenue lors du traitement.",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        "❌ Une erreur est survenue lors du traitement.",
                        ephemeral=True,
                    )
            except discord.NotFound:
                logger.warning(
                    "Interaction expirée, impossible de notifier l'utilisateur."
                )

    async def setup_hook(self) -> None:
        """Charge les extensions puis synchronise l'arbre des commandes."""
        for ext in INITIAL_EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info(f"Extension chargée : {ext}")
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Échec du chargement de l'extension {ext}: {exc}")
                raise

        # Synchronisation des commandes slash.
        # Si un GUILD_ID est défini, on copie les commandes globales vers ce
        # serveur puis on synchronise dessus (instantané, idéal en dev) ;
        # sinon on synchronise globalement (peut prendre ~1h de propagation).
        if settings.DISCORD_GUILD_ID:
            guild = discord.Object(id=int(settings.DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synchronisé {len(synced)} commande(s) sur le guild {guild.id}.")
        else:
            synced = await self.tree.sync()
            logger.info(f"Synchronisé {len(synced)} commande(s) globalement.")


def create_bot() -> OrionisBot:
    """Crée et retourne une instance configurée du bot Orionis.

    Le bot n'est pas démarré ici ; l'appelant doit utiliser
    ``async with bot:`` puis ``await bot.start(token)``.
    """
    return OrionisBot()
