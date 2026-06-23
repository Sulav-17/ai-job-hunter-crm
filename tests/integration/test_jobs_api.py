from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.database.session import session_scope
from backend.main import app
from backend.models.job import JobPosting


JOB_DESCRIPTION = (
    "This fictional job posting describes a practical analytics role focused "
    "on reporting, documentation, stakeholder updates, and data quality checks."
)


@pytest.fixture
def created_job_ids() -> Generator[list[int], None, None]:
    job_ids: list[int] = []
    try:
        yield job_ids
    finally:
        if job_ids:
            with session_scope() as session:
                session.execute(
                    delete(JobPosting).where(
                        JobPosting.id.in_(job_ids),
                    ),
                )
                session.commit()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_job(
    client: TestClient,
    created_job_ids: list[int],
    title: str = "Data Analyst",
) -> dict:
    response = client.post(
        "/jobs",
        json={
            "title": title,
            "company": "Northstar Labs",
            "location": "Toronto, ON",
            "employment_type": "full_time",
            "work_mode": "hybrid",
            "source_url": "https://example.com/jobs/data-analyst",
            "description": JOB_DESCRIPTION,
        },
    )
    assert response.status_code == 201
    job = response.json()
    created_job_ids.append(job["id"])
    return job


@pytest.mark.integration
def test_create_and_retrieve_job(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    created = create_job(client, created_job_ids)

    response = client.get(f"/jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == "Data Analyst"
    assert response.json()["description"] == JOB_DESCRIPTION
    assert response.json()["source_url"] == "https://example.com/jobs/data-analyst"


@pytest.mark.integration
def test_list_jobs_uses_summary_response_and_newest_first_order(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    first = create_job(client, created_job_ids, title="Data Analyst")
    second = create_job(client, created_job_ids, title="Operations Analyst")

    response = client.get("/jobs")

    assert response.status_code == 200
    jobs = response.json()
    created = [job for job in jobs if job["id"] in {first["id"], second["id"]}]
    assert [job["id"] for job in created] == [second["id"], first["id"]]
    for job in created:
        assert "description" not in job
        assert "source_url" not in job


@pytest.mark.integration
def test_partial_update_preserves_omitted_values(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    created = create_job(client, created_job_ids)

    response = client.patch(
        f"/jobs/{created['id']}",
        json={"title": "Senior Data Analyst", "work_mode": "remote"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Senior Data Analyst"
    assert updated["work_mode"] == "remote"
    assert updated["company"] == created["company"]
    assert updated["description"] == created["description"]


@pytest.mark.integration
def test_clearing_nullable_field(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    created = create_job(client, created_job_ids)

    response = client.patch(
        f"/jobs/{created['id']}",
        json={"location": "   ", "source_url": None},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["location"] is None
    assert updated["source_url"] is None


@pytest.mark.integration
def test_delete_job(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    created = create_job(client, created_job_ids)

    delete_response = client.delete(f"/jobs/{created['id']}")
    retrieve_response = client.get(f"/jobs/{created['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert retrieve_response.status_code == 404
    assert retrieve_response.json() == {"detail": "Job not found"}


@pytest.mark.integration
def test_missing_job_returns_404(client: TestClient) -> None:
    response = client.get("/jobs/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


@pytest.mark.integration
def test_invalid_payload_returns_422(client: TestClient) -> None:
    response = client.post(
        "/jobs",
        json={
            "title": "   ",
            "company": "Northstar Labs",
            "employment_type": "",
            "description": "Too short",
        },
    )

    assert response.status_code == 422


@pytest.mark.integration
def test_empty_patch_returns_422(
    client: TestClient,
    created_job_ids: list[int],
) -> None:
    created = create_job(client, created_job_ids)

    response = client.patch(f"/jobs/{created['id']}", json={})

    assert response.status_code == 422
