"""
ui.vitals.theme — Vitals 글로벌 스타일 진입점

페이지 첫 줄에서 `apply_vitals_theme()` 호출 → 와인레드 팔레트, LG EI 폰트,
Streamlit 기본 사이드바 hide, 카드/표/버튼 톤이 일괄 적용된다.

디자인 토큰 출처: docs/design/landing.html 의 :root 변수 + 사용자 피드백
반영본 (와인 강조 1점 정책, 8~12px radius, calm engineering 톤).
"""
from __future__ import annotations
import streamlit as st

from .fonts import (
    font_face_block,
    FONT_BODY_STACK,
    FONT_DISPLAY_STACK,
    FONT_MONO_STACK,
)


def _build_css() -> str:
    """모든 글로벌 스타일을 한 덩어리로 빌드."""
    return f"""
{font_face_block()}

:root {{
    /* Brand */
    --primary:        #A50034;
    --primary-dark:   #7E0027;
    --primary-tint:   #F8E5EC;

    /* Surfaces */
    --page-bg:        #F7F8FA;
    --card-bg:        #FFFFFF;
    --soft:           #F1F3F5;

    /* Borders */
    --border:         #E5E7EB;
    --border-strong:  #CBD0D6;

    /* Ink */
    --ink-body:       #1F2430;
    --ink-muted:      #6B7280;
    --ink-subtle:     #9CA3AF;

    /* Status (Good / Warn / Bad) */
    --status-good:    #1F8B4C;
    --status-warn:    #B57F1B;
    --status-bad:     #B23A48;
    --status-good-tint: #E6F4EA;
    --status-warn-tint: #FAF1DD;

    /* On-dark (login video bg 등 다크 영역용) */
    --on-dark:           #FFFFFF;
    --on-dark-muted:     rgba(255,255,255,0.76);
    --on-dark-subtle:    rgba(255,255,255,0.56);
    --panel-dark:        rgba(12,14,18,0.68);
    --panel-border-dark: rgba(255,255,255,0.10);

    /* Fonts */
    --font-body:    {FONT_BODY_STACK};
    --font-display: {FONT_DISPLAY_STACK};
    --font-mono:    {FONT_MONO_STACK};

    /* Layout */
    --radius:        8px;
    --radius-card:   12px;
    --shadow-card:   0 8px 22px -4px rgba(15,17,21,0.06);
    --shadow-elev:   0 30px 80px -20px rgba(0,0,0,0.55);
}}

/* Reset / base ---------------------------------------------------- */
html, body, [class*="css"] {{
    font-family: var(--font-body);
    word-break: keep-all;
}}
html, body {{
    background: var(--page-bg);
    color: var(--ink-body);
    -webkit-font-smoothing: antialiased;
}}

/* Streamlit 사이드바 — 우리 디자인 톤으로 스타일 (기본 표시, 페이지 이동에 사용)
   로그인 페이지는 ui/login_ui/styles.py 에서 별도 hide 함. */
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {{
    background: #FFFFFF !important;
    border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    color: var(--ink-muted) !important;
    border-radius: var(--radius) !important;
    transition: background .12s, color .12s !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{
    background: var(--soft) !important;
    color: var(--ink-body) !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
    color: var(--ink-body) !important;
    background: var(--primary-tint) !important;
    border-left: 3px solid var(--primary) !important;
    padding-left: 13px !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}

/* Streamlit 기본 푸터 hide */
footer {{ visibility: hidden; }}

/* Streamlit 컨테이너 폭/패딩 */
.block-container {{
    padding-top: 1.6rem !important;
    padding-bottom: 1.2rem !important;
    max-width: 1640px !important;
}}

/* Headings ------------------------------------------------------- */
h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-display);
    color: var(--ink-body);
    letter-spacing: -0.02em;
    word-break: keep-all;
}}

/* Streamlit form inputs (text/select/date) — 와인 포커스 링 ------ */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
.stTextInput > div > div,
.stDateInput > div > div,
.stSelectbox > div > div {{
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: #FFFFFF !important;
    transition: border-color .15s, box-shadow .15s;
}}
[data-baseweb="input"]:focus-within > div,
[data-baseweb="select"]:focus-within > div,
.stTextInput > div > div:focus-within,
.stDateInput > div > div:focus-within {{
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-tint) !important;
}}

/* Streamlit buttons ---------------------------------------------- */
.stButton > button,
.stDownloadButton > button {{
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: #FFFFFF !important;
    color: var(--ink-body) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    transition: border-color .15s, background .15s, color .15s;
}}
.stButton > button:hover,
.stDownloadButton > button:hover {{
    border-color: var(--border-strong) !important;
    background: var(--soft) !important;
}}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #FFFFFF !important;
}}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    background: var(--primary-dark) !important;
    border-color: var(--primary-dark) !important;
    color: #FFFFFF !important;
}}

/* Streamlit tabs — 와인 활성 밑줄 */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 1px solid var(--border);
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--ink-muted) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid transparent !important;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--ink-body) !important;
    border-bottom-color: var(--primary) !important;
}}

/* Status badge utility (Good / Warn / Bad) ----------------------- */
.vit-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.vit-badge--good   {{ background: var(--status-good-tint); color: var(--status-good); }}
.vit-badge--warn   {{ background: var(--status-warn-tint); color: var(--status-warn); }}
.vit-badge--subtle {{ background: var(--soft);             color: var(--ink-muted);  }}
.vit-badge__dot {{ width:5px; height:5px; border-radius:50%; background:currentColor; }}

/* Vitals brand-mark utility (with wine dot) ---------------------- */
.vit-brandmark {{
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1;
    color: var(--ink-body);
}}
.vit-brandmark::after {{
    content: ".";
    color: var(--primary);
    font-weight: 700;
    margin-left: 0.02em;
}}
"""


def apply_vitals_theme() -> None:
    """모든 페이지의 첫 줄에서 호출 — 와인 팔레트 + LG EI 폰트 + Streamlit 기본 hide.
    한 페이지에서 여러 번 호출돼도 부작용 없음 (Streamlit이 markdown을 캐시).
    """
    st.markdown(f"<style>\n{_build_css()}\n</style>", unsafe_allow_html=True)
