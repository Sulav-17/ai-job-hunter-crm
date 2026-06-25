from __future__ import annotations

import streamlit as st

PALETTE = {
    "background": "#f6f8fb",
    "surface": "#ffffff",
    "surface_alt": "#f1f5f9",
    "border": "#d9e2ec",
    "text": "#102033",
    "muted": "#65758b",
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "success": "#15803d",
    "warning": "#b45309",
    "danger": "#b91c1c",
    "info": "#0369a1",
}


def apply_global_styles() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --crm-bg: {PALETTE["background"]};
            --crm-surface: {PALETTE["surface"]};
            --crm-surface-alt: {PALETTE["surface_alt"]};
            --crm-border: {PALETTE["border"]};
            --crm-text: {PALETTE["text"]};
            --crm-muted: {PALETTE["muted"]};
            --crm-primary: {PALETTE["primary"]};
            --crm-primary-dark: {PALETTE["primary_dark"]};
            --crm-success: {PALETTE["success"]};
            --crm-warning: {PALETTE["warning"]};
            --crm-danger: {PALETTE["danger"]};
            --crm-info: {PALETTE["info"]};
        }}

        .stApp {{
            background: var(--crm-bg);
            color: var(--crm-text);
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0f172a 0%, #172554 100%);
        }}

        div[data-testid="stSidebarNav"],
        ul[data-testid="stSidebarNavItems"],
        div[data-testid="stSidebarNavLinkContainer"],
        a[data-testid="stSidebarNavLink"] {{
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: #e5eefc !important;
        }}

        section[data-testid="stSidebar"] .stRadio label {{
            padding: 0.35rem 0;
            border-radius: 0.5rem;
        }}

        .crm-sidebar-nav-label {{
            color: #b6c4da !important;
            font-size: 0.82rem;
            font-weight: 800;
            margin: 0.35rem 0 0.45rem;
        }}

        .block-container {{
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }}

        h1, h2, h3 {{
            letter-spacing: 0;
            color: var(--crm-text);
        }}

        div[data-testid="stMetric"] {{
            background: var(--crm-surface);
            border: 1px solid var(--crm-border);
            border-radius: 0.75rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }}

        div[data-testid="stForm"] {{
            background: var(--crm-surface);
            border: 1px solid var(--crm-border);
            border-radius: 0.75rem;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }}

        .stButton > button, .stFormSubmitButton > button {{
            border-radius: 0.55rem;
            border: 1px solid var(--crm-border);
            font-weight: 650;
        }}

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {{
            background: var(--crm-primary);
            border-color: var(--crm-primary-dark);
        }}

        .crm-card {{
            background: var(--crm-surface);
            border: 1px solid var(--crm-border);
            border-radius: 0.75rem;
            padding: 1rem 1.1rem;
            margin: 0 0 0.85rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }}

        .crm-card.compact {{
            padding: 0.8rem 0.9rem;
        }}

        .crm-page-kicker {{
            color: var(--crm-muted);
            font-size: 0.96rem;
            margin-top: -0.65rem;
            margin-bottom: 1.15rem;
        }}

        .crm-hero {{
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.16), transparent 34%),
                linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
            border: 1px solid var(--crm-border);
            border-radius: 0.95rem;
            padding: 1.45rem 1.55rem;
            margin-bottom: 1.4rem;
            box-shadow: 0 16px 44px rgba(15, 23, 42, 0.08);
        }}

        .crm-hero-eyebrow {{
            color: var(--crm-primary-dark);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }}

        .crm-hero-title {{
            color: var(--crm-text);
            font-size: 2.15rem;
            font-weight: 850;
            line-height: 1.1;
            margin-bottom: 0.55rem;
        }}

        .crm-hero-text {{
            color: var(--crm-muted);
            font-size: 1.02rem;
            line-height: 1.55;
            max-width: 760px;
        }}

        .crm-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            border-radius: 999px;
            border: 1px solid var(--crm-border);
            background: var(--crm-surface-alt);
            color: var(--crm-text);
            padding: 0.2rem 0.55rem;
            margin: 0.1rem 0.2rem 0.1rem 0;
            font-size: 0.78rem;
            font-weight: 700;
        }}

        .crm-badge.success {{ color: var(--crm-success); background: #ecfdf5; border-color: #bbf7d0; }}
        .crm-badge.warning {{ color: var(--crm-warning); background: #fffbeb; border-color: #fde68a; }}
        .crm-badge.danger {{ color: var(--crm-danger); background: #fef2f2; border-color: #fecaca; }}
        .crm-badge.info {{ color: var(--crm-info); background: #eff6ff; border-color: #bfdbfe; }}
        .crm-badge.muted {{ color: var(--crm-muted); background: #f8fafc; border-color: var(--crm-border); }}

        .crm-kanban-column {{
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--crm-border);
            border-radius: 0.85rem;
            padding: 0.85rem;
            min-height: 420px;
        }}

        .crm-sidebar-brand {{
            padding: 0.75rem 0 1rem;
            border-bottom: 1px solid rgba(226, 232, 240, 0.18);
            margin-bottom: 0.75rem;
        }}

        .crm-sidebar-brand-title {{
            font-size: 1.08rem;
            font-weight: 800;
        }}

        .crm-sidebar-brand-subtitle {{
            color: #b6c4da !important;
            font-size: 0.82rem;
            margin-top: 0.15rem;
        }}

        @media (max-width: 1100px) {{
            .block-container {{
                padding-left: 1.1rem;
                padding-right: 1.1rem;
            }}
            .crm-kanban-column {{
                min-height: 260px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
