from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


STATUS_LABELS = {
    "saved": "Saved",
    "applied": "Applied",
    "interview": "Interview",
    "rejected": "Rejected",
    "offer": "Offer",
}

STATUS_TONES = {
    "saved": "muted",
    "applied": "info",
    "interview": "warning",
    "rejected": "danger",
    "offer": "success",
}

_CARD_STACK: list[Any] = []


def page_header(title: str, description: str) -> None:
    st.title(title)
    st.markdown(
        f'<div class="crm-page-kicker">{escape(description)}</div>',
        unsafe_allow_html=True,
    )


def card_start(*, compact: bool = False, extra_class: str = "") -> None:
    container = st.container(border=True)
    context_manager = container.__enter__()
    _CARD_STACK.append(container)


def card_end() -> None:
    if _CARD_STACK:
        container = _CARD_STACK.pop()
        container.__exit__(None, None, None)


def badge(label: str, tone: str = "muted") -> str:
    return (
        f'<span class="crm-badge {escape(tone)}">'
        f'{escape(label)}</span>'
    )


def badges(labels: list[str], *, tone: str = "muted") -> None:
    if not labels:
        st.caption("No items yet.")
        return
    st.markdown("".join(badge(label, tone) for label in labels), unsafe_allow_html=True)


def status_badge(status: str) -> None:
    label = STATUS_LABELS.get(status, status.replace("_", " ").title())
    tone = STATUS_TONES.get(status, "muted")
    st.markdown(badge(label, tone), unsafe_allow_html=True)


def stale_badge(stale: bool) -> None:
    st.markdown(
        badge("Stale - refresh recommended", "warning")
        if stale
        else badge("Current", "success"),
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str, *, action_hint: str | None = None) -> None:
    card_start()
    st.subheader(title)
    st.caption(body)
    if action_hint:
        st.info(action_hint)
    card_end()


def warning_panel(message: str) -> None:
    st.warning(message)


def api_error(error: Exception) -> None:
    message = getattr(error, "message", str(error))
    st.error(message)


def score_card(label: str, score: int | float | None, *, suffix: str = "") -> None:
    value = "Not available" if score is None else f"{score}{suffix}"
    st.metric(label, value)


def record_label(record: dict[str, Any], *, fallback: str) -> str:
    parts = [
        str(record.get("full_name") or record.get("title") or fallback),
        str(record.get("company") or "").strip(),
    ]
    return " - ".join(part for part in parts if part)


def candidate_label(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('full_name', 'Candidate')} #{candidate.get('id')}"


def job_label(job: dict[str, Any]) -> str:
    company = job.get("company")
    suffix = f" at {company}" if company else ""
    return f"{job.get('title', 'Job')}{suffix} #{job.get('id')}"


def format_datetime(value: str | None) -> str:
    if not value:
        return "Not set"
    return value.replace("T", " ").replace("+00:00", " UTC")


def short_text(value: str | None, *, limit: int = 140) -> str:
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text or "No notes."
    return text[: limit - 1].rstrip() + "..."


def select_record(
    label: str,
    records: list[dict[str, Any]],
    *,
    label_func,
    state_key: str,
) -> int | None:
    if not records:
        st.selectbox(label, ["No records available"], disabled=True)
        return None
    options = {label_func(record): record["id"] for record in records}
    labels = list(options)
    current_id = st.session_state.get(state_key)
    index = 0
    if current_id in options.values():
        index = list(options.values()).index(current_id)
    selected_label = st.selectbox(label, labels, index=index)
    selected_id = options[selected_label]
    st.session_state[state_key] = selected_id
    return selected_id


def confirmation_key(kind: str, record_id: int) -> str:
    return f"confirm_delete_{kind}_{record_id}"
