import asyncio
import logging
import sys
from pathlib import Path

# Add 'src' directory to python path
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Now imports will work cleanly
from bot.client import create_bot
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)


async def main() -> None:
    if not settings.DISCORD_BOT_TOKEN:
        logging.error("DISCORD_BOT_TOKEN missing in .env file.")
        return

    bot = create_bot()
    async with bot:
        await bot.start(settings.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())