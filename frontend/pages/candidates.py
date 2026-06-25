from __future__ import annotations

from typing import Any

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError


def render(api: ApiClient, app_info: dict[str, object] | None = None) -> None:
    ui.page_header(
        "Candidates",
        "Manage candidate profiles, parse resume text, and inspect embedding metadata.",
    )
    ui.demo_banner(app_info)
    try:
        candidates = api.list_candidates()
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    left, right = st.columns([0.95, 1.55])
    with left:
        _candidate_list(api, candidates)
        if ui.is_read_only(app_info):
            ui.read_only_panel()
        else:
            _create_candidate_form(api)
    with right:
        selected_id = st.session_state.get("selected_candidate_id")
        if selected_id is None and candidates:
            selected_id = candidates[0]["id"]
            st.session_state["selected_candidate_id"] = selected_id
        if selected_id is None:
            ui.empty_state(
                "No candidate selected",
                "Create a candidate or select one from the list to view details.",
            )
        else:
            _candidate_detail(api, selected_id, app_info)


def _candidate_list(api: ApiClient, candidates: list[dict[str, Any]]) -> None:
    st.subheader("Candidate List")
    if not candidates:
        ui.empty_state(
            "No candidates",
            "Candidate list cards intentionally avoid resume and summary bodies.",
        )
        return

    for candidate in candidates:
        ui.card_start(compact=True)
        st.markdown(f"**{candidate['full_name']}**")
        ui.demo_record_badge(candidate)
        st.caption(candidate.get("headline") or "No headline")
        chips = []
        if candidate.get("location"):
            chips.append(candidate["location"])
        if candidate.get("years_experience") is not None:
            chips.append(f"{candidate['years_experience']} years")
        ui.badges(chips, tone="info")
        if st.button(
            "View candidate",
            key=f"candidate_select_{candidate['id']}",
            use_container_width=True,
        ):
            st.session_state["selected_candidate_id"] = candidate["id"]
            st.rerun()
        ui.card_end()


