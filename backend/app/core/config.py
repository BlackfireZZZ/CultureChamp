from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CultureChamp API"
    app_env: str = "development"
    database_url: str = (
        "postgresql+asyncpg://culturechamp:culturechamp_local@localhost:5432/culturechamp"
    )
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
