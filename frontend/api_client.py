from __future__ import annotations

from typing import Any

import httpx


class ApiClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApiUnavailableError(ApiClientError):
    pass


class ApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("POST", path, json_body=json_body, params=params)

    def patch(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("PATCH", path, json_body=json_body, params=params)

    def delete(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, params=params)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                self._join_path(path),
                json=json_body,
                params=params,
            )
        except httpx.TimeoutException as exc:
            raise ApiUnavailableError("API request timed out") from exc
        except httpx.ConnectError as exc:
            raise ApiUnavailableError("API is unavailable") from exc
        except httpx.HTTPError as exc:
            raise ApiUnavailableError("API request failed") from exc

        if response.status_code == 204:
            return None

        if response.is_error:
            raise ApiClientError(
                self._error_message(response),
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("API returned malformed JSON") from exc

    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def ready(self) -> dict[str, Any]:
        return self.get("/ready")

    def list_candidates(self) -> list[dict[str, Any]]:
        return self.get("/candidates")

    def create_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/candidates", json_body=payload)

    def get_candidate(self, candidate_id: int) -> dict[str, Any]:
        return self.get(f"/candidates/{candidate_id}")

    def update_candidate(self, candidate_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"/candidates/{candidate_id}", json_body=payload)

    def delete_candidate(self, candidate_id: int) -> None:
        self.delete(f"/candidates/{candidate_id}")

    def parse_candidate(self, candidate_id: int) -> dict[str, Any]:
        return self.post(f"/candidates/{candidate_id}/parse")

    def get_candidate_parse_result(self, candidate_id: int) -> dict[str, Any]:
        return self.get(f"/candidates/{candidate_id}/parse-result")

    def create_candidate_embedding(self, candidate_id: int) -> dict[str, Any]:
        return self.post(f"/candidates/{candidate_id}/embedding")

    def get_candidate_embedding(self, candidate_id: int) -> dict[str, Any]:
        return self.get(f"/candidates/{candidate_id}/embedding")

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.get("/jobs")

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/jobs", json_body=payload)

    def get_job(self, job_id: int) -> dict[str, Any]:
        return self.get(f"/jobs/{job_id}")

    def update_job(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"/jobs/{job_id}", json_body=payload)

    def delete_job(self, job_id: int) -> None:
        self.delete(f"/jobs/{job_id}")

    def parse_job(self, job_id: int) -> dict[str, Any]:
        return self.post(f"/jobs/{job_id}/parse")

    def get_job_parse_result(self, job_id: int) -> dict[str, Any]:
        return self.get(f"/jobs/{job_id}/parse-result")

    def create_job_embedding(self, job_id: int) -> dict[str, Any]:
        return self.post(f"/jobs/{job_id}/embedding")

    def get_job_embedding(self, job_id: int) -> dict[str, Any]:
        return self.get(f"/jobs/{job_id}/embedding")

    def calculate_match(self, candidate_id: int, job_id: int) -> dict[str, Any]:
        return self.post(f"/candidates/{candidate_id}/jobs/{job_id}/match")

    def get_match_result(self, candidate_id: int, job_id: int) -> dict[str, Any]:
        return self.get(f"/candidates/{candidate_id}/jobs/{job_id}/match-result")

    def calculate_semantic_match(self, candidate_id: int, job_id: int) -> dict[str, Any]:
        return self.post(f"/candidates/{candidate_id}/jobs/{job_id}/semantic-match")

    def get_semantic_match_result(self, candidate_id: int, job_id: int) -> dict[str, Any]:
        return self.get(
            f"/candidates/{candidate_id}/jobs/{job_id}/semantic-match-result",
        )

    def generate_tailoring(
        self,
        candidate_id: int,
        job_id: int,
        *,
        regenerate: bool = False,
    ) -> dict[str, Any]:
        return self.post(
            f"/candidates/{candidate_id}/jobs/{job_id}/tailoring",
            json_body={"regenerate": regenerate},
        )

    def get_tailoring_result(self, candidate_id: int, job_id: int) -> dict[str, Any]:
        return self.get(f"/candidates/{candidate_id}/jobs/{job_id}/tailoring-result")

    def list_applications(self) -> list[dict[str, Any]]:
        return self.get("/applications")

    def create_application(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/applications", json_body=payload)

    def get_application(self, application_id: int) -> dict[str, Any]:
        return self.get(f"/applications/{application_id}")

    def update_application(
        self,
        application_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.patch(f"/applications/{application_id}", json_body=payload)

    def delete_application(self, application_id: int) -> None:
        self.delete(f"/applications/{application_id}")

    def get_application_status_history(self, application_id: int) -> list[dict[str, Any]]:
        return self.get(f"/applications/{application_id}/status-history")

    def _join_path(self, path: str) -> str:
        if not path:
            return "/"
        return "/" + path.lstrip("/")

    def _error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            return text or f"API returned HTTP {response.status_code}"

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str):
                return detail
            if isinstance(detail, list):
                return _validation_detail_message(detail)
        return f"API returned HTTP {response.status_code}"


def _validation_detail_message(detail: list[Any]) -> str:
    messages: list[str] = []
    for item in detail:
        if not isinstance(item, dict):
            continue
        location = item.get("loc", [])
        message = item.get("msg", "Invalid value")
        if isinstance(location, list) and location:
            location_text = ".".join(str(part) for part in location if part != "body")
            messages.append(f"{location_text}: {message}" if location_text else str(message))
        else:
            messages.append(str(message))
    return "; ".join(messages) if messages else "Validation failed"
