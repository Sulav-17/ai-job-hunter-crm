from __future__ import annotations

from typing import Any

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError


def render(api: ApiClient) -> None:
    ui.page_header(
        "Tailoring",
        "Generate and review text-only, evidence-backed application materials.",
    )
    try:
        candidates = api.list_candidates()
        jobs = api.list_jobs()
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    selectors = st.columns(2)
    with selectors[0]:
        candidate_id = ui.select_record(
            "Candidate",
            candidates,
            label_func=ui.candidate_label,
            state_key="tailoring_candidate_id",
        )
    with selectors[1]:
        job_id = ui.select_record(
            "Job",
            jobs,
            label_func=ui.job_label,
            state_key="tailoring_job_id",
        )

    if candidate_id is None or job_id is None:
        ui.empty_state("Select records", "Tailoring requires one candidate and one job.")
        return

    actions = st.columns([1, 1, 1.4])
    if actions[0].button("Generate or reuse", type="primary", use_container_width=True):
        _generate(api, candidate_id, job_id, regenerate=False)
    if actions[1].button("Force regeneration", use_container_width=True):
        _generate(api, candidate_id, job_id, regenerate=True)
    if actions[2].button("Retrieve saved tailoring result", use_container_width=True):
        st.rerun()

    try:
        result = api.get_tailoring_result(candidate_id, job_id)
    except ApiClientError as exc:
        ui.warning_panel(exc.message)
        return

    _render_tailoring_result(result)


def _generate(api: ApiClient, candidate_id: int, job_id: int, *, regenerate: bool) -> None:
    try:
        with st.spinner("Generating tailoring content..."):
            api.generate_tailoring(candidate_id, job_id, regenerate=regenerate)
        st.success("Tailoring result is ready.")
        st.rerun()
    except ApiClientError as exc:
        ui.api_error(exc)


def _render_tailoring_result(result: dict[str, Any]) -> None:
    top = st.columns([1, 2, 1])
    with top[0]:
        ui.stale_badge(result["stale"])
    top[1].caption(f"Model: {result['model_name']} | Prompt: {result['prompt_version']}")
    top[2].caption(f"Generated: {ui.format_datetime(result.get('generated_at'))}")

    tabs = st.tabs(["Summary", "Resume Bullets", "Cover Letter", "Keywords", "Warnings"])
    with tabs[0]:
        ui.card_start()
        st.write(result["tailored_summary"])
        ui.card_end()
    with tabs[1]:
        for index, bullet in enumerate(result.get("resume_bullets", []), start=1):
            ui.card_start()
            st.markdown(f"**Bullet {index}**")
            st.write(bullet["text"])
            st.caption("Supporting evidence")
            st.info(bullet["supporting_evidence"])
            ui.badges(bullet.get("keywords", []), tone="info")
            ui.card_end()
    with tabs[2]:
        st.text_area("Cover-letter draft", value=result["cover_letter"], height=360)
    with tabs[3]:
        ui.badges(result.get("keywords_used", []), tone="info")
    with tabs[4]:
        warnings = result.get("warnings", [])
        if not warnings:
            ui.empty_state("No warnings", "The provider returned no warnings.")
        for warning in warnings:
            st.warning(warning)
