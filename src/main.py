import asyncio
import logging
import sys
from pydantic import ValidationError

from config import settings
from database.client import db


def check_configuration() -> None:
    print("🔍 Vérification de la configuration...")

    # Dictionnaire des configurations à vérifier avec masquage des secrets
    configs = {
        "Environnement": settings.ENVIRONMENT,
        "Niveau de log": settings.LOG_LEVEL,
        "URL Supabase": settings.SUPABASE_URL,
        "Clé Supabase": (
            f"{settings.SUPABASE_KEY[:6]}...***"
            if settings.SUPABASE_KEY
            else "Non définie"
        ),
        "Clé API Bitvavo": (
            f"{settings.BITVAVO_API_KEY[:6]}...***"
            if settings.BITVAVO_API_KEY
            else "Non définie"
        ),
        "Secret Bitvavo": "******" if settings.BITVAVO_API_SECRET else "Non défini",
        "Token Discord": (
            f"{settings.DISCORD_BOT_TOKEN[:6]}...***"
            if settings.DISCORD_BOT_TOKEN
            else "Non défini"
        ),
        "ID Guilde Discord": settings.DISCORD_GUILD_ID or "Optionnel (non défini)",
        "Clé API OpenAI": (
            f"{settings.OPENROUTER_API[:6]}...***"
            if settings.OPENROUTER_API
            else "Optionnel (non définie)"
        ),
    }

    print("\n✅ Configuration chargée avec succès :\n")
    for key, value in configs.items():
        print(f"  • {key:<20} : {value}")

    print("\n🚀 Le socle de configuration de la Phase 0 est prêt !")


async def test_database_connection() -> bool:
    """Teste la connexion à la base de données Supabase.

    Effectue un véritable appel réseau (liste des buckets Storage) afin de
    valider la connectivité au endpoint Supabase et l'authentification via la
    clé configurée. Retourne ``True`` en cas de succès, ``False`` sinon.
    """
    print("\n🔌 Test de la connexion à Supabase...")

    try:
        client = await db.connect()
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ Échec de l'initialisation du client Supabase : {exc}")
        return False

    try:
        # Appel réseau réel : liste des buckets Storage.
        # Ne dépend pas d'une table spécifique et valide la clé (service_role).
        buckets = await client.storage.list_buckets()
        print(
            f"  ✅ Connexion Supabase établie — "
            f"{len(buckets)} bucket(s) Storage accessible(s)."
        )
        for bucket in buckets:
            print(f"     • {bucket.name}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ Échec de la requête Supabase : {exc}")
        return False
    finally:
        await db.disconnect()


if __name__ == "__main__":
    # Configuration du logging pour afficher les logs du module database.client
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    try:
        check_configuration()
    except ValidationError as e:
        print("\n❌ Erreur de validation des variables d'environnement :", file=sys.stderr)
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  • Champ manquant ou invalide : [{field}] — {error['msg']}", file=sys.stderr)
        sys.exit(1)

    connection_ok = asyncio.run(test_database_connection())
    if not connection_ok:
        print("\n❌ Le test de connexion à la base de données a échoué.", file=sys.stderr)
        sys.exit(1)

    print("\n🚀 Le socle de configuration et de base de données est prêt !")