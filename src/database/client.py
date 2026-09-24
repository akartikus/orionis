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
        if self._client is None:
            return
        client = self._client
        logger.info("Closing Supabase connection...")
        # Le client Supabase de haut niveau n'expose pas de méthode de
        # fermeture unique ; on ferme proprement chaque sous-client async.
        # `auth` et `realtime` sont toujours créés à l'initialisation ;
        # `postgrest`, `storage` et `functions` sont paresseux (on n'accède
        # qu'à l'attribut privé pour ne pas déclencher leur création).
        closers = (
            ("auth", getattr(client.auth, "close", None)),
            ("realtime", getattr(client.realtime, "close", None)),
            ("postgrest", getattr(getattr(client, "_postgrest", None), "aclose", None)),
            ("storage", getattr(getattr(client, "_storage", None), "aclose", None)),
            ("functions", getattr(getattr(client, "_functions", None), "aclose", None)),
        )
        for name, closer in closers:
            if closer is None:
                continue
            try:
                await closer()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error while closing Supabase {name} client: {exc}")
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
    """Dépendance FastAPI : fournit le client Supabase partagé.

    Le client étant un singleton global, on ne le ferme pas après chaque
    requête ; la fermeture se fait via ``await db.disconnect()`` à l'arrêt.
    """
    client = await db.connect()
    yield client