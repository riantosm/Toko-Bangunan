from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str
    app_env: str = "development"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    redis_url: str = "redis://localhost:6379"


settings = Settings()  # type: ignore[call-arg]
