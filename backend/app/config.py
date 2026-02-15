from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ZonalHub API"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    database_url: str = "sqlite:///./zonalhub.db"
    default_page_size: int = 25
    max_page_size: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()

