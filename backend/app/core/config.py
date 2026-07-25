from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelAI"
    SERVICE_NAME: str = "sentinel-ai-backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://sentinel:change_me@localhost:5432/sentinel_ai"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Stored as raw comma-separated strings, not list[str]: pydantic-settings
    # attempts to JSON-decode any list/complex-typed field sourced from an
    # env var or .env entry *before* any field_validator runs, so a plain
    # value like "http://localhost:5173" (not JSON) would crash Settings()
    # at startup. Parsing lazily via a property sidesteps that entirely.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    ALLOWED_HOSTS: str = "*"

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT is Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT is Environment.TESTING

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT is Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()