from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError

STATUSES = ["saved", "applied", "interview", "rejected", "offer"]


def render(api: ApiClient, app_info: dict[str, object] | None = None) -> None:
    ui.page_header(
        "Applications",
        "Track saved opportunities through a polished five-stage workflow.",
    )
    ui.demo_banner(app_info)
    try:
        candidates = api.list_candidates()
        jobs = api.list_jobs()
        applications = api.list_applications()
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    candidate_names = {candidate["id"]: ui.candidate_label(candidate) for candidate in candidates}
    job_names = {job["id"]: ui.job_label(job) for job in jobs}

    if ui.is_read_only(app_info):
        ui.read_only_panel()
    else:
        _create_application_form(api, candidates, jobs)
    st.divider()
    _kanban(api, applications, candidate_names, job_names, app_info)

    selected_id = st.session_state.get("selected_application_id")
    if selected_id is not None:
        st.divider()
        _application_detail(api, selected_id, candidate_names, job_names, app_info)


def _create_application_form(
    api: ApiClient,
    candidates: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> None:
    with st.expander("Create Application", expanded=False):
        if not candidates or not jobs:
            ui.warning_panel("Create at least one candidate and one job before tracking applications.")
            return
        candidate_options = {ui.candidate_label(candidate): candidate["id"] for candidate in candidates}
        job_options = {ui.job_label(job): job["id"] for job in jobs}
        with st.form("application_create_form", clear_on_submit=True):
            candidate_label = st.selectbox("Candidate", list(candidate_options))
            job_label = st.selectbox("Job", list(job_options))
            status = st.selectbox("Initial status", STATUSES)
            notes = st.text_area("Notes", height=120)
            submitted = st.form_submit_button("Create application", type="primary")
        if submitted:
            payload = {
                "candidate_id": candidate_options[candidate_label],
                "job_id": job_options[job_label],
                "status": status,
                "notes": notes or None,
            }
            try:
                created = api.create_application(payload)
                st.session_state["selected_application_id"] = created["id"]
                st.success("Application created.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)


def _kanban(
    api: ApiClient,
    applications: list[dict[str, Any]],
    candidate_names: dict[int, str],
    job_names: dict[int, str],
    app_info: dict[str, object] | None,
) -> None:
    st.subheader("Kanban Workflow")
    columns = st.columns(5)
    for index, status in enumerate(STATUSES):
        with columns[index]:
            st.markdown(f"#### {ui.STATUS_LABELS[status]}")
            status_apps = [
                application
                for application in applications
                if application.get("status") == status
            ]
            if not status_apps:
                st.caption("No cards.")
            for application in status_apps:
                _application_card(api, application, candidate_names, job_names, app_info)


def _application_card(
    api: ApiClient,
    application: dict[str, Any],
    candidate_names: dict[int, str],
    job_names: dict[int, str],
    app_info: dict[str, object] | None,
) -> None:
    ui.card_start(compact=True)
    job_label = job_names.get(application["job_id"], f"Job #{application['job_id']}")
    candidate_label = candidate_names.get(
        application["candidate_id"],
        f"Candidate #{application['candidate_id']}",
    )
    st.markdown(f"**{job_label}**")
    ui.demo_record_badge(application)
    st.caption(candidate_label)
    ui.status_badge(application["status"])
    st.caption(f"Follow-up: {ui.format_datetime(application.get('next_follow_up_at'))}")
    detail = st.button("Open details", key=f"application_detail_{application['id']}")
    if not ui.is_read_only(app_info):
        new_status = st.selectbox(
            "Move status",
            STATUSES,
            index=STATUSES.index(application["status"]),
            key=f"application_status_{application['id']}",
            label_visibility="collapsed",
        )
        if st.button("Update status", key=f"application_status_update_{application['id']}"):
            try:
                api.update_application(application["id"], {"status": new_status})
                st.success("Status updated.")
                st.rerun()
            except ApiClientError as exc:
                ui.api_error(exc)
    if detail:
        st.session_state["selected_application_id"] = application["id"]
        st.rerun()
    ui.card_end()


def _application_detail(
    api: ApiClient,
    application_id: int,
    candidate_names: dict[int, str],
    job_names: dict[int, str],
    app_info: dict[str, object] | None,
) -> None:
    try:
        application = api.get_application(application_id)
        history = api.get_application_status_history(application_id)
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    st.subheader(f"Application #{application_id}")
    ui.demo_record_badge(application)
    ui.card_start()
    st.write(job_names.get(application["job_id"], f"Job #{application['job_id']}"))
    st.caption(candidate_names.get(application["candidate_id"], f"Candidate #{application['candidate_id']}"))
    ui.status_badge(application["status"])
    ui.card_end()

    tab_names = ["Detail", "History"]
    if not ui.is_read_only(app_info):
        tab_names = ["Detail", "Edit", "History", "Danger Zone"]
    tabs = st.tabs(tab_names)
    with tabs[0]:
        st.markdown("#### Notes Preview")
        st.write(application.get("notes") or "No notes.")
        st.caption(f"Applied: {ui.format_datetime(application.get('applied_at'))}")
        st.caption(f"Next follow-up: {ui.format_datetime(application.get('next_follow_up_at'))}")
    history_tab_index = 1
    if not ui.is_read_only(app_info):
        with tabs[1]:
            _edit_application_form(api, application)
        history_tab_index = 2
    with tabs[history_tab_index]:
        if not history:
            ui.empty_state("No status history", "Status changes will appear here.")
        for item in history:
            ui.card_start(compact=True)
            st.write(
                f"{item.get('previous_status') or 'created'} -> {item['new_status']}"
            )
            st.caption(ui.format_datetime(item.get("changed_at")))
            ui.card_end()
    if not ui.is_read_only(app_info):
        with tabs[3]:
            _delete_application(api, application)


def _edit_application_form(api: ApiClient, application: dict[str, Any]) -> None:
    existing_followup = _date_from_iso(application.get("next_follow_up_at"))
    with st.form(f"application_edit_form_{application['id']}"):
        status = st.selectbox(
            "Status",
            STATUSES,
            index=STATUSES.index(application["status"]),
        )
        follow_up = st.date_input(
            "Next follow-up date",
            value=existing_followup,
        )
        notes = st.text_area("Notes", value=application.get("notes") or "", height=180)
        submitted = st.form_submit_button("Save application", type="primary")
    if submitted:
        payload = {
            "status": status,
            "next_follow_up_at": f"{follow_up.isoformat()}T09:00:00",
            "notes": notes or None,
        }
        try:
            api.update_application(application["id"], payload)
            st.success("Application updated.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)


def _delete_application(api: ApiClient, application: dict[str, Any]) -> None:
    key = ui.confirmation_key("application", application["id"])
    st.warning("Deleting an application also removes its status history.")
    if not st.session_state.get(key):
        if st.button(
            "Request application deletion",
            key=f"application_delete_request_{application['id']}",
        ):
            st.session_state[key] = True
            st.rerun()
        return

    st.error(f"Confirm deletion of application #{application['id']}")
    col_a, col_b = st.columns(2)
    if col_a.button("Confirm delete application", type="primary"):
        try:
            api.delete_application(application["id"])
            st.session_state.pop(key, None)
            st.session_state.pop("selected_application_id", None)
            st.success("Application deleted.")
            st.rerun()
        except ApiClientError as exc:
            ui.api_error(exc)
    if col_b.button("Cancel", key=f"application_delete_cancel_{application['id']}"):
        st.session_state.pop(key, None)
        st.rerun()


def _date_from_iso(value: str | None) -> date:
    if not value:
        return date.today()
    return date.fromisoformat(value[:10])
