from __future__ import annotations

from collections.abc import Sequence


def resolve_active_page(
    query_page: object,
    session_page: object,
    page_names: Sequence[str],
    *,
    default_page: str = "Overview",
) -> str:
    query_value = _first_query_value(query_page)
    if query_value in page_names:
        return query_value
    if isinstance(session_page, str) and session_page in page_names:
        return session_page
    if default_page in page_names:
        return default_page
    return page_names[0]


def resolve_render_page(
    query_page: object,
    session_page: object,
    pending_page: object,
    page_names: Sequence[str],
    *,
    default_page: str = "Overview",
) -> str:
    if isinstance(pending_page, str) and pending_page in page_names:
        return pending_page
    return resolve_active_page(
        query_page,
        session_page,
        page_names,
        default_page=default_page,
    )


def query_page_needs_update(query_page: object, selected_page: str) -> bool:
    return _first_query_value(query_page) != selected_page


def _first_query_value(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    return None
