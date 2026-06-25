import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings, get_settings
from backend.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _settings(app_mode: str) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        app_mode=app_mode,
    )


def test_app_info_local_response() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings("local")

    response = client.get("/app-info")

    assert response.status_code == 200
    assert response.json() == {
        "app_mode": "local",
        "read_only": False,
        "demo_data": False,
    }


def test_app_info_demo_response_exposes_no_sensitive_configuration() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings("demo")

    response = client.get("/app-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "app_mode": "demo",
        "read_only": True,
        "demo_data": True,
        "notice": "This demonstration contains fictional, precomputed data.",
    }
    forbidden_keys = {"database_url", "ollama_base_url", "embedding_model", "generation_model"}
    assert forbidden_keys.isdisjoint(payload)
