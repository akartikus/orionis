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
    LLM_PROVIDER: str = "openrouter"  # 'openrouter' | 'openai' | 'local'
    LLM_DEFAULT_MODEL: str = "z-ai/glm-5"  # modèle par défaut (GLM-5 via OpenRouter)
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT_SECONDS: float = 30.0
    OPENAI_API_KEY: str | None = None  # requis si LLM_PROVIDER=openai
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # requis si LLM_PROVIDER=local
    # Raisonnement (modèles reasoning comme GLM-5). False = sorties fiables,
    # rapides et économiques (recommandé pour un bot de trading) ; True active
    # le raisonnement pour les analyses complexes (coûte plus de tokens).
    LLM_REASONING_ENABLED: bool = False
    LLM_REASONING_EFFORT: str | None = None  # 'low' | 'high' | 'max' (si activé)

    FASTAPI_BASE_URL: str = "http://127.0.0.1:8000"

    # Scheduler (APScheduler) — intervalles en minutes
    SCHEDULER_PORTFOLIO_INTERVAL_MINUTES: int = 5
    SCHEDULER_MARKET_INTERVAL_MINUTES: int = 1
    SCHEDULER_NEWS_INTERVAL_MINUTES: int = 15

    # Assets surveillés par le market sync (comma-separated)
    MARKET_SYNC_ASSETS: str = "BTC,ETH,SOL"

    # Orionis Core — configuration du workflow quotidien et des seuils d'alerte
    DAILY_ANALYSIS_HOUR: int = 8
    DAILY_ANALYSIS_MINUTE: int = 0
    PRICE_DROP_THRESHOLD_PCT: float = 8.0
    PRICE_SURGE_THRESHOLD_PCT: float = 8.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def market_assets_list(self) -> list[str]:
        """Parse la chaîne ``MARKET_SYNC_ASSETS`` en liste d'assets."""
        return [asset.strip() for asset in self.MARKET_SYNC_ASSETS.split(",") if asset.strip()]


settings = Settings()