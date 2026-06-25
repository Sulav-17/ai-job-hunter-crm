from __future__ import annotations

from urllib.parse import urlencode

import streamlit as st

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError

STATUSES = ["saved", "applied", "interview", "rejected", "offer"]


def render(api: ApiClient, app_info: dict[str, object] | None = None) -> None:
    ui.page_header(
        "Overview",
        "A command center for candidates, jobs, applications, and next actions.",
    )
    ui.demo_banner(app_info)
    _hero(app_info)
    if ui.is_demo_mode(app_info):
        ui.precomputed_panel()
    try:
        candidates = api.list_candidates()
        jobs = api.list_jobs()
        applications = api.list_applications()
    except ApiClientError as exc:
        ui.api_error(exc)
        return

    status_counts = {
        status: sum(1 for application in applications if application.get("status") == status)
        for status in STATUSES
    }

    metric_columns = st.columns(4)
    metric_columns[0].metric("Candidates", len(candidates))
    metric_columns[1].metric("Jobs", len(jobs))
    metric_columns[2].metric("Applications", len(applications))
    metric_columns[3].metric("Interviews", status_counts["interview"])

    st.subheader("Pipeline")
    pipeline_columns = st.columns(5)
    for index, status in enumerate(STATUSES):
        pipeline_columns[index].metric(ui.STATUS_LABELS[status], status_counts[status])

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Recent Applications")
        if not applications:
            ui.empty_state(
                "No applications yet",
                "Create an application from the Applications page when a candidate and job are ready.",
            )
        for application in applications[:6]:
            ui.card_start(compact=True)
            top = st.columns([2, 1])
            top[0].markdown(f"**Application #{application['id']}**")
            with top[1]:
                ui.status_badge(application["status"])
            st.caption(
                f"Candidate #{application['candidate_id']} -> Job #{application['job_id']}"
            )
            st.caption(f"Follow-up: {ui.format_datetime(application.get('next_follow_up_at'))}")
            ui.card_end()

    with right:
        st.subheader("Quick Workflows")
        ui.card_start()
        st.markdown("**1. Add or choose records**")
        st.caption("Create candidate and job records before parsing or matching.")
        st.markdown("**2. Parse source text**")
        st.caption("Extract deterministic skills, experience, and education signals.")
        st.markdown("**3. Match and tailor**")
        st.caption("Calculate deterministic match, optional semantic similarity, then generate text-only tailoring.")
        st.markdown("**4. Track applications**")
        st.caption("Move applications through the five-status Kanban workflow.")
        ui.card_end()


def _hero(app_info: dict[str, object] | None) -> None:
    st.markdown(
        """
        <div class="crm-hero">
            <div class="crm-hero-eyebrow">Local-first career workspace</div>
            <div class="crm-hero-title">AI Job Hunter CRM</div>
            <div class="crm-hero-text">
                Track jobs, compare fit with explainable scores, tailor applications
                from grounded candidate data, and manage progress from first save to offer.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if ui.is_demo_mode(app_info):
        ui.read_only_panel()
        return
    left, right, _ = st.columns([1, 1, 2.2])
    left.link_button(
        "Add Your Candidate Profile",
        f"?{urlencode({'page': 'Candidates', 'create': 'candidate'})}",
        type="primary",
        use_container_width=True,
    )
    right.link_button(
        "Add a Job",
        f"?{urlencode({'page': 'Jobs', 'create': 'job'})}",
        use_container_width=True,
    )