def _create_candidate_form(api: ApiClient) -> None:
    expanded = st.query_params.get("create") == "candidate" or bool(
        st.session_state.pop("candidate_create_expanded", False)
    )
    with st.expander("Create Candidate", expanded=expanded):
        with st.form("candidate_create_form", clear_on_submit=True):
            full_name = st.text_input("Full name")
            headline = st.text_input("Headline")
            location = st.text_input("Location")
            years = st.number_input("Years experience", min_value=0, max_value=80, value=0)
            professional_summary = st.text_area("Professional summary", height=120)
            resume_text = st.text_area("Resume text", height=220)
            submitted = st.form_submit_button("Create candidate", type="primary")
        if submitted:
            payload = {
                "full_name": full_name,
                "headline": headline or None,
                "location": location or None,
                "years_experience": years,
                "professional_summary": professional_summary or None,
                "resume_text": resume_text or None,
            }
            try:
                created = api.create_candidate(payload)
                st.session_state["selected_candidate_id"] = created["id"]
                st.success("Candidate created.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)


def _candidate_detail(
    api: ApiClient,
    candidate_id: int,
    app_info: dict[str, object] | None,
) -> None:
    try:
        candidate = api.get_candidate(candidate_id)
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    st.subheader(candidate["full_name"])
    ui.demo_record_badge(candidate)
    ui.card_start()
    detail_cols = st.columns(3)
    detail_cols[0].metric("Years", candidate.get("years_experience") or 0)
    detail_cols[1].metric("Location", candidate.get("location") or "Not set")
    detail_cols[2].metric("Updated", ui.format_datetime(candidate.get("updated_at")))
    st.caption(candidate.get("headline") or "No headline")
    ui.card_end()

    tab_names = ["Profile", "Parse & Embedding"]
    if not ui.is_read_only(app_info):
        tab_names.extend(["Edit", "Danger Zone"])
    tabs = st.tabs(tab_names)
    with tabs[0]:
        st.markdown("#### Professional Summary")
        st.write(candidate.get("professional_summary") or "No professional summary.")
        with st.expander("Private resume text", expanded=False):
            st.text_area(
                "Resume text",
                value=candidate.get("resume_text") or "",
                height=260,
                disabled=True,
            )
    with tabs[1]:
        _candidate_parse_and_embedding(api, candidate_id, app_info)
    if not ui.is_read_only(app_info):
        with tabs[2]:
            _edit_candidate_form(api, candidate)
        with tabs[3]:
            _delete_candidate(api, candidate)


def _candidate_parse_and_embedding(
    api: ApiClient,
    candidate_id: int,
    app_info: dict[str, object] | None,
) -> None:
    if ui.is_read_only(app_info):
        ui.precomputed_panel()
    else:
        actions = st.columns(2)
        if actions[0].button("Parse resume", type="primary", use_container_width=True):
            try:
                api.parse_candidate(candidate_id)
                st.success("Candidate parsed.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)
        if actions[1].button("Create embedding", use_container_width=True):
            try:
                api.create_candidate_embedding(candidate_id)
                st.success("Candidate embedding refreshed.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)

    st.markdown("#### Parse Result")
    try:
        parse_result = api.get_candidate_parse_result(candidate_id)
        _render_candidate_parse_result(parse_result)
    except ApiClientError as exc:
        ui.warning_panel(exc.message)

    st.markdown("#### Embedding Metadata")
    try:
        embedding = api.get_candidate_embedding(candidate_id)
        ui.card_start(compact=True)
        ui.stale_badge(embedding["stale"])
        st.caption(f"Model: {embedding['model_name']}")
        st.caption(f"Dimensions: {embedding['dimensions']}")
        st.caption(f"Embedded: {ui.format_datetime(embedding.get('embedded_at'))}")
        ui.card_end()
    except ApiClientError as exc:
        ui.warning_panel(exc.message)


def _render_candidate_parse_result(parse_result: dict[str, Any]) -> None:
    ui.card_start()
    st.caption(f"Parser: {parse_result['parser_version']}")
    st.caption(f"Parsed: {ui.format_datetime(parse_result.get('parsed_at'))}")
    st.write(f"Experience: {parse_result.get('parsed_years_experience')}")
    st.write(f"Education: {parse_result.get('education_level') or 'Not detected'}")
    ui.badges([skill["name"] for skill in parse_result.get("skills", [])], tone="info")
    ui.card_end()


def _edit_candidate_form(api: ApiClient, candidate: dict[str, Any]) -> None:
    with st.form(f"candidate_edit_form_{candidate['id']}"):
        full_name = st.text_input("Full name", value=candidate["full_name"])
        headline = st.text_input("Headline", value=candidate.get("headline") or "")
        location = st.text_input("Location", value=candidate.get("location") or "")
        years = st.number_input(
            "Years experience",
            min_value=0,
            max_value=80,
            value=candidate.get("years_experience") or 0,
        )
        professional_summary = st.text_area(
            "Professional summary",
            value=candidate.get("professional_summary") or "",
            height=120,
        )
        resume_text = st.text_area(
            "Resume text",
            value=candidate.get("resume_text") or "",
            height=220,
        )
        submitted = st.form_submit_button("Save candidate", type="primary")
    if submitted:
        payload = {
            "full_name": full_name,
            "headline": headline or None,
            "location": location or None,
            "years_experience": years,
            "professional_summary": professional_summary or None,
            "resume_text": resume_text or None,
        }
        try:
            api.update_candidate(candidate["id"], payload)
            st.success("Candidate updated.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)


def _delete_candidate(api: ApiClient, candidate: dict[str, Any]) -> None:
    key = ui.confirmation_key("candidate", candidate["id"])
    st.warning(
        "Deleting this candidate also removes owned parse, matching, embedding, "
        "tailoring, and application records through the backend."
    )
    if not st.session_state.get(key):
        if st.button("Request candidate deletion", key=f"candidate_delete_request_{candidate['id']}"):
            st.session_state[key] = True
            st.rerun()
        return

    st.error(f"Confirm deletion of candidate: {candidate['full_name']}")
    col_a, col_b = st.columns(2)
    if col_a.button("Confirm delete candidate", type="primary"):
        try:
            api.delete_candidate(candidate["id"])
            st.session_state.pop(key, None)
            st.session_state.pop("selected_candidate_id", None)
            st.success("Candidate deleted.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)
    if col_b.button("Cancel", key=f"candidate_delete_cancel_{candidate['id']}"):
        st.session_state.pop(key, None)
        st.rerun()
