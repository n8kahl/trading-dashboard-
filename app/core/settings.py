import os
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    # Core
    APP_NAME: str = os.getenv("APP_NAME", "Trading Assistant API")
    APP_ENV: str = os.getenv("APP_ENV", "prod")  # prod|dev|test
    APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "America/Chicago")

    # External services (optional at startup; warn if missing)
    POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY")
    CHATDATA_API_KEY: Optional[str] = os.getenv("CHATDATA_API_KEY")
    CHATDATA_CHATBOT_ID: Optional[str] = os.getenv("CHATDATA_CHATBOT_ID")

    # Broker (optional for now)
    TRADIER_ACCESS_TOKEN: Optional[str] = os.getenv("TRADIER_ACCESS_TOKEN")
    TRADIER_ACCOUNT_ID: Optional[str] = os.getenv("TRADIER_ACCOUNT_ID")
    TRADIER_ENV: str = os.getenv("TRADIER_ENV", "sandbox")
    TRADIER_BASE: Optional[str] = os.getenv("TRADIER_BASE")

    @property
    def tradier_base_url(self) -> str:
        """Return the Tradier API base URL without a trailing slash.

        If ``TRADIER_BASE`` is unset, choose between the sandbox and
        production API hosts based on ``TRADIER_ENV``.
        """
        base = self.TRADIER_BASE
        if not base:
            base = "https://sandbox.tradier.com" if self.TRADIER_ENV == "sandbox" else "https://api.tradier.com"
        return base.rstrip("/")

    # Storage / misc
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    FMP_API_KEY: Optional[str] = os.getenv("FMP_API_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")
    ALERT_POLL_SEC: int = int(os.getenv("ALERT_POLL_SEC", "15"))


settings = Settings()


class HealthStatus(BaseModel):
    ok: bool
    warnings: list[str]
    routers: dict
