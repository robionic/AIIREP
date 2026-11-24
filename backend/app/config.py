from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Industrial Reverse Engineering Platform API"
    database_url: str = "sqlite:///./aiirep.db"
    redis_url: str = "redis://redis:6379/0"
    storage_path: str = "./data/uploads"
    max_upload_bytes: int = 500 * 1024 * 1024
    cors_origins: str = "http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
