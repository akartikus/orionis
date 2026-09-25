from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ORIONIS"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Bitvavo
    BITVAVO_API_KEY: str
    BITVAVO_API_SECRET: str

    # Discord
    DISCORD_BOT_TOKEN: str
    DISCORD_GUILD_ID: str | None = None

    # LLM
    OPENROUTER_API: str | None = None

    FASTAPI_BASE_URL: str = "http://127.0.0.1:8000"

    # Scheduler (APScheduler) — intervalles en minutes
    SCHEDULER_PORTFOLIO_INTERVAL_MINUTES: int = 5
    SCHEDULER_MARKET_INTERVAL_MINUTES: int = 1
    SCHEDULER_NEWS_INTERVAL_MINUTES: int = 15

    # Assets surveillés par le market sync (comma-separated)
    MARKET_SYNC_ASSETS: str = "BTC,ETH,SOL"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def market_assets_list(self) -> list[str]:
        """Parse la chaîne ``MARKET_SYNC_ASSETS`` en liste d'assets."""
        return [asset.strip() for asset in self.MARKET_SYNC_ASSETS.split(",") if asset.strip()]


settings = Settings()