"""Базовые настройки бота."""


from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Конфигурация бота."""

    BOT_TOKEN: str | None = None
    DATABASE_URL: str = "sqlite+aiosqlite:///./profbot.db"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


config = Config()