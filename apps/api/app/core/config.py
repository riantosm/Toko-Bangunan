from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    app_env: str = "development"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "dev-only-insecure-secret-change-me-please-32b+"
    rate_limit_intake_per_min: int = 10
    access_ttl_seconds: int = 28800
    whatsapp_verify_token: str = "dev-verify-token"
    whatsapp_app_secret: str = "dev-app-secret"
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    internal_api_secret: str = "dev-internal-secret"


settings = Settings()  # type: ignore[call-arg]
