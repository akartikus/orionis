import logging
from typing import AsyncGenerator, Optional
from supabase import AsyncClient, create_async_client
from config import settings

logger = logging.getLogger(__name__)


class SupabaseDatabase:

    def __init__(self) -> None:
        self._client: Optional[AsyncClient] = None

    async def connect(self) -> AsyncClient:
        if self._client is None:
            try:
                logger.info("Init connection to Supabase ORIONIS...")
                self._client = await create_async_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY,
                )
                logger.info("Supabase connection Success.")
            except Exception as e:
                logger.error(f"Supabase connection Error: {e}")
                raise e
        return self._client

    async def disconnect(self) -> None:
        if self._client is not None:
            logger.info("Closing Supabase connection...")
            # Supabase utilise un client httpx interne qui gère sa propre fermeture
            self._client = None
            logger.info("Connection Supabase closed.")

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "Client Supabase not initialised "
                "Call `await db.connect()` before reaching client."
            )
        return self._client


# Instance globale partagée
db = SupabaseDatabase()


async def get_db_client() -> AsyncGenerator[AsyncClient, None]:
    client = await db.connect()
    try:
        yield client
    finally:
        pass