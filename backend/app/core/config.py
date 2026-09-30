from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CultureChamp API"
    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://culturechamp:culturechamp_local@localhost:5432/culturechamp"
    )
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    source_storage_root: str = "/workspace/.private/sources"
    vector_url: str = "http://localhost:6333"
    model_provider: Literal["fake", "openai_compatible"] = "fake"
    model_api_endpoint: str | None = None
    model_api_name: str | None = None
    model_api_key: SecretStr | None = None
    model_policy_approved: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
