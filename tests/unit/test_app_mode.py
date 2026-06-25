from pydantic import ValidationError
import pytest

from backend.core.config import Settings
from backend.core.mode import app_info_payload


def _settings(**overrides) -> Settings:
    values = {"database_url": "postgresql+psycopg://user:pass@localhost:5432/db"}
    values.update(overrides)
    return Settings(**values)


def test_app_mode_defaults_to_local() -> None:
    settings = _settings()

    assert settings.app_mode == "local"
    assert app_info_payload(settings) == {
        "app_mode": "local",
        "read_only": False,
        "demo_data": False,
    }


def test_app_mode_accepts_explicit_local_and_demo_with_normalization() -> None:
    assert _settings(app_mode=" LOCAL ").app_mode == "local"
    assert _settings(app_mode=" Demo ").app_mode == "demo"


def test_invalid_app_mode_fails_clearly() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(app_mode="production")

    assert "APP_MODE must be local or demo" in str(exc_info.value)


def test_demo_app_info_exposes_only_safe_fields() -> None:
    payload = app_info_payload(_settings(app_mode="demo"))

    assert payload["app_mode"] == "demo"
    assert payload["read_only"] is True
    assert payload["demo_data"] is True
    assert payload["notice"] == "This demonstration contains fictional, precomputed data."
    assert "database_url" not in payload
    assert "ollama_base_url" not in payload
    assert "embedding_model" not in payload
