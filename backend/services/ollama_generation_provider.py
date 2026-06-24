from __future__ import annotations

import json
from typing import Any

import httpx

from backend.services.generation_provider import (
    GenerationPrompt,
    GenerationProviderError,
    MalformedGenerationOutputError,
)
from backend.services.tailoring_prompt import TAILORING_OUTPUT_JSON_SCHEMA


class OllamaGenerationProvider:
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

    def generate(self, prompt: GenerationPrompt) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "system": prompt.system_instructions,
            "prompt": prompt.user_prompt,
            "stream": False,
            "format": TAILORING_OUTPUT_JSON_SCHEMA,
            "options": {
                "temperature": 0,
                "top_p": 0.8,
                "num_predict": 2000,
                "think": False,
            },
        }
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GenerationProviderError("Generation provider unavailable") from exc

        if not isinstance(response_payload, dict):
            raise GenerationProviderError("Generation provider unavailable")

        generated_text = response_payload.get("response")
        if not isinstance(generated_text, str):
            raise GenerationProviderError("Generation provider unavailable")

        try:
            parsed = json.loads(generated_text)
        except json.JSONDecodeError as exc:
            raise MalformedGenerationOutputError(
                "Generation provider returned invalid output",
            ) from exc

        if not isinstance(parsed, dict):
            raise MalformedGenerationOutputError(
                "Generation provider returned invalid output",
            )
        return parsed
