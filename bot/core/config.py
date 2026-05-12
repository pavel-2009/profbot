"""Базовые настройки бота."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Конфигурация бота."""

    BOT_TOKEN: str | None = None
    PAYMENT_TOKEN: str | None = None
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/profbot"
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "profbot"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    SHOP_LIST_PAGINATION_SIZE: int = 5
    
    ADMINS: list[int] = []

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


config = Config()


def validate_runtime_config() -> None:
    """Проверить обязательные настройки перед запуском бота."""
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required. Set it in .env or environment variables.")
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required.")
    if not config.PAYMENT_TOKEN:
        raise RuntimeError("PAYMENT_TOKEN is required. Set it in .env or environment variables.")