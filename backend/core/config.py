from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_mode: str = "local"
    database_url: str
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"
    embedding_timeout_seconds: int = Field(default=60, gt=0)
    generation_provider: str = "ollama"
    generation_model: str = "qwen3:4b"
    generation_timeout_seconds: int = Field(default=120, gt=0)
    demo_seed_on_startup: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_mode")
    @classmethod
    def validate_app_mode(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"local", "demo"}:
            raise ValueError("APP_MODE must be local or demo")
        return normalized

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized != "ollama":
            raise ValueError("EMBEDDING_PROVIDER must be ollama")
        return normalized

    @field_validator("generation_provider")
    @classmethod
    def validate_generation_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized != "ollama":
            raise ValueError("GENERATION_PROVIDER must be ollama")
        return normalized

    @field_validator("embedding_model", "ollama_base_url", "generation_model")
    @classmethod
    def reject_blank_provider_setting(cls, value: str) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError("provider settings cannot be blank")
        return stripped


@lru_cache
def get_settings() -> Settings:
    return Settings()
