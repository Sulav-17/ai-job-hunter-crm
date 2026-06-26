from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from frontend import components as ui
from frontend.api_client import ApiClient, ApiClientError
from frontend.navigation import query_page_needs_update, resolve_render_page
from frontend.pages import applications, candidates, jobs, matching, overview, tailoring
from frontend.styles import apply_global_styles

PAGES = {
    "Overview": overview.render,
    "Candidates": candidates.render,
    "Jobs": jobs.render,
    "Matching": matching.render,
    "Tailoring": tailoring.render,
    "Applications": applications.render,
}

PENDING_NAVIGATION_KEY = "pending_navigation_page"
NAVIGATION_WIDGET_KEY = "sidebar_navigation"


def main() -> None:
    load_dotenv()
    st.set_page_config(
        page_title="AI Job Hunter CRM",
        page_icon=":briefcase:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()

    page_names = list(PAGES)
    pending_page = st.session_state.pop(PENDING_NAVIGATION_KEY, None)
    active_page = resolve_render_page(
        st.query_params.get("page"),
        st.session_state.get("active_page"),
        pending_page,
        page_names,
    )
    st.session_state["active_page"] = active_page

    if query_page_needs_update(st.query_params.get("page"), active_page):
        st.query_params["page"] = active_page

    api = _get_api_client()
    app_info = _get_app_info(api)
    selected_page = _sidebar(api, page_names, active_page, app_info)
    PAGES[selected_page](api, app_info)


@st.cache_resource
def _get_api_client() -> ApiClient:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    timeout_seconds = float(os.getenv("FRONTEND_REQUEST_TIMEOUT_SECONDS", "120"))
    return ApiClient(base_url=base_url, timeout_seconds=timeout_seconds)


def _get_app_info(api: ApiClient) -> dict[str, object]:
    try:
        return api.app_info()
    except ApiClientError:
        return {"app_mode": "local", "read_only": False, "demo_data": False}


def _sidebar(
    api: ApiClient,
    page_names: list[str],
    active_page: str,
    app_info: dict[str, object],
) -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="crm-sidebar-brand">
                <div class="crm-sidebar-brand-mark">AI</div>
                <div>
                    <div class="crm-sidebar-brand-title">Job Hunter CRM</div>
                    <div class="crm-sidebar-brand-subtitle">Career intelligence workspace</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if ui.is_demo_mode(app_info):
            ui.demo_banner(app_info)
        else:
            st.info("Private local workspace")

        st.markdown(
            '<div class="crm-sidebar-nav-label">Workspace</div>',
            unsafe_allow_html=True,
        )

        selected_page = _sidebar_navigation(page_names, active_page)
        st.session_state["active_page"] = selected_page

        st.markdown('<div class="crm-sidebar-footer">', unsafe_allow_html=True)
        st.caption("System status")
        _api_status(api)
        st.markdown("</div>", unsafe_allow_html=True)
        return selected_page


def _sidebar_navigation(page_names: list[str], active_page: str) -> str:
    if st.session_state.get(NAVIGATION_WIDGET_KEY) != active_page:
        st.session_state[NAVIGATION_WIDGET_KEY] = active_page

    st.radio(
        "Workspace navigation",
        options=page_names,
        key=NAVIGATION_WIDGET_KEY,
        on_change=_on_navigation_change,
        label_visibility="collapsed",
    )
    return str(st.session_state[NAVIGATION_WIDGET_KEY])


def _on_navigation_change() -> None:
    selected_page = st.session_state.get(NAVIGATION_WIDGET_KEY)
    if not isinstance(selected_page, str) or selected_page not in PAGES:
        return

    st.session_state[PENDING_NAVIGATION_KEY] = selected_page
    st.session_state["active_page"] = selected_page
    st.query_params["page"] = selected_page


def _api_status(api: ApiClient) -> None:
    try:
        api.health()
        try:
            api.ready()
            st.success("API ready")
        except ApiClientError:
            st.warning("API reachable, database waking")
    except ApiClientError:
        st.error("API waking up")


if __name__ == "__main__":
    main()
