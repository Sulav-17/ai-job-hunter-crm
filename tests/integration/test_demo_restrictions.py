import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings, get_settings
from backend.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def demo_mode_override() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="postgresql+psycopg://jobhunter:jobhunter_dev@localhost:5433/jobhunter",
        app_mode="demo",
    )
    yield
    app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        (
            "post",
            "/candidates",
            {
                "full_name": "Fictional Blocked Candidate",
                "resume_text": "Fictional text.",
            },
        ),
        ("patch", "/candidates/1", {"headline": "Blocked"}),
        ("delete", "/candidates/1", None),
        (
            "post",
            "/jobs",
            {
                "title": "Blocked Job",
                "company": "Blocked Co",
                "description": "Fictional blocked job description with enough length for validation.",
            },
        ),
        ("patch", "/jobs/1", {"location": "Blocked"}),
        ("delete", "/jobs/1", None),
        ("post", "/candidates/1/parse", None),
        ("post", "/jobs/1/parse", None),
        ("post", "/candidates/1/embedding", None),
        ("post", "/jobs/1/embedding", None),
        ("post", "/candidates/1/jobs/1/match", None),
        ("post", "/candidates/1/jobs/1/semantic-match", None),
        ("post", "/candidates/1/jobs/1/tailoring", {"regenerate": False}),
        ("post", "/applications", {"candidate_id": 1, "job_id": 1}),
        ("patch", "/applications/1", {"status": "applied"}),
        ("delete", "/applications/1", None),
    ],
)
def test_demo_mode_blocks_mutating_and_provider_routes(
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    request = getattr(client, method)

    response = request(path, json=json_body) if json_body is not None else request(path)

    assert response.status_code == 403
    assert response.json() == {"detail": "Demo mode is read-only"}


@pytest.mark.integration
def test_demo_mode_keeps_safe_read_endpoints_available() -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/app-info").json()["app_mode"] == "demo"
    assert client.get("/candidates").status_code == 200
    assert client.get("/jobs").status_code == 200
    assert client.get("/applications").status_code == 200
