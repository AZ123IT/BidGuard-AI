from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BidGuard AI"
    database_url: str = "sqlite:///./bidguard.db"
    upload_dir: Path = Path("../data/uploads")
    cors_origins: str = "http://localhost:3000"

    embedding_provider: str = "local"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    embedding_api_key: str | None = None
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "local-hash-v1"
    embedding_dimension: int = Field(default=64, ge=8, le=4096)

    llm_provider: str = "local_fake"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    retrieval_limit: int = Field(default=5, ge=1, le=20)
    min_retrieval_score: float = Field(default=0.05, ge=0.0, le=1.0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_upload_dir(self) -> Path:
        return self.upload_dir.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
