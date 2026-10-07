from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Non-secret values come from a ConfigMap, the
    database URL (which contains the password) from a Secret."""

    app_name: str = "SpendWise API"
    app_version: str = "1.0.0"
    app_env: str = "local"
    log_level: str = "info"
    currency: str = "INR"
    database_url: str = "postgresql+psycopg://spendwise:spendwise@localhost:5432/spendwise"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
