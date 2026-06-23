from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.database.session import session_scope
from backend.main import app
from backend.models.candidate import CandidateProfile


@pytest.fixture
def created_candidate_ids() -> Generator[list[int], None, None]:
    candidate_ids: list[int] = []
    try:
        yield candidate_ids
    finally:
        if candidate_ids:
            with session_scope() as session:
                session.execute(
                    delete(CandidateProfile).where(
                        CandidateProfile.id.in_(candidate_ids),
                    ),
                )
                session.commit()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_candidate(
    client: TestClient,
    created_candidate_ids: list[int],
    full_name: str = "Avery Stone",
) -> dict:
    response = client.post(
        "/candidates",
        json={
            "full_name": full_name,
            "headline": "Data Analyst",
            "location": "Toronto, ON",
            "professional_summary": "Fictional analyst profile for tests.",
            "years_experience": 4,
            "resume_text": "Fictional resume text for candidate API tests.",
        },
    )
    assert response.status_code == 201
    candidate = response.json()
    created_candidate_ids.append(candidate["id"])
    return candidate


@pytest.mark.integration
def test_create_and_retrieve_candidate(
    client: TestClient,
    created_candidate_ids: list[int],
) -> None:
    created = create_candidate(client, created_candidate_ids)

    response = client.get(f"/candidates/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["full_name"] == "Avery Stone"
    assert response.json()["resume_text"] == (
        "Fictional resume text for candidate API tests."
    )


@pytest.mark.integration
def test_list_candidates_uses_summary_response(
    client: TestClient,
    created_candidate_ids: list[int],
) -> None:
    first = create_candidate(client, created_candidate_ids, full_name="Avery Stone")
    second = create_candidate(client, created_candidate_ids, full_name="Blair Reed")

    response = client.get("/candidates")

    assert response.status_code == 200
    candidates = response.json()
    created = [
        candidate
        for candidate in candidates
        if candidate["id"] in {first["id"], second["id"]}
    ]
    assert [candidate["id"] for candidate in created] == [first["id"], second["id"]]
    for candidate in created:
        assert "professional_summary" not in candidate
        assert "resume_text" not in candidate


@pytest.mark.integration
def test_partial_update_preserves_omitted_values(
    client: TestClient,
    created_candidate_ids: list[int],
) -> None:
    created = create_candidate(client, created_candidate_ids)

    response = client.patch(
        f"/candidates/{created['id']}",
        json={"headline": None, "years_experience": 5},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["headline"] is None
    assert updated["years_experience"] == 5
    assert updated["full_name"] == created["full_name"]
    assert updated["location"] == created["location"]


@pytest.mark.integration
def test_delete_candidate(
    client: TestClient,
    created_candidate_ids: list[int],
) -> None:
    created = create_candidate(client, created_candidate_ids)

    delete_response = client.delete(f"/candidates/{created['id']}")
    retrieve_response = client.get(f"/candidates/{created['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert retrieve_response.status_code == 404
    assert retrieve_response.json() == {"detail": "Candidate not found"}


@pytest.mark.integration
def test_missing_candidate_returns_404(client: TestClient) -> None:
    response = client.get("/candidates/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Candidate not found"}


@pytest.mark.integration
def test_invalid_payload_returns_422(client: TestClient) -> None:
    response = client.post(
        "/candidates",
        json={
            "full_name": "   ",
            "years_experience": 81,
            "unknown": "field",
        },
    )

    assert response.status_code == 422
