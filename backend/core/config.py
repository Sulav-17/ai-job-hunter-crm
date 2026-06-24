from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"
    embedding_timeout_seconds: int = Field(default=60, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized != "ollama":
            raise ValueError("EMBEDDING_PROVIDER must be ollama")
        return normalized

    @field_validator("embedding_model", "ollama_base_url")
    @classmethod
    def reject_blank_embedding_setting(cls, value: str) -> str:
        stripped = value.strip()
        if stripped == "":
            raise ValueError("embedding settings cannot be blank")
        return stripped


@lru_cache
def get_settings() -> Settings:
    return Settings()
