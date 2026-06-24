from __future__ import annotations

from typing import Any

import httpx

from backend.services.embedding_provider import EmbeddingProviderError
from backend.services.semantic_similarity import (
    VectorValidationError,
    validate_embedding_vector,
)


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        timeout_seconds: int,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def model_identity(self) -> str:
        return f"ollama:{self.model_name}"

    def embed(self, source_text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": source_text},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmbeddingProviderError("Embedding provider unavailable") from exc

        vector = _first_embedding_from_payload(payload)
        try:
            return list(validate_embedding_vector(vector).values)
        except VectorValidationError as exc:
            raise EmbeddingProviderError("Embedding provider unavailable") from exc


def _first_embedding_from_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        raise EmbeddingProviderError("Embedding provider unavailable")

    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or not embeddings:
        raise EmbeddingProviderError("Embedding provider unavailable")

    return embeddings[0]
