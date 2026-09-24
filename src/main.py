import sys
from pydantic import ValidationError
from config import settings


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


if __name__ == "__main__":
    try:
        check_configuration()
    except ValidationError as e:
        print("\n❌ Erreur de validation des variables d'environnement :", file=sys.stderr)
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  • Champ manquant ou invalide : [{field}] — {error['msg']}", file=sys.stderr)
        sys.exit(1)