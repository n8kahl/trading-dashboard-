from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Core
    APP_NAME: str = "Trading Assistant API"
    APP_ENV: str = "prod"  # prod|dev|test
    APP_TIMEZONE: str = "America/Chicago"

    # External services (optional at startup; warn if missing)
    POLYGON_API_KEY: Optional[str] = None
    CHATDATA_API_KEY: Optional[str] = None
    CHATDATA_CHATBOT_ID: Optional[str] = None

    # Broker (optional for now)
    TRADIER_ACCESS_TOKEN: Optional[str] = None
    TRADIER_ACCOUNT_ID: Optional[str] = None
    TRADIER_ENV: str = "sandbox"
    TRADIER_BASE: str = "https://sandbox.tradier.com"

    # Storage / misc
    DATABASE_URL: Optional[str] = None
    FMP_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    ALERT_POLL_SEC: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

class HealthStatus(BaseModel):
    ok: bool
    warnings: list[str]
    routers: dict
