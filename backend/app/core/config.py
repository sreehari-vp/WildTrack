from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")


def _sqlalchemy_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_log_level: str = "info"
    app_cors_origins: str = ""
    database_url: str
    database_migration_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    mongodb_uri: str
    mongodb_database: str = "wildtrack"
    simulation_interval_seconds: float = 5.0

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        return _sqlalchemy_url(self.database_url)

    @property
    def sqlalchemy_migration_url(self) -> str:
        return _sqlalchemy_url(self.database_migration_url or self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
