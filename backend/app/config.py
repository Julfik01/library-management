# backend/app/config.py
# Pydantic BaseSettings loads values from environment variables and optional .env file.
# CLAUDE.md: Settings are injected via Docker Compose environment — .env is gitignored.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"


settings = Settings()
