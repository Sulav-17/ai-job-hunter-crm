from __future__ import annotations

import httpx
import pytest

from frontend.api_client import ApiClient, ApiClientError, ApiUnavailableError
from frontend.components import is_demo_mode, is_read_only
from frontend.navigation import (
    query_page_needs_update,
    resolve_active_page,
    resolve_render_page,
)


def test_successful_json_response() -> None:
    client = _client([httpx.Response(200, json={"status": "ok"})])

    assert client.get("/health") == {"status": "ok"}


def test_no_content_response() -> None:
    client = _client([httpx.Response(204)])

    assert client.delete("/candidates/1") is None


def test_app_info_response_and_read_only_helpers() -> None:
    client = _client(
        [
            httpx.Response(
                200,
                json={
                    "app_mode": "demo",
                    "read_only": True,
                    "demo_data": True,
                    "notice": "This demonstration contains fictional, precomputed data.",
                },
            ),
        ],
    )

    app_info = client.app_info()

    assert app_info["app_mode"] == "demo"
    assert is_demo_mode(app_info) is True
    assert is_read_only(app_info) is True
    assert is_demo_mode({"app_mode": "local", "read_only": False}) is False


def test_fastapi_string_detail_extraction() -> None:
    client = _client([httpx.Response(404, json={"detail": "Candidate not found"})])

    with pytest.raises(ApiClientError) as exc_info:
        client.get("/candidates/999")

    assert exc_info.value.message == "Candidate not found"
    assert exc_info.value.status_code == 404


def test_fastapi_validation_list_extraction() -> None:
    client = _client(
        [
            httpx.Response(
                422,
                json={
                    "detail": [
                        {
                            "loc": ["body", "full_name"],
                            "msg": "Field required",
                        },
                        {
                            "loc": ["body", "years_experience"],
                            "msg": "Input should be less than or equal to 80",
                        },
                    ],
                },
            ),
        ],
    )

    with pytest.raises(ApiClientError) as exc_info:
        client.post("/candidates", json_body={})

    assert exc_info.value.message == (
        "full_name: Field required; "
        "years_experience: Input should be less than or equal to 80"
    )


def test_timeout_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    client = _client_with_handler(handler)

    with pytest.raises(ApiUnavailableError) as exc_info:
        client.get("/health")

    assert exc_info.value.message == "API request timed out"


def test_connection_error_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = _client_with_handler(handler)

    with pytest.raises(ApiUnavailableError) as exc_info:
        client.get("/health")

    assert exc_info.value.message == "API is unavailable"


def test_malformed_success_response() -> None:
    client = _client([httpx.Response(200, text="not json")])

    with pytest.raises(ApiClientError) as exc_info:
        client.get("/health")

    assert exc_info.value.message == "API returned malformed JSON"


def test_non_json_error_response() -> None:
    client = _client([httpx.Response(500, text="Internal Server Error")])

    with pytest.raises(ApiClientError) as exc_info:
        client.get("/health")

    assert exc_info.value.message == "Internal Server Error"


def test_path_joining_query_parameters_and_trailing_slash_base_url() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    client = ApiClient(
        base_url="http://api.local/",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )

    assert client.get("candidates", params={"page": 1, "q": "fictional"}) == {"ok": True}
    assert seen_urls == ["http://api.local/candidates?page=1&q=fictional"]


def test_navigation_prefers_valid_query_page() -> None:
    pages = ["Overview", "Candidates", "Jobs"]

    assert resolve_active_page("Jobs", "Candidates", pages) == "Jobs"
    assert resolve_active_page(["Candidates"], "Jobs", pages) == "Candidates"


def test_navigation_falls_back_to_session_then_default() -> None:
    pages = ["Overview", "Candidates", "Jobs"]

    assert resolve_active_page("Unknown", "Jobs", pages) == "Jobs"
    assert resolve_active_page("Unknown", "Missing", pages) == "Overview"


def test_navigation_query_sync_detection() -> None:
    assert query_page_needs_update("Overview", "Jobs") is True
    assert query_page_needs_update("Jobs", "Jobs") is False
    assert query_page_needs_update(["Jobs"], "Jobs") is False


def test_navigation_pending_page_wins_over_stale_query_page() -> None:
    pages = ["Overview", "Candidates", "Jobs"]

    assert resolve_render_page("Overview", "Overview", "Candidates", pages) == "Candidates"


def _client(responses: list[httpx.Response]) -> ApiClient:
    def handler(request: httpx.Request) -> httpx.Response:
        response = responses.pop(0)
        response.request = request
        return response

    return _client_with_handler(handler)


def _client_with_handler(handler) -> ApiClient:
    return ApiClient(
        base_url="http://api.local/",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
