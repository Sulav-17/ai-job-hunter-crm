import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from backend.database.health import check_database_ready
from backend.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_readiness_endpoint_returns_ready_when_database_is_available() -> None:
    def ready_database() -> dict[str, str]:
        return {"status": "ready", "database": "ok"}

    app.dependency_overrides[check_database_ready] = ready_database

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_endpoint_returns_503_when_database_is_unavailable() -> None:
    def unavailable_database() -> dict[str, str]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    app.dependency_overrides[check_database_ready] = unavailable_database

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
