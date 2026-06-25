from __future__ import annotations

from typing import Any

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError


def render(api: ApiClient, app_info: dict[str, object] | None = None) -> None:
    ui.page_header(
        "Matching",
        "Compare one parsed candidate with one parsed job using deterministic and semantic signals.",
    )
    ui.demo_banner(app_info)
    if ui.is_demo_mode(app_info):
        ui.precomputed_panel()
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
            state_key="matching_candidate_id",
        )
    with selectors[1]:
        job_id = ui.select_record(
            "Job",
            jobs,
            label_func=ui.job_label,
            state_key="matching_job_id",
        )

    if candidate_id is None or job_id is None:
        ui.empty_state(
            "Select records",
            "Matching requires at least one candidate and one job.",
        )
        return

    deterministic, semantic = st.columns([1.2, 1])
    with deterministic:
        _deterministic_match(api, candidate_id, job_id, app_info)
    with semantic:
        _semantic_match(api, candidate_id, job_id, app_info)


def _deterministic_match(
    api: ApiClient,
    candidate_id: int,
    job_id: int,
    app_info: dict[str, object] | None,
) -> None:
    st.subheader("Deterministic Match")
    if ui.is_read_only(app_info):
        st.caption("Showing the saved precomputed demo match.")
    else:
        actions = st.columns(2)
        if actions[0].button("Calculate deterministic match", type="primary", use_container_width=True):
            try:
                api.calculate_match(candidate_id, job_id)
                st.success("Deterministic match calculated.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)
        if actions[1].button("Retrieve saved match", use_container_width=True):
            st.rerun()

    try:
        result = api.get_match_result(candidate_id, job_id)
    except ApiClientError as exc:
        ui.warning_panel(exc.message)
        return

    score_cols = st.columns(4)
    score_cols[0].metric("Overall", f"{result['overall_score']}%")
    score_cols[1].metric("Required", _score(result.get("required_skill_score")))
    score_cols[2].metric("Preferred", _score(result.get("preferred_skill_score")))
    score_cols[3].metric("Experience", _score(result.get("experience_score")))

    st.markdown("#### Applicable Weights")
    weights = result.get("applicable_weights", {})
    ui.badges(
        [
            f"Required {weights.get('required_skills')}%",
            f"Preferred {weights.get('preferred_skills')}%",
            f"Experience {weights.get('experience')}%",
            f"Education {weights.get('education')}%",
        ],
        tone="muted",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("Matched required")
        ui.badges(_skill_names(result, "matched_required_skills"), tone="success")
        st.markdown("Matched preferred")
        ui.badges(_skill_names(result, "matched_preferred_skills"), tone="info")
    with right:
        st.markdown("Missing required")
        ui.badges(_skill_names(result, "missing_required_skills"), tone="danger")
        st.markdown("Missing preferred")
        ui.badges(_skill_names(result, "missing_preferred_skills"), tone="warning")

    st.markdown("#### Experience and Education")
    st.write(
        f"Experience: candidate {result.get('candidate_years_used')} years; "
        f"required {result.get('required_years')} years."
    )
    st.write(
        f"Education: candidate {result.get('candidate_education_level') or 'not detected'}; "
        f"required {result.get('required_education_level') or 'not specified'}."
    )


def _semantic_match(
    api: ApiClient,
    candidate_id: int,
    job_id: int,
    app_info: dict[str, object] | None,
) -> None:
    st.subheader("Semantic Similarity")
    st.caption("Separate from deterministic scoring. No hybrid score is created.")
    if ui.is_read_only(app_info):
        st.caption("Showing the saved precomputed demo semantic result.")
    else:
        actions = st.columns(2)
        if actions[0].button("Calculate semantic match", type="primary", use_container_width=True):
            try:
                api.calculate_semantic_match(candidate_id, job_id)
                st.success("Semantic match calculated.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)
        if actions[1].button("Retrieve semantic result", use_container_width=True):
            st.rerun()

    try:
        result = api.get_semantic_match_result(candidate_id, job_id)
    except ApiClientError as exc:
        ui.warning_panel(exc.message)
        return

    ui.card_start()
    st.metric("Semantic score", f"{result['semantic_score']}%")
    st.metric("Cosine similarity", f"{result['cosine_similarity']:.4f}")
    st.caption(f"Model: {result['model_name']}")
    st.caption(f"Calculated: {ui.format_datetime(result.get('calculated_at'))}")
    ui.card_end()


def _skill_names(result: dict[str, Any], key: str) -> list[str]:
    return [skill["name"] for skill in result.get(key, [])]


def _score(value: int | None) -> str:
    return "N/A" if value is None else f"{value}%"
