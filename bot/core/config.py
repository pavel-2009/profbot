"""Базовые настройки бота."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Конфигурация бота."""

    BOT_TOKEN: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./profbot.db"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


config = Config()
