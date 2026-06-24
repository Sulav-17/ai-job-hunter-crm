import json

import pytest

from backend.services.generation_provider import GenerationPrompt
from backend.services.ollama_generation_provider import OllamaGenerationProvider
from backend.services.tailoring_prompt import TailoringOutputError, validate_tailoring_output
from tests.unit.test_tailoring_prompt import RESUME_TEXT, _valid_payload


def test_rejects_unknown_or_missing_structured_fields() -> None:
    payload = _valid_payload()
    payload["extra"] = "unsupported"
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(payload, resume_text=RESUME_TEXT, gap_warnings=[])

    missing_payload = _valid_payload()
    del missing_payload["cover_letter"]
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(missing_payload, resume_text=RESUME_TEXT, gap_warnings=[])


def test_rejects_summary_and_bullet_limits() -> None:
    payload = _valid_payload()
    payload["tailored_summary"] = "x" * 2001
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(payload, resume_text=RESUME_TEXT, gap_warnings=[])

    too_few = _valid_payload()
    too_few["resume_bullets"] = too_few["resume_bullets"][:2]
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(too_few, resume_text=RESUME_TEXT, gap_warnings=[])

    long_bullet = _valid_payload()
    long_bullet["resume_bullets"][0]["text"] = "x" * 501
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(long_bullet, resume_text=RESUME_TEXT, gap_warnings=[])


def test_evidence_matching_is_case_insensitive_and_whitespace_normalized() -> None:
    payload = _valid_payload()
    payload["resume_bullets"][0]["supporting_evidence"] = "built   python DASHBOARDS"

    output = validate_tailoring_output(payload, resume_text=RESUME_TEXT, gap_warnings=[])

    assert output.resume_bullets[0].supporting_evidence == "built python DASHBOARDS"


def test_rejects_unsupported_evidence_and_markdown_tables() -> None:
    payload = _valid_payload()
    payload["resume_bullets"][0]["supporting_evidence"] = "Managed Kubernetes clusters"
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(payload, resume_text=RESUME_TEXT, gap_warnings=[])

    table_payload = _valid_payload()
    table_payload["cover_letter"] = "Dear Hiring Team,\n| Skill | Match |\n| --- | --- |"
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(table_payload, resume_text=RESUME_TEXT, gap_warnings=[])


def test_keyword_and_warning_bounds() -> None:
    payload = _valid_payload()
    payload["keywords_used"] = [f"keyword {index}" for index in range(51)]
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(payload, resume_text=RESUME_TEXT, gap_warnings=[])

    warnings_payload = _valid_payload()
    warnings_payload["warnings"] = [f"warning {index}" for index in range(21)]
    with pytest.raises(TailoringOutputError):
        validate_tailoring_output(warnings_payload, resume_text=RESUME_TEXT, gap_warnings=[])


def test_ollama_provider_reports_malformed_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"response": "{not json"}

    calls: list[dict] = []

    def fake_post(*args, json, **kwargs):
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    provider = OllamaGenerationProvider(
        model_name="qwen3:4b",
        base_url="http://localhost:11434",
        timeout_seconds=120,
    )

    with pytest.raises(Exception) as exc_info:
        provider.generate(GenerationPrompt("system", "prompt"))

    assert "invalid output" in str(exc_info.value)
    assert calls[0]["model"] == "qwen3:4b"
    assert calls[0]["stream"] is False
    assert isinstance(calls[0]["format"], dict)
    assert calls[0]["options"]["think"] is False


def test_repeated_fake_provider_output_is_deterministic() -> None:
    prompt = GenerationPrompt("system", "prompt")
    provider = DeterministicFakeProvider()

    assert provider.model_identity == "fake:test-model"
    assert provider.generate(prompt) == provider.generate(prompt)
    assert provider.generate(prompt) == json.loads(json.dumps(provider.generate(prompt)))


class DeterministicFakeProvider:
    @property
    def model_identity(self) -> str:
        return "fake:test-model"

    def generate(self, prompt: GenerationPrompt) -> dict:
        return _valid_payload()
