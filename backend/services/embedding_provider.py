from __future__ import annotations

from typing import Protocol


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, source_text: str) -> list[float]:
        pass

    @property
    def model_identity(self) -> str:
        pass
