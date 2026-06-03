from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./fx_dashboard.db"
    FX_API_BASE_URL: str = "https://api.frankfurter.dev/v2"
    DEFAULT_PAIRS: str = "GBP/USD,EUR/USD,USD/INR,EUR/GBP"
    SNAPSHOT_INTERVAL_MINUTES: int = 60
    ALERT_THRESHOLD_PERCENT: float = 1.0
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()