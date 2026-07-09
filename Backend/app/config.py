from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./fx_dashboard.db"

    # Market data provider: "twelvedata" (real intraday) or "frankfurter" (daily ECB only).
    MARKET_DATA_PROVIDER: str = "frankfurter"
    FX_API_BASE_URL: str = "https://api.frankfurter.dev/v1"
    TWELVE_DATA_API_KEY: str = ""
    TWELVE_DATA_BASE_URL: str = "https://api.twelvedata.com"

    DEFAULT_PAIRS: str = "GBP/USD,EUR/USD,USD/INR,EUR/GBP"
    SNAPSHOT_INTERVAL_MINUTES: int = 60
    ALERT_THRESHOLD_PERCENT: float = 1.0
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # LLM for plain-English "why did it move" explanations.
    # Provider: "gemini" (free tier) or "anthropic".
    LLM_PROVIDER: str = "gemini"

    # Google Gemini (free tier, no credit card).
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # Anthropic (optional alternative).
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5"

    # News + explanation behaviour.
    NEWS_MAX_ARTICLES: int = 8
    EXPLANATION_CACHE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()