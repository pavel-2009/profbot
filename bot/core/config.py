"""Базовые настройки бота."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Конфигурация бота."""

    BOT_TOKEN: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./profbot.db?timeout=30&check_same_thread=false"
    
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    SHOP_LIST_PAGINATION_SIZE: int = 5
    
    ADMINS: list[int] = []

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


config = Config()
