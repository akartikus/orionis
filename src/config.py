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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()