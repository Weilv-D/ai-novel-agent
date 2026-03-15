"""Application configuration."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AI Novel Agent API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/novel_agent"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://localhost:3001"]

    # API Keys
    secret_key: str = "change-this-in-production-min-32-chars-long"
    api_key_header: str = "X-API-Key"
    admin_api_key: str = ""

    # LLM (Chat)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.7
    agent_skills_dir: str = ""

    # Embedding (defaults to same provider as chat if not set)
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Ensure embedding dimensions are positive."""
        if v <= 0:
            raise ValueError("embedding_dimension must be > 0")
        return v

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, v: bool | str | int) -> bool:
        """Handle common boolean spellings and shell DEBUG values safely."""
        if isinstance(v, bool):
            return v

        if isinstance(v, int):
            return v != 0

        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if value in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False

        raise ValueError("debug must be a boolean-compatible value")

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
