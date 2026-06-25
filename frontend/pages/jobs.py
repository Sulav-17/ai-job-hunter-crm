from __future__ import annotations

from typing import Any

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError

EMPLOYMENT_TYPES = ["", "full_time", "part_time", "contract", "internship", "temporary", "other"]
WORK_MODES = ["", "remote", "hybrid", "on_site"]


def render(api: ApiClient) -> None:
    ui.page_header("Jobs", "Manage saved job postings, parsing, and embedding metadata.")
    try:
        jobs = api.list_jobs()
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    left, right = st.columns([0.95, 1.55])
    with left:
        _job_list(jobs)
        _create_job_form(api)
    with right:
        selected_id = st.session_state.get("selected_job_id")
        if selected_id is None and jobs:
            selected_id = jobs[0]["id"]
            st.session_state["selected_job_id"] = selected_id
        if selected_id is None:
            ui.empty_state("No job selected", "Create or select a job to view details.")
        else:
            _job_detail(api, selected_id)


def _job_list(jobs: list[dict[str, Any]]) -> None:
    st.subheader("Job List")
    if not jobs:
        ui.empty_state("No jobs", "Job cards intentionally avoid full descriptions.")
        return
    for job in jobs:
        ui.card_start(compact=True)
        st.markdown(f"**{job['title']}**")
        st.caption(job["company"])
        chips = [
            value
            for value in [job.get("location"), job.get("employment_type"), job.get("work_mode")]
            if value
        ]
        ui.badges(chips, tone="info")
        if st.button("View job", key=f"job_select_{job['id']}", use_container_width=True):
            st.session_state["selected_job_id"] = job["id"]
            st.rerun()
        ui.card_end()


def _create_job_form(api: ApiClient) -> None:
    expanded = st.query_params.get("create") == "job" or bool(
        st.session_state.pop("job_create_expanded", False)
    )
    with st.expander("Create Job", expanded=expanded):
        with st.form("job_create_form", clear_on_submit=True):
            title = st.text_input("Title")
            company = st.text_input("Company")
            location = st.text_input("Location")
            employment_type = st.selectbox("Employment type", EMPLOYMENT_TYPES)
            work_mode = st.selectbox("Work mode", WORK_MODES)
            source_url = st.text_input("Source URL")
            description = st.text_area("Description", height=260)
            submitted = st.form_submit_button("Create job", type="primary")
        if submitted:
            payload = {
                "title": title,
                "company": company,
                "location": location or None,
                "employment_type": employment_type or None,
                "work_mode": work_mode or None,
                "source_url": source_url or None,
                "description": description,
            }
            try:
                created = api.create_job(payload)
                st.session_state["selected_job_id"] = created["id"]
                st.success("Job created.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)


def _job_detail(api: ApiClient, job_id: int) -> None:
    try:
        job = api.get_job(job_id)
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    st.subheader(job["title"])
    ui.card_start()
    cols = st.columns(3)
    cols[0].metric("Company", job["company"])
    cols[1].metric("Mode", job.get("work_mode") or "Not set")
    cols[2].metric("Updated", ui.format_datetime(job.get("updated_at")))
    ui.badges(
        [value for value in [job.get("location"), job.get("employment_type")] if value],
        tone="info",
    )
    ui.card_end()

    tabs = st.tabs(["Description", "Parse & Embedding", "Edit", "Danger Zone"])
    with tabs[0]:
        st.text_area("Job description", value=job.get("description") or "", height=320, disabled=True)
        if job.get("source_url"):
            st.link_button("Open source URL", job["source_url"])
    with tabs[1]:
        _job_parse_and_embedding(api, job_id)
    with tabs[2]:
        _edit_job_form(api, job)
    with tabs[3]:
        _delete_job(api, job)


def _job_parse_and_embedding(api: ApiClient, job_id: int) -> None:
    actions = st.columns(2)
    if actions[0].button("Parse job", type="primary", use_container_width=True):
        try:
            api.parse_job(job_id)
            st.success("Job parsed.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)
    if actions[1].button("Create embedding", use_container_width=True):
        try:
            api.create_job_embedding(job_id)
            st.success("Job embedding refreshed.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)

    st.markdown("#### Parse Result")
    try:
        parse_result = api.get_job_parse_result(job_id)
        _render_job_parse_result(parse_result)
    except ApiClientError as exc:
        ui.warning_panel(exc.message)

    st.markdown("#### Embedding Metadata")
    try:
        embedding = api.get_job_embedding(job_id)
        ui.card_start(compact=True)
        ui.stale_badge(embedding["stale"])
        st.caption(f"Model: {embedding['model_name']}")
        st.caption(f"Dimensions: {embedding['dimensions']}")
        st.caption(f"Embedded: {ui.format_datetime(embedding.get('embedded_at'))}")
        ui.card_end()
    except ApiClientError as exc:
        ui.warning_panel(exc.message)


def _render_job_parse_result(parse_result: dict[str, Any]) -> None:
    ui.card_start()
    st.caption(f"Parser: {parse_result['parser_version']}")
    st.caption(f"Parsed: {ui.format_datetime(parse_result.get('parsed_at'))}")
    st.write(f"Required experience: {parse_result.get('minimum_years_experience')}")
    st.write(f"Required education: {parse_result.get('education_requirement') or 'Not detected'}")
    st.markdown("Required skills")
    ui.badges([skill["name"] for skill in parse_result.get("required_skills", [])], tone="danger")
    st.markdown("Preferred skills")
    ui.badges([skill["name"] for skill in parse_result.get("preferred_skills", [])], tone="info")
    ui.card_end()


def _edit_job_form(api: ApiClient, job: dict[str, Any]) -> None:
    with st.form(f"job_edit_form_{job['id']}"):
        title = st.text_input("Title", value=job["title"])
        company = st.text_input("Company", value=job["company"])
        location = st.text_input("Location", value=job.get("location") or "")
        employment_type = st.selectbox(
            "Employment type",
            EMPLOYMENT_TYPES,
            index=EMPLOYMENT_TYPES.index(job.get("employment_type") or ""),
        )
        work_mode = st.selectbox(
            "Work mode",
            WORK_MODES,
            index=WORK_MODES.index(job.get("work_mode") or ""),
        )
        source_url = st.text_input("Source URL", value=job.get("source_url") or "")
        description = st.text_area("Description", value=job.get("description") or "", height=260)
        submitted = st.form_submit_button("Save job", type="primary")
    if submitted:
        payload = {
            "title": title,
            "company": company,
            "location": location or None,
            "employment_type": employment_type or None,
            "work_mode": work_mode or None,
            "source_url": source_url or None,
            "description": description,
        }
        try:
            api.update_job(job["id"], payload)
            st.success("Job updated.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)


def _delete_job(api: ApiClient, job: dict[str, Any]) -> None:
    key = ui.confirmation_key("job", job["id"])
    st.warning(
        "Deleting this job also removes owned parse, matching, embedding, tailoring, "
        "and application records through the backend."
    )
    if not st.session_state.get(key):
        if st.button("Request job deletion", key=f"job_delete_request_{job['id']}"):
            st.session_state[key] = True
            st.rerun()
        return

    st.error(f"Confirm deletion of job: {job['title']} at {job['company']}")
    col_a, col_b = st.columns(2)
    if col_a.button("Confirm delete job", type="primary"):
        try:
            api.delete_job(job["id"])
            st.session_state.pop(key, None)
            st.session_state.pop("selected_job_id", None)
            st.success("Job deleted.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)
    if col_b.button("Cancel", key=f"job_delete_cancel_{job['id']}"):
        st.session_state.pop(key, None)
        st.rerun()
