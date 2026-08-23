from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    google_api_key: str
    google_llm_model: str = "gemini-3.5-flash"

    # Razorpay (test-mode)
    razorpay_key_id: str
    razorpay_key_secret: str

    # Database
    database_url: str

    # LangGraph checkpointer
    checkpoint_db_url: str

    # Server
    port: int
    frontend_url: str

    # Environment
    env: str

    @property
    def is_dev(self) -> bool:
        return self.env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Use as a FastAPI dependency."""
    return Settings()
