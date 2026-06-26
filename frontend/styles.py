from __future__ import annotations

import streamlit as st

PALETTE = {
    "background": "#f4f7fb",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#dbe4ef",
    "text": "#102033",
    "muted": "#64748b",
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
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.05), transparent 28%),
                var(--crm-bg);
            color: var(--crm-text);
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0b1220 0%, #111c33 54%, #14213d 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.14);
        }}

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding-top: 1.15rem;
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

        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
            color: #8fa1ba !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stAlert"] {{
            border: 1px solid rgba(148, 163, 184, 0.16);
            background: rgba(37, 99, 235, 0.12);
            border-radius: 0.8rem;
            padding: 0.8rem 0.9rem;
        }}

        section[data-testid="stSidebar"] [data-testid="stAlert"] p {{
            color: #e5edf8 !important;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] {{
            gap: 0.42rem;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            width: 100%;
            min-height: 2.65rem;
            padding: 0.62rem 0.78rem;
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 0.72rem;
            background: rgba(255, 255, 255, 0.045);
            transition: background 150ms ease, border-color 150ms ease, transform 150ms ease;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: rgba(255, 255, 255, 0.09);
            border-color: rgba(148, 163, 184, 0.24);
            transform: translateX(2px);
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
            color: #cbd5e1 !important;
            font-weight: 650;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            border-color: rgba(147, 197, 253, 0.6);
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.26);
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
            color: #ffffff !important;
        }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
            display: none;
        }}

        .crm-sidebar-brand {{
            display: flex;
            align-items: center;
            gap: 0.72rem;
            padding: 0.25rem 0 1rem;
            margin-bottom: 0.85rem;
            border-bottom: 1px solid rgba(226, 232, 240, 0.12);
        }}

        .crm-sidebar-brand-mark {{
            display: grid;
            place-items: center;
            width: 2.35rem;
            height: 2.35rem;
            border-radius: 0.72rem;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: #ffffff !important;
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            box-shadow: 0 8px 22px rgba(37, 99, 235, 0.26);
        }}

        .crm-sidebar-brand-title {{
            color: #f8fafc !important;
            font-size: 1.02rem;
            font-weight: 800;
            line-height: 1.1;
        }}

        .crm-sidebar-brand-subtitle {{
            color: #94a3b8 !important;
            font-size: 0.76rem;
            margin-top: 0.18rem;
        }}

        .crm-sidebar-nav-label {{
            color: #71839d !important;
            margin: 1rem 0 0.5rem;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        .crm-sidebar-footer {{
            margin-top: 1.2rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(226, 232, 240, 0.1);
        }}

        h1, h2, h3 {{
            color: var(--crm-text);
            letter-spacing: 0;
        }}

        div[data-testid="stMetric"],
        div[data-testid="stForm"],
        .crm-card {{
            background: var(--crm-surface);
            border: 1px solid var(--crm-border);
            border-radius: 0.85rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        }}

        div[data-testid="stMetric"] {{
            padding: 1rem 1.1rem;
        }}

        div[data-testid="stForm"] {{
            padding: 1rem 1.1rem;
        }}

        .crm-card {{
            padding: 1rem 1.1rem;
            margin: 0 0 0.85rem;
        }}

        .crm-card.compact {{
            padding: 0.8rem 0.9rem;
        }}

        .stButton > button,
        .stFormSubmitButton > button {{
            border: 1px solid var(--crm-border);
            border-radius: 0.6rem;
            font-weight: 650;
        }}

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {{
            background: var(--crm-primary);
            border-color: var(--crm-primary-dark);
        }}

        .crm-page-kicker {{
            color: var(--crm-muted);
            margin-top: -0.65rem;
            margin-bottom: 1.15rem;
            font-size: 0.96rem;
        }}

        .crm-hero {{
            margin-bottom: 1.4rem;
            padding: 1.6rem 1.7rem;
            border: 1px solid var(--crm-border);
            border-radius: 1rem;
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.16), transparent 34%),
                linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
            box-shadow: 0 18px 46px rgba(15, 23, 42, 0.08);
        }}

        .crm-hero-eyebrow {{
            color: var(--crm-primary-dark);
            margin-bottom: 0.35rem;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .crm-hero-title {{
            color: var(--crm-text);
            margin-bottom: 0.55rem;
            font-size: 2.15rem;
            font-weight: 850;
            line-height: 1.1;
        }}

        .crm-hero-text {{
            max-width: 760px;
            color: var(--crm-muted);
            font-size: 1.02rem;
            line-height: 1.55;
        }}

        .crm-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            margin: 0.1rem 0.2rem 0.1rem 0;
            padding: 0.2rem 0.55rem;
            border: 1px solid var(--crm-border);
            border-radius: 999px;
            background: var(--crm-surface-alt);
            color: var(--crm-text);
            font-size: 0.78rem;
            font-weight: 700;
        }}

        .crm-badge.success {{ color: var(--crm-success); background: #ecfdf5; border-color: #bbf7d0; }}
        .crm-badge.warning {{ color: #92400e; background: #fef3c7; border-color: #fcd34d; }}
        .crm-badge.danger {{ color: var(--crm-danger); background: #fef2f2; border-color: #fecaca; }}
        .crm-badge.info {{ color: var(--crm-info); background: #eff6ff; border-color: #bfdbfe; }}
        .crm-badge.muted {{ color: var(--crm-muted); background: #f8fafc; border-color: var(--crm-border); }}

        section[data-testid="stSidebar"] .crm-badge.warning {{
            color: #fde68a !important;
            background: rgba(180, 83, 9, 0.18);
            border-color: rgba(253, 230, 138, 0.35);
        }}

        .crm-kanban-column {{
            min-height: 420px;
            padding: 0.85rem;
            border: 1px solid var(--crm-border);
            border-radius: 0.85rem;
            background: rgba(255, 255, 255, 0.72);
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
