from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GroupSync"
    api_prefix: str = "/api/v1"

    secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    database_url: str = "sqlite:///./groupsync.db"

    # NoDecode: accept a plain comma-separated string instead of JSON
    cors_origins: Annotated[list[str], NoDecode] = ["*"]

    upload_dir: str = "./uploads"
    max_upload_mb: int = 10

    scheduler_enabled: bool = True
    deadline_check_interval_minutes: int = 60
    expo_push_url: str = "https://exp.host/--/api/v2/push/send"

    group_max_members: int = 10

    login_max_attempts: int = 5
    login_window_seconds: int = 900

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
