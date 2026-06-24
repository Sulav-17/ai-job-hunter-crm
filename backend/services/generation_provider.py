from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class GenerationProviderError(RuntimeError):
    pass


class MalformedGenerationOutputError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationPrompt:
    system_instructions: str
    user_prompt: str


class GenerationProvider(Protocol):
    def generate(self, prompt: GenerationPrompt) -> dict[str, Any]:
        pass

    @property
    def model_identity(self) -> str:
        pass
