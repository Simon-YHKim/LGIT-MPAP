import os
import html as html_lib
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib import font_manager, rcParams
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from auth_guard import require_login

# Streamlit 기본 페이지 설정: 좌측 메뉴는 접은 상태로 시작하고, 실제 숨김은 CSS에서 처리합니다.
st.set_page_config(
    page_title="CMP 달성률 Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
require_login(
    page_name="CMP_dashboard",
    page_path="pages/1_CMP_Dashboard.py"
)

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

# preview-streamlit-clone.html sec-cmp parity marker (표현 layer)
import streamlit as _st_marker  # noqa: E402
_st_marker.markdown(
    '<div class="sc-page-section sc-cmp-section is-active" data-sec="cmp"></div>',
    unsafe_allow_html=True
)
# components.html iframe 으로 parent body class 조작 (markdown script 는 sanitize)
import streamlit.components.v1 as _comp_for_body_class  # noqa: E402
_comp_for_body_class.html(
    '<script>parent.document.body.classList.remove("is-login-active");'
    'parent.document.body.classList.add("is-cmp-active");</script>',
    height=0
)
from ui.vitals import render_section_header as _render_section_header  # noqa: E402
_render_section_header("cmp")

from access_logger import log_page_access

log_page_access("1_CMP_Dashboard")

from ui.analytics import inject_tracker
inject_tracker(page_name="1_CMP_Dashboard", page_path="pages/1_CMP_Dashboard.py")

# -----------------------------
# DB 설정
# -----------------------------
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "CMP"
DB_USER = "postgres"
DB_PASSWORD = os.getenv("CMP_DB_PASSWORD", "!Q2w3e4r5t")
DB_SCHEMA = "public"
DB_TABLE = "mart_cmp_dashboard_daily"

FACTORY_COL = '영역'
MODEL_COL = '모델'
PROCESS_COL = '공정명 (L1)'
EQUIPMENT_COL = '설비'
PERIOD_COL = '기간'
CMP_COL = 'CMP 달성률'
ACTUAL_UPH_COL = '실적 UPH'
CMP_UPH_COL = 'CMP UPH'
ACTUAL_EFF_COL = 'Production Operating Rate (Full Load)(생산가동률 Full 부하)'
CMP_EFF_COL = 'CMP EFF'
MAX_VALID_ACHIEVEMENT = 5.0
MAX_VALID_CMP = 5.0
CHART_YMIN = 50
CHART_YMAX = 150
LEFT_COLS = [MODEL_COL, FACTORY_COL, PROCESS_COL]
DASHBOARD_DB_LOOKBACK_MONTHS = 3


MATPLOTLIB_KR_FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
MATPLOTLIB_EN_FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"

def set_korean_font():
    """Matplotlib 폰트 설정
    - Matplotlib에서는 혼합(한글/영문) 폰트보다 한글 폰트를 확실히 등록/적용하는 것이 안정적입니다.
    - UI(CSS)는 Arial + LG fallback 유지, Matplotlib은 LG를 강제 우선 적용합니다.
    """
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\malgunsl.ttf",
        MATPLOTLIB_KR_FONT_PATH,
    ]

    family_names = []
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                font_manager.fontManager.addfont(font_path)
            except Exception:
                pass
            try:
                font_name = font_manager.FontProperties(fname=font_path).get_name()
                if font_name not in family_names:
                    family_names.append(font_name)
            except Exception:
                continue

    if family_names:
        rcParams['font.family'] = family_names
        rcParams['font.sans-serif'] = family_names
    rcParams['axes.unicode_minus'] = False


def get_matplotlib_korean_fontprop():
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\malgunsl.ttf",
        MATPLOTLIB_KR_FONT_PATH,
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                font_manager.fontManager.addfont(font_path)
            except Exception:
                pass
            return font_manager.FontProperties(fname=font_path)
    return None

def resolve_data_file() -> str:
    return "DB"


@st.cache_resource(show_spinner=False)
def get_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # 공용 DB 보호 목적: 연결을 오래 붙잡지 않도록 NullPool 사용
    return create_engine(
        url,
        future=True,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={
            "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000"
        },
    )


@st.cache_data(show_spinner=False, ttl=600)
def read_csv_flex(path: str) -> pd.DataFrame:
    """DB 전용 로더: 초기 로딩 성능 개선을 위해 최근 N개월 + 대시보드 필요 컬럼만 조회합니다.

    - 기준일: mart_cmp_dashboard_daily 내 비이상치 데이터의 MAX(work_date)
    - 조회범위: 기준일 - DASHBOARD_DB_LOOKBACK_MONTHS 개월 이후
    - 조회컬럼: 대시보드 표시/필터/집계에 필요한 최소 컬럼
    """
    sql = f"""
    WITH max_dt AS (
        SELECT MAX(work_date) AS max_work_date
        FROM {DB_SCHEMA}.{DB_TABLE}
        WHERE COALESCE(outlier_flag, '') <> '이상치'
    )
    SELECT
        m.work_date,
        m.period,
        m.model,
        m.process_l1,
        m.equipment,
        m.cmp_achievement_rate,
        m.uph_achievement_rate,
        m.efficiency_achievement_rate,
        m.area
    FROM {DB_SCHEMA}.{DB_TABLE} m
    CROSS JOIN max_dt
    WHERE COALESCE(m.outlier_flag, '') <> '이상치'
      AND max_dt.max_work_date IS NOT NULL
      AND m.work_date >= (max_dt.max_work_date - (:lookback_months * INTERVAL '1 month'))
    ORDER BY m.work_date, m.model, m.area, m.process_l1
    """

    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), con=conn, params={"lookback_months": DASHBOARD_DB_LOOKBACK_MONTHS})

    rename_map = {
        'model': '모델',
        'process_l1': '공정명 (L1)',
        'equipment': '설비',
        'period': '기간',
        'cmp_achievement_rate': 'CMP 달성률',
        'uph_achievement_rate': 'UPH 달성률',
        'efficiency_achievement_rate': 'Efficiency 달성률',
        'area': '영역',
        'work_date': '기준일자',
    }
    df = df.rename(columns=rename_map)

    # period가 비어 있거나 DB에 없는 경우 work_date 기준으로 기존 형식의 기간 컬럼 생성
    if '기간' not in df.columns and '기준일자' in df.columns:
        dt = pd.to_datetime(df['기준일자'], errors='coerce')
        df['기간'] = dt.dt.strftime('%Y-%m-%d 07:00:00') + '~' + (dt + pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d 07:00:00')
    elif '기간' in df.columns and '기준일자' in df.columns:
        missing_period = df['기간'].isna() | (df['기간'].astype(str).str.strip() == '')
        if missing_period.any():
            dt = pd.to_datetime(df.loc[missing_period, '기준일자'], errors='coerce')
            df.loc[missing_period, '기간'] = dt.dt.strftime('%Y-%m-%d 07:00:00') + '~' + (dt + pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d 07:00:00')

    for c in ['영역', '모델', '공정명 (L1)', '설비']:
        if c in df.columns:
            df[c] = clean_text_series(df[c])

    numeric_cols = ['CMP 달성률', 'UPH 달성률', 'Efficiency 달성률']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    df = df.replace([np.inf, -np.inf], np.nan)
    return df

def parse_date_from_period(series: pd.Series) -> pd.Series:
    start = series.astype(str).str.split('~').str[0].str.strip()
    return pd.to_datetime(start, errors='coerce').dt.normalize()


def month_label(dt: pd.Timestamp) -> str:
    return f"'{str(dt.year)[-2:]}.{dt.month}월"


def week_of_month(dt: pd.Timestamp) -> int:
    return int(((dt.day - 1) // 7) + 1)


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    num = pd.to_numeric(num, errors='coerce')
    den = pd.to_numeric(den, errors='coerce')
    out = num / den
    return out.replace([np.inf, -np.inf], np.nan)


def clean_text_series(s: pd.Series) -> pd.Series:
    """문자열 컬럼 정리: strip 후 nan/None/빈값/- 를 결측으로 통일"""
    s = s.astype("string").str.strip()
    bad = {"nan", "None", "", "-"}
    s = s.mask(s.isin(bad))
    return s.astype(object)


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{v * 100:.1f}%'


def achievement_color(v):
    if pd.isna(v):
        return '#ffffff'
    if v >= 1.00:
        return '#F7F8FA'
    elif v >= 0.95:
        return '#FAF1DD'
    else:
        return '#F8E5EC'

def apply_common_css():
    css = """
    <style>
    @font-face {
        font-family: 'LGLocal';
        src: local('LG Smart_H'), local('LGSmHaTR'), local('LG Smart');
        font-display: swap;
    }
    @font-face {
        font-family: 'ArialLocal';
        src: local('Arial Narrow'), local('Arial'), local('ARIALN');
        font-display: swap;
    }

    /* PERF: 페이지 토큰을 Vitals 팔레트와 정렬 — 클래스 이름은 그대로 두되 값만 교체.
       모든 .section-heading / .block-wrap / .filter-box / .summary-table 등이
       자동으로 와인 + Vitals status 색으로 통일. 함수 시그니처·DOM 구조 0 변경. */
    :root {
        /* Page-local 별칭 → Vitals 정식 토큰 (--page-bg, --card-bg, --soft,
           --border, --ink-body 등) 으로 fallback. 두 이름 모두 사용 가능. */
        --bg:           var(--page-bg, #F7F8FA);
        --page-bg:      #F7F8FA;
        --surface:      var(--card-bg, #FFFFFF);
        --card-bg:      #FFFFFF;
        --surface-soft: var(--soft, #F1F3F5);
        --soft:         #F1F3F5;
        --surface-muted:#F1F3F5;
        --line:         var(--border, #E5E7EB);
        --border:       #E5E7EB;
        --line-strong:  #CBD0D6;
        --ink:          var(--ink-body, #1F2430);
        --ink-body:     #1F2430;
        --muted:        var(--ink-muted, #6B7280);
        --ink-muted:    #6B7280;
        --accent-rose:  var(--primary, #A50034);
        --primary:      #A50034;
        --accent-blue:  var(--primary-dark, #7E0027);
        --primary-dark: #7E0027;
        --accent-violet:#7E0027;
        --accent-navy:  #A50034;
        --good:         var(--status-good-tint, #E6F4EA);
        --status-good:  #1F8B4C;
        --mid:          var(--status-warn-tint, #FAF1DD);
        --status-warn:  #B57F1B;
        --bad:          var(--status-bad-tint, #FDECEF);
        --status-bad:   #B23A48;
        --shadow: 0 8px 22px -4px rgba(15,17,21,0.06);
        --radius: 12px;
    }

    /* 전체 UI 글꼴 — ui.vitals.theme 의 LG EI Text/Headline 스택 사용.
       페이지 단위로 override 하지 않음. */

    .stApp {
        background: linear-gradient(180deg, #FFFFFF 0%, #F7F8FA 100%);
        color: var(--ink);
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.2rem;
        max-width: 1880px;
    }
    h1, h2, h3, h4, h5, h6, body, p, label, div, span {
        color: var(--ink);
    }
    .stApp h1 {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
        letter-spacing: -0.02em;
    }
    .stApp h2 {
        font-size: 1.25rem;
        font-weight: 800;
        margin-top: 0.2rem;
        margin-bottom: 0.8rem;
        letter-spacing: -0.01em;
    }
    .page-shell {
        background: var(--surface);
        border: 1px solid var(--line);
        border-top: 3px solid var(--accent-navy);
        border-radius: 0;
        box-shadow: var(--shadow);
        padding: 18px 22px 16px 22px;
        margin-bottom: 18px;
    }
    .page-eyebrow {
        font-size: 12px;
        font-weight: 700;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .page-subtitle {
        color: var(--muted);
        font-size: 13px;
        margin-top: 4px;
    }
    .section-wrap {
        margin-top: 14px;
        margin-bottom: 18px;
    }
    .section-heading {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    .section-heading .bar {
        width: 4px;
        height: 18px;
        background: var(--primary, var(--accent-rose));   /* preview cmp-sub-head 와 동일 — wine 단색, radius:0 */
    }
    .section-heading .title {
        font-size: 22px;
        font-weight: 800;
        color: var(--ink);
        line-height: 1.1;
        letter-spacing: -0.02em;
    }
    .section-heading .desc {
        color: var(--muted);
        font-size: 12px;
        margin-left: 4px;
    }

    .filter-box, .filter-panel {
        padding: 14px 16px 10px 16px;
        border: 1px solid var(--line);
        border-radius: 0;
        background: linear-gradient(180deg, #ffffff 0%, #FFFFFF 100%);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.92);
        margin-bottom: 14px;
    }
    .filter-panel h3, .filter-box h3 { margin: 0 0 8px 0 !important; }

    .stMultiSelect [data-baseweb='tag'],
    div[data-baseweb='tag'],
    span[data-baseweb='tag'] {
        background: linear-gradient(180deg, #ffffff 0%, #F7F8FA 100%) !important;
        border: 1px solid var(--line) !important;
        color: var(--ink) !important;
        border-radius: 0!important;
        box-shadow: 0 1px 3px rgba(31, 36, 48, 0.04) !important;
        padding-left: 2px !important;
        padding-right: 2px !important;
    }
    .stSelectbox [data-baseweb='select'] > div,
    .stMultiSelect [data-baseweb='select'] > div,
    .stDateInput > div > div,
    .stTextInput > div > div > input {
        background: linear-gradient(180deg, #ffffff 0%, #FFFFFF 100%) !important;
        border: 1px solid var(--line) !important;
        border-radius: 0!important;
        min-height: 42px !important;
        box-shadow: 0 2px 8px rgba(31, 36, 48, 0.04) !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }
    .stSelectbox [data-baseweb='select'] > div:hover,
    .stMultiSelect [data-baseweb='select'] > div:hover,
    .stDateInput > div > div:hover {
        border-color: var(--line-strong) !important;
        background: #ffffff !important;
    }
    .stSelectbox [data-baseweb='select']:focus-within > div,
    .stMultiSelect [data-baseweb='select']:focus-within > div,
    .stDateInput > div:focus-within > div {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(111, 143, 189, 0.12) !important;
        background: #ffffff !important;
    }
    .stSelectbox label p,
    .stMultiSelect label p,
    .stDateInput label p {
        font-weight: 700 !important;
        color: var(--ink) !important;
        letter-spacing: -0.01em;
    }
    div[data-baseweb='popover'] {
        border-radius: 0!important;
        overflow: hidden !important;
        border: 1px solid var(--line) !important;
        box-shadow: 0 14px 32px rgba(31, 36, 48, 0.10) !important;
        background: #ffffff !important;
    }
    div[role='listbox'] {
        padding: 6px !important;
        background: #ffffff !important;
    }
    div[role='option'] {
        border-radius: 0!important;
        margin: 2px 4px !important;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
    }
    div[role='option'][aria-selected='true'] {
        background: #F7F8FA !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }
    div[role='option']:hover {
        background: #F7F8FA !important;
    }

    .block-wrap {
        background: var(--surface);
        border: 1px solid var(--line);
        border-top: 3px solid var(--accent-navy);
        border-radius: 0;
        box-shadow: var(--shadow);
        padding: 16px 16px 14px 16px;
        margin-top: 10px;
        margin-bottom: 22px;
    }
    .model-box {
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
        border: 1px solid var(--line);
        border-radius: 0;
        min-height: 850px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-weight: 800;
        font-size: 19px;
        color: var(--ink);
        padding: 20px 14px;
        white-space: pre-line;
        letter-spacing: -0.01em;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.95);
    }

    .summary-table, .worst-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 12px;
        table-layout: fixed;
        overflow: hidden;
        border-radius: 0;
        border: 1px solid var(--line);
    }
    .summary-table th, .summary-table td,
    .worst-table th, .worst-table td {
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        text-align: center;
        padding: 7px 4px;
        vertical-align: middle;
        word-wrap: break-word;
        background: #fff;
    }
    .summary-table th:last-child, .summary-table td:last-child,
    .worst-table th:last-child, .worst-table td:last-child {
        border-right: 0;
    }
    .summary-table tr:last-child td,
    .worst-table tr:last-child td {
        border-bottom: 0;
    }
    .summary-table thead th,
    .worst-table thead th {
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
        font-weight: 800;
        color: var(--ink);
    }
    .table-title {
        font-weight: 800;
        margin: 0 0 8px 0;
        font-size: 15px;
        color: var(--ink);
        letter-spacing: -0.01em;
    }
    .section-space { height: 10px; }
    .small-note { color: var(--muted); font-size: 11px; }
    div[data-testid='stCaptionContainer'] p { color: var(--muted); }

    div[data-testid='stMetric'] {
        background: linear-gradient(180deg, #ffffff 0%, #F7F8FA 100%);
        border: 1px solid var(--line);
        border-radius: 0;
        padding: 10px 12px;
        box-shadow: var(--shadow);
    }

    .stDownloadButton button,
    .stButton button {
        border-radius: 0!important;
        border: 1px solid var(--line) !important;
        background: linear-gradient(180deg, #ffffff 0%, #F7F8FA 100%) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }

    .st-frozen-wrap {
        max-height: 700px;
        overflow: auto;
        border: 1px solid var(--line);
        border-radius: 0;
        background: #ffffff;
    }
    table.sticky-cmp {
        border-collapse: separate;
        border-spacing: 0;
        width: max-content;
        min-width: 100%;
        font-size: 13px;
    }
    table.sticky-cmp th,
    table.sticky-cmp td {
        border-right: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        padding: 6px 10px;
        white-space: nowrap;
        text-align: center;
    }
    table.sticky-cmp thead th {
        position: sticky;
        top: 0;
        z-index: 20;
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
        font-weight: 800;
    }
    table.sticky-cmp th:first-child,
    table.sticky-cmp td:first-child {
        border-left: 1px solid var(--line);
    }
    table.sticky-cmp thead tr:first-child th {
        border-top: 1px solid var(--line);
    }
    .sticky-col-1 { position: sticky; left: 0px; z-index: 12; background: #ffffff; }
    .sticky-col-2 { position: sticky; left: 90px; z-index: 12; background: #ffffff; }
    .sticky-col-3 { position: sticky; left: 210px; z-index: 12; background: #ffffff; }
    table.sticky-cmp thead .sticky-col-1,
    table.sticky-cmp thead .sticky-col-2,
    table.sticky-cmp thead .sticky-col-3 {
        z-index: 25;
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
    }
    .col-model { min-width: 90px; max-width: 90px; width: 90px; }
    .col-factory { min-width: 120px; max-width: 120px; }
    .col-process { min-width: 220px; max-width: 220px; text-align: left !important; }
    .col-date { min-width: 90px; max-width: 90px; }
    .left-text { text-align: left !important; }


    /* =========================================================
       추가 요구사항
       1) 전체 글꼴: 맑은 고딕
       2) Streamlit 기본 상단/좌측 구성요소 삭제/투명화
       3) 상단 메뉴 복귀 버튼 스타일
       ========================================================= */
    /* 폰트 override 제거 — ui.vitals.theme LG EI 스택 사용 */

    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        border: 0 !important;
    }
    /* 사이드바 hide CSS 제거 (2026-05-10) — 모든 페이지에서 사이드바 작동 보장.
       이전 엔지니어 inline hide 룰이 cascade 되어 toggle 클릭 후에도 width 0
       유지. 표현 layer 만 변경, 백엔드 무영향. */
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    .home-button-wrap {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        margin: 0 0 10px 0;
    }
    .home-button-wrap div[data-testid="stButton"] {
        width: auto !important;
    }
    .home-button-wrap .stButton > button,
    .home-button-wrap button[kind="secondary"] {
        height: 34px !important;
        padding: 0 14px !important;
        border-radius: 0!important;
        border: 1px solid var(--line-strong) !important;
        background: #ffffff !important;
        color: var(--ink) !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        box-shadow: 0 6px 18px rgba(31, 36, 48, 0.08) !important;
    }
    .home-button-wrap .stButton > button:hover,
    .home-button-wrap button[kind="secondary"]:hover {
        border-color: var(--accent-navy) !important;
        color: var(--accent-navy) !important;
        transform: translateY(-1px);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
def load_top_data(path: str):
    df = read_csv_flex(path)
    required = [FACTORY_COL, MODEL_COL, PROCESS_COL, PERIOD_COL, CMP_COL, 'UPH 달성률', 'Efficiency 달성률']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f'필수 컬럼이 없습니다: {missing}')

    work = df.copy()
    work['날짜'] = parse_date_from_period(work[PERIOD_COL])
    for c in [FACTORY_COL, MODEL_COL, PROCESS_COL]:
        work[c] = clean_text_series(work[c])

    numeric_cols = [CMP_COL, 'UPH 달성률', 'Efficiency 달성률']
    for c in numeric_cols:
        work[c] = pd.to_numeric(work[c], errors='coerce')
    work = work.replace([np.inf, -np.inf], np.nan)
    work = work.dropna(subset=[FACTORY_COL, MODEL_COL, PROCESS_COL, '날짜', CMP_COL]).copy()

    # DB에서 이미 계산된 달성률 컬럼 사용
    for c in [CMP_COL, 'UPH 달성률', 'Efficiency 달성률']:
        work.loc[(work[c] <= 0) | (work[c] > MAX_VALID_ACHIEVEMENT), c] = np.nan

    work = work.dropna(subset=[CMP_COL]).copy()
    work['월표시'] = work['날짜'].map(month_label)
    work['주차'] = work['날짜'].map(week_of_month)
    work['주차표시'] = work['주차'].astype(str) + 'W'
    return work

def apply_top_filters(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if df.empty or df['날짜'].dropna().empty:
        st.warning('상단 표시 가능한 날짜 데이터가 없습니다.')
        return df.iloc[0:0].copy()

    factories = sorted(df[FACTORY_COL].dropna().unique().tolist())
    models = sorted(df[MODEL_COL].dropna().unique().tolist())
    min_dt = df['날짜'].dropna().min().date()
    max_dt = df['날짜'].dropna().max().date()
    default_start = (pd.Timestamp(max_dt) - pd.DateOffset(months=3)).date()
    if default_start < min_dt:
        default_start = min_dt

    st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.0, 2.2, 1.3])
    with c1:
        sel_factory = st.multiselect('영역', factories, default=factories, key=f'{prefix}_factory')
    with c2:
        sel_model = st.multiselect('모델', models, default=models, key=f'{prefix}_model')
    with c3:
        sel_dates = st.date_input('기간', value=(default_start, max_dt), min_value=min_dt, max_value=max_dt, key=f'{prefix}_dates')
    st.markdown("</div>", unsafe_allow_html=True)

    if isinstance(sel_dates, tuple) and len(sel_dates) == 2:
        start_date = pd.to_datetime(sel_dates[0])
        end_date = pd.to_datetime(sel_dates[1])
    else:
        start_date = pd.to_datetime(min_dt)
        end_date = pd.to_datetime(max_dt)

    out = df.copy()
    if sel_factory:
        out = out[out[FACTORY_COL].isin(sel_factory)]
    if sel_model:
        out = out[out[MODEL_COL].isin(sel_model)]
    out = out[(out['날짜'] >= start_date) & (out['날짜'] <= end_date)]
    return out


def percent_axis_formatter(x, pos):
    return f'{x:.1f}%'


def make_line_chart(daily: pd.DataFrame, y_col: str, title: str, color: str):
    fp_kr = get_matplotlib_korean_fontprop()

    fig, ax = plt.subplots(figsize=(7.2, 2.9), facecolor='#ffffff')
    ax.set_facecolor('#FFFFFF')
    y = daily[y_col] * 100
    x = daily['날짜']

    ax.plot(x, y, color=color, marker='o', linewidth=2.4, markersize=6, solid_capstyle='round')
    ax.fill_between(x, y, [CHART_YMIN] * len(y), color=color, alpha=0.07)

    if fp_kr is not None:
        ax.set_title(title, fontsize=10.5, fontweight='bold', loc='left', pad=8, fontproperties=fp_kr)
    else:
        ax.set_title(title, fontsize=10.5, fontweight='bold', loc='left', pad=8)

    ax.set_ylim(CHART_YMIN, CHART_YMAX)
    ax.yaxis.set_major_formatter(FuncFormatter(percent_axis_formatter))
    ax.grid(axis='y', linestyle='--', linewidth=0.7, alpha=0.22, color='#6b7280')
    ax.grid(axis='x', visible=False)
    ax.tick_params(axis='x', labelsize=8, pad=6, colors='#6B7280')
    ax.tick_params(axis='y', labelsize=8, colors='#6B7280')

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')

    if fp_kr is not None:
        for lbl in ax.get_xticklabels():
            lbl.set_fontproperties(fp_kr)
        for lbl in ax.get_yticklabels():
            lbl.set_fontproperties(fp_kr)

    for xi, yi in zip(x, y):
        if not pd.isna(yi):
            text_kwargs = dict(
                ha='center', va='bottom', fontsize=7.2, color='#6B7280',
                bbox=dict(boxstyle='round,pad=0.18', fc='#ffffff', ec='none', alpha=0.85),
            )
            if fp_kr is not None:
                text_kwargs['fontproperties'] = fp_kr
            ax.text(xi, yi + 1.2, f'{yi:.1f}%', **text_kwargs)

    fig.autofmt_xdate(rotation=0)
    fig.tight_layout(pad=1.0)
    return fig

def build_summary_matrix(model_df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        model_df.groupby(['월표시', '주차', '주차표시'], dropna=False)
        .agg(CMP=(CMP_COL, 'mean'), UPH=('UPH 달성률', 'mean'), Efficiency=('Efficiency 달성률', 'mean'))
        .reset_index()
    )
    agg = agg.sort_values(['월표시', '주차'])
    return agg


def build_worst5_history(model_df: pd.DataFrame):
    weekly = (
        model_df.groupby([PROCESS_COL, '월표시', '주차', '주차표시'], dropna=False)[CMP_COL]
        .mean()
        .reset_index(name='CMP')
    )
    if weekly.empty or model_df.empty or model_df['날짜'].dropna().empty:
        return weekly, None

    # 조회된 데이터에서 가장 최근 날짜가 속한 주차를 기준으로 Worst 5 선정
    latest_date = model_df['날짜'].dropna().max()
    latest_month = month_label(latest_date)
    latest_week = week_of_month(latest_date)
    latest_week_label = f'{latest_week}W'

    latest_rows = weekly[(weekly['월표시'] == latest_month) & (weekly['주차'] == latest_week)].copy()
    if latest_rows.empty:
        return weekly.iloc[0:0].copy(), f'{latest_month} {latest_week_label}'

    latest_rows = latest_rows.sort_values('CMP', na_position='last').head(5).copy()
    latest_rows['_rank_key'] = range(1, len(latest_rows) + 1)
    target = latest_rows[[PROCESS_COL, '_rank_key']].drop_duplicates()

    hist = weekly.merge(target, on=PROCESS_COL, how='inner').copy()
    hist = hist.sort_values(['_rank_key', '월표시', '주차'])
    return hist, f'{latest_month} {latest_week_label}'


def render_summary_html(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "<div class='small-note'>표시할 요약 데이터가 없습니다.</div>"

    months = list(dict.fromkeys(summary['월표시'].tolist()))
    month_to_weeks = {m: summary.loc[summary['월표시'] == m, '주차표시'].drop_duplicates().tolist() for m in months}
    lookup = {}
    for _, r in summary.iterrows():
        lookup[(r['월표시'], r['주차표시'], 'CMP')] = r['CMP']
        lookup[(r['월표시'], r['주차표시'], 'UPH')] = r['UPH']
        lookup[(r['월표시'], r['주차표시'], 'Efficiency')] = r['Efficiency']

    html = []
    html.append("<div class='table-title'>■ 달성률</div>")
    html.append("<table class='summary-table'><thead><tr>")
    html.append("<th rowspan='2' style='width:84px;'>구분</th>")
    for m in months:
        html.append(f"<th colspan='{len(month_to_weeks[m])}'>{m}</th>")
    html.append("</tr><tr>")
    for m in months:
        for w in month_to_weeks[m]:
            html.append(f"<th>{w}</th>")
    html.append("</tr></thead><tbody>")
    for metric in ['CMP', 'UPH', 'Efficiency']:
        html.append(f"<tr><td><b>{metric}</b></td>")
        for m in months:
            for w in month_to_weeks[m]:
                v = lookup.get((m, w, metric), np.nan)
                html.append(f"<td style='background:{achievement_color(v)};'>{fmt_pct(v)}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return ''.join(html)


def render_worst5_html(worst_hist: pd.DataFrame, latest_week_label: str | None) -> str:
    if worst_hist.empty:
        return "<div class='small-note'>표시할 Worst 5 데이터가 없습니다.</div>"

    months = list(dict.fromkeys(worst_hist['월표시'].tolist()))
    month_to_weeks = {m: worst_hist.loc[worst_hist['월표시'] == m, '주차표시'].drop_duplicates().tolist() for m in months}
    processes = worst_hist[[PROCESS_COL, '_rank_key']].drop_duplicates().sort_values('_rank_key')[PROCESS_COL].tolist()
    rank_map = {p: i for i, p in enumerate(processes, start=1)}
    lookup = {(r[PROCESS_COL], r['월표시'], r['주차표시']): r['CMP'] for _, r in worst_hist.iterrows()}

    label = latest_week_label if latest_week_label else '최근 주차'
    html = []
    html.append(f"<div class='table-title'>■ CMP Worst 5 <span class='small-note'>({label} 기준)</span></div>")
    html.append("<table class='worst-table'><thead><tr>")
    html.append("<th rowspan='2' style='width:54px;'>Worst</th><th rowspan='2' style='width:140px;'>Process</th>")
    for m in months:
        html.append(f"<th colspan='{len(month_to_weeks[m])}'>{m}</th>")
    html.append("</tr><tr>")
    for m in months:
        for w in month_to_weeks[m]:
            html.append(f"<th>{w}</th>")
    html.append("</tr></thead><tbody>")
    for p in processes[:5]:
        html.append(f"<tr><td>{rank_map[p]}</td><td>{p}</td>")
        for m in months:
            for w in month_to_weeks[m]:
                v = lookup.get((p, m, w), np.nan)
                html.append(f"<td style='background:{achievement_color(v)};'>{fmt_pct(v)}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return ''.join(html)



def render_worst5_interactive(worst_hist: pd.DataFrame, latest_week_label: str | None, key_prefix: str) -> str | None:
    if worst_hist.empty:
        st.markdown("<div class='small-note'>표시할 Worst 5 데이터가 없습니다.</div>", unsafe_allow_html=True)
        return None

    months = list(dict.fromkeys(worst_hist['월표시'].tolist()))
    month_to_weeks = {m: worst_hist.loc[worst_hist['월표시'] == m, '주차표시'].drop_duplicates().tolist() for m in months}
    processes = worst_hist[[PROCESS_COL, '_rank_key']].drop_duplicates().sort_values('_rank_key')[PROCESS_COL].tolist()[:5]
    rank_map = {p: i for i, p in enumerate(processes, start=1)}
    lookup = {(r[PROCESS_COL], r['월표시'], r['주차표시']): r['CMP'] for _, r in worst_hist.iterrows()}

    state_key = f'{key_prefix}_selected_process'
    if state_key not in st.session_state or st.session_state[state_key] not in processes:
        st.session_state[state_key] = processes[0] if processes else None

    label = latest_week_label if latest_week_label else '최근 주차'
    st.markdown(f"<div class='table-title'>■ CMP Worst 5 <span class='small-note'>({label} 기준)</span></div>", unsafe_allow_html=True)
    st.caption('Process 버튼을 클릭하면 동일 기간의 CMP / UPH / Efficiency 달성률 상세가 아래에 표시됩니다.')

    all_week_labels = []
    for m in months:
        for w in month_to_weeks[m]:
            all_week_labels.append((m, w))

    header_cols = st.columns([0.5, 1.8] + [0.9] * len(all_week_labels))
    header_cols[0].markdown('**Worst**')
    header_cols[1].markdown('**Process**')
    for i, (m, w) in enumerate(all_week_labels, start=2):
        header_cols[i].markdown(f"**{m}<br>{w}**", unsafe_allow_html=True)

    for proc in processes:
        row_cols = st.columns([0.5, 1.8] + [0.9] * len(all_week_labels))
        row_cols[0].markdown(str(rank_map[proc]))
        if row_cols[1].button(str(proc), key=f'{key_prefix}_proc_{rank_map[proc]}', use_container_width=True):
            st.session_state[state_key] = proc
        for j, (m, w) in enumerate(all_week_labels, start=2):
            v = lookup.get((proc, m, w), np.nan)
            row_cols[j].markdown(
                f"<div style='background:{achievement_color(v)};padding:4px 2px;border-radius:0;text-align:center;'>{fmt_pct(v)}</div>",
                unsafe_allow_html=True,
            )

    return st.session_state.get(state_key)


def build_process_detail_matrix(model_df: pd.DataFrame, selected_process: str, worst_hist: pd.DataFrame) -> pd.DataFrame:
    if not selected_process or worst_hist.empty:
        return pd.DataFrame()

    period_weeks = (
        worst_hist[['월표시', '주차', '주차표시']]
        .drop_duplicates()
        .sort_values(['월표시', '주차'])
        .copy()
    )
    proc_df = model_df[model_df[PROCESS_COL] == selected_process].copy()
    if proc_df.empty:
        return pd.DataFrame()

    agg = (
        proc_df.groupby(['월표시', '주차', '주차표시'], dropna=False)
        .agg(CMP=(CMP_COL, 'mean'), UPH=('UPH 달성률', 'mean'), Efficiency=('Efficiency 달성률', 'mean'))
        .reset_index()
    )
    return period_weeks.merge(agg, on=['월표시', '주차', '주차표시'], how='left')


def render_process_detail_html(detail_df: pd.DataFrame, selected_process: str) -> str:
    if detail_df.empty:
        return "<div class='small-note'>선택한 공정의 동일 기간 CMP / UPH / Efficiency 데이터가 없습니다.</div>"

    months = list(dict.fromkeys(detail_df['월표시'].tolist()))
    month_to_weeks = {m: detail_df.loc[detail_df['월표시'] == m, '주차표시'].drop_duplicates().tolist() for m in months}
    lookup = {}
    for _, r in detail_df.iterrows():
        lookup[(r['월표시'], r['주차표시'], 'CMP')] = r['CMP']
        lookup[(r['월표시'], r['주차표시'], 'UPH')] = r['UPH']
        lookup[(r['월표시'], r['주차표시'], 'Efficiency')] = r['Efficiency']

    html = []
    html.append(f"<div class='table-title'>■ {selected_process} 동일 기간 상세</div>")
    html.append("<table class='summary-table'><thead><tr>")
    html.append("<th rowspan='2' style='width:110px;'>구분</th>")
    for m in months:
        html.append(f"<th colspan='{len(month_to_weeks[m])}'>{m}</th>")
    html.append("</tr><tr>")
    for m in months:
        for w in month_to_weeks[m]:
            html.append(f"<th>{w}</th>")
    html.append("</tr></thead><tbody>")
    for metric in ['CMP', 'UPH', 'Efficiency']:
        html.append(f"<tr><td><b>{metric}</b></td>")
        for m in months:
            for w in month_to_weeks[m]:
                v = lookup.get((m, w, metric), np.nan)
                html.append(f"<td style='background:{achievement_color(v)};'>{fmt_pct(v)}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return ''.join(html)


def render_worst5_process_dropdown(worst_hist: pd.DataFrame, key_prefix: str) -> str | None:
    if worst_hist.empty:
        return None

    processes = (
        worst_hist[[PROCESS_COL, '_rank_key']]
        .drop_duplicates()
        .sort_values('_rank_key')
        [PROCESS_COL]
        .tolist()[:5]
    )
    if not processes:
        return None

    st.caption('아래 드롭다운에서 공정을 선택하면 동일 기간 CMP / UPH / Efficiency 상세가 아래에 표시됩니다.')
    return st.selectbox(
        '상세 조회 공정 선택',
        options=processes,
        index=0,
        key=f'{key_prefix}_selected_process_dropdown',
    )


# -----------------------------
# Worst5 상세 영역 부분 rerun 최적화
# -----------------------------
_fragment_decorator = getattr(st, "fragment", None)


def _render_worst5_detail_body(model_df: pd.DataFrame, worst_hist: pd.DataFrame, key_prefix: str):
    """Worst5 상세 공정 선택 + 상세 테이블 렌더링 본문"""
    selected_process = render_worst5_process_dropdown(worst_hist, key_prefix)
    if selected_process:
        detail_df = build_process_detail_matrix(model_df, selected_process, worst_hist)
        st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
        st.markdown(render_process_detail_html(detail_df, selected_process), unsafe_allow_html=True)


if _fragment_decorator is not None:
    @_fragment_decorator
    def render_worst5_detail_fragment(model_df: pd.DataFrame, worst_hist: pd.DataFrame, key_prefix: str):
        """Streamlit 1.37+ 에서는 이 블록만 rerun 됩니다."""
        _render_worst5_detail_body(model_df, worst_hist, key_prefix)
else:
    def render_worst5_detail_fragment(model_df: pd.DataFrame, worst_hist: pd.DataFrame, key_prefix: str):
        """구버전 Streamlit fallback: fragment 미지원 시 일반 렌더링."""
        _render_worst5_detail_body(model_df, worst_hist, key_prefix)

def model_box_text(model_name: str) -> str:
    return model_name.replace('/', '/\n')


def render_top_model_section(model_df: pd.DataFrame, model_name: str):
    daily = (
        model_df.groupby('날짜', dropna=False)
        .agg(CMP=(CMP_COL, 'mean'), UPH=('UPH 달성률', 'mean'), Efficiency=('Efficiency 달성률', 'mean'))
        .reset_index()
        .sort_values('날짜')
        .tail(7)
    )
    summary = build_summary_matrix(model_df)
    worst_hist, latest_week_label = build_worst5_history(model_df)
    key_prefix = f"top_{abs(hash(str(model_name))) % 10**8}"

    st.markdown("<div class='block-wrap'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.35, 2.8, 4.0], gap='medium')
    with c1:
        st.markdown(f"<div class='model-box'>{model_box_text(model_name)}</div>", unsafe_allow_html=True)
    with c2:
        fig_cmp = make_line_chart(daily, 'CMP', f'CMP 달성률 ({model_name})', '#A50034')  # Vitals primary
        st.pyplot(fig_cmp, use_container_width=True)
        plt.close(fig_cmp)

        fig_uph = make_line_chart(daily, 'UPH', f'UPH 달성률 ({model_name})', '#B57F1B')  # Vitals status-warn
        st.pyplot(fig_uph, use_container_width=True)
        plt.close(fig_uph)

        fig_eff = make_line_chart(daily, 'Efficiency', f'Efficiency 달성률 ({model_name})', '#1F8B4C')  # Vitals status-good
        st.pyplot(fig_eff, use_container_width=True)
        plt.close(fig_eff)
    with c3:
        st.markdown(render_summary_html(summary), unsafe_allow_html=True)
        st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
        st.markdown(render_worst5_html(worst_hist, latest_week_label), unsafe_allow_html=True)
        # 핵심 개선: Worst5 상세 드롭다운 + 상세 테이블만 fragment로 분리 rerun
        render_worst5_detail_fragment(model_df, worst_hist, key_prefix)
    st.markdown("</div>", unsafe_allow_html=True)


def render_top_section(data_file: str):
    st.markdown("""
    <div class='section-wrap'>
      <div class='section-heading'>
        <div class='bar'></div>
        <div>
          <div class='title'>CMP 달성률 요약</div>
          <div class='desc'>초기 화면은 최근 3개월 달성률 실적입니다.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    try:
        df = load_top_data(data_file)
    except Exception as e:
        st.error(f'상단 페이지 데이터 로딩 오류: {e}')
        return

    if df.empty:
        st.warning('상단 페이지에 표시할 데이터가 없습니다.')
        return

    filtered = apply_top_filters(df, prefix='top')
    if filtered.empty:
        st.info('선택한 조건에 맞는 상단 데이터가 없습니다.')
        return

    model_order = filtered.groupby(MODEL_COL)['날짜'].max().sort_values(ascending=False).index.tolist()
    for model_name in model_order:
        model_df = filtered[filtered[MODEL_COL] == model_name].copy()
        if not model_df.empty:
            render_top_model_section(model_df, model_name)

def load_bottom_data(path: str) -> pd.DataFrame:
    df = read_csv_flex(path)
    required = [FACTORY_COL, MODEL_COL, PROCESS_COL, PERIOD_COL, CMP_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f'필수 컬럼이 없습니다: {missing}')

    if EQUIPMENT_COL not in df.columns:
        df[EQUIPMENT_COL] = np.nan

    period_start = df[PERIOD_COL].astype(str).str.split('~').str[0].str.strip()
    df['날짜'] = pd.to_datetime(period_start, errors='coerce').dt.normalize()
    for c in [FACTORY_COL, MODEL_COL, PROCESS_COL, EQUIPMENT_COL]:
        df[c] = clean_text_series(df[c])
    df[CMP_COL] = pd.to_numeric(df[CMP_COL], errors='coerce')
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=[FACTORY_COL, MODEL_COL, PROCESS_COL, '날짜', CMP_COL]).copy()
    df = df[(df[CMP_COL] > 0) & (df[CMP_COL] <= MAX_VALID_CMP)].copy()
    return df

@st.cache_data(show_spinner=False)
def build_bottom_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    row_avg = (
        df.groupby([MODEL_COL, FACTORY_COL, PROCESS_COL, '날짜'], dropna=False)[CMP_COL]
        .mean()
        .reset_index(name='평균 CMP 달성률')
    )
    row_avg['색상 기준 CMP'] = row_avg['평균 CMP 달성률']
    row_avg = row_avg.replace([np.inf, -np.inf], np.nan)
    return row_avg


def apply_bottom_filters(df: pd.DataFrame, prefix: str):
    if df.empty or df['날짜'].dropna().empty:
        st.warning('하단 표시 가능한 날짜 데이터가 없습니다.')
        today = pd.Timestamp.today().date()
        return df.iloc[0:0].copy(), today, today

    factories = sorted(df[FACTORY_COL].dropna().unique().tolist())
    processes = sorted(df[PROCESS_COL].dropna().unique().tolist())
    models = sorted(df[MODEL_COL].dropna().unique().tolist())
    min_dt = df['날짜'].dropna().min().date()
    max_dt = df['날짜'].dropna().max().date()
    default_from = (pd.Timestamp(max_dt) - pd.Timedelta(weeks=3)).date()
    if default_from < min_dt:
        default_from = min_dt

    st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
    row1_c1, row1_c2, row1_c3 = st.columns([1.25, 1.25, 1.0])
    with row1_c1:
        selected_factories = st.multiselect('영역', factories, default=factories, key=f'{prefix}_factory')
    with row1_c2:
        selected_models = st.multiselect('모델', models, default=models, key=f'{prefix}_model')
    with row1_c3:
        selected_processes = st.multiselect('공정', processes, default=processes, key=f'{prefix}_process')
    row2_c1, row2_c2 = st.columns([1, 1])
    with row2_c1:
        from_date = st.date_input('From', value=default_from, min_value=min_dt, max_value=max_dt, key=f'{prefix}_from')
    with row2_c2:
        to_date = st.date_input('To', value=max_dt, min_value=min_dt, max_value=max_dt, key=f'{prefix}_to')
    st.markdown("</div>", unsafe_allow_html=True)

    if from_date > to_date:
        st.error('From 날짜가 To 날짜보다 늦을 수 없습니다.')
        return df.iloc[0:0].copy(), from_date, to_date

    filt = df[
        df[FACTORY_COL].isin(selected_factories)
        & df[PROCESS_COL].isin(selected_processes)
        & df[MODEL_COL].isin(selected_models)
        & (df['날짜'] >= pd.Timestamp(from_date))
        & (df['날짜'] <= pd.Timestamp(to_date))
    ].copy()
    return filt, from_date, to_date


def build_bottom_pivot(filtered: pd.DataFrame):
    """공정 parent row + 설비 child row를 함께 생성하는 tree pivot.

    parent row: 모델/영역/공정 기준 일별 평균 CMP 달성률
    child row : 해당 공정 하위 equipment별 일별 평균 CMP 달성률
    """
    if filtered.empty:
        return pd.DataFrame(), pd.DataFrame()

    work = filtered.copy()
    if EQUIPMENT_COL not in work.columns:
        work[EQUIPMENT_COL] = np.nan

    date_values = sorted(work['날짜'].dropna().unique().tolist())
    date_cols = [f'{pd.Timestamp(d).month}/{pd.Timestamp(d).day}' for d in date_values]

    parent_avg = (
        work.groupby([MODEL_COL, FACTORY_COL, PROCESS_COL, '날짜'], dropna=False)[CMP_COL]
        .mean()
        .reset_index(name='평균 CMP 달성률')
    )
    parent_pivot = parent_avg.pivot_table(
        index=[MODEL_COL, FACTORY_COL, PROCESS_COL],
        columns='날짜',
        values='평균 CMP 달성률',
        aggfunc='mean'
    )

    equipment_avg = (
        work.dropna(subset=[EQUIPMENT_COL])
        .groupby([MODEL_COL, FACTORY_COL, PROCESS_COL, EQUIPMENT_COL, '날짜'], dropna=False)[CMP_COL]
        .mean()
        .reset_index(name='평균 CMP 달성률')
    )
    if equipment_avg.empty:
        equipment_pivot = pd.DataFrame()
    else:
        equipment_pivot = equipment_avg.pivot_table(
            index=[MODEL_COL, FACTORY_COL, PROCESS_COL, EQUIPMENT_COL],
            columns='날짜',
            values='평균 CMP 달성률',
            aggfunc='mean'
        )

    rows = []
    colors = []
    parent_index = list(parent_pivot.index)
    parent_index = sorted(parent_index, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))

    for seq, key_tuple in enumerate(parent_index):
        model, factory, process = key_tuple
        parent_key = f"p_{seq}"
        base = {
            '__row_type': 'parent',
            '__row_key': parent_key,
            '__parent_key': '',
            MODEL_COL: model,
            FACTORY_COL: factory,
            PROCESS_COL: process,
        }
        color_base = base.copy()
        for d, label in zip(date_values, date_cols):
            val = parent_pivot.loc[key_tuple, d] if d in parent_pivot.columns else np.nan
            base[label] = val
            color_base[label] = val
        rows.append(base)
        colors.append(color_base)

        if not equipment_pivot.empty:
            try:
                eq_slice = equipment_pivot.xs(key_tuple, level=[MODEL_COL, FACTORY_COL, PROCESS_COL], drop_level=False)
            except KeyError:
                eq_slice = pd.DataFrame()
            if not eq_slice.empty:
                eq_keys = list(eq_slice.index)
                eq_keys = sorted(eq_keys, key=lambda x: str(x[3]))
                for eq_key in eq_keys:
                    equipment = eq_key[3]
                    child = {
                        '__row_type': 'child',
                        '__row_key': f"{parent_key}_{abs(hash(str(equipment))) % 10**8}",
                        '__parent_key': parent_key,
                        MODEL_COL: '',
                        FACTORY_COL: '',
                        PROCESS_COL: f"└ {equipment}",
                    }
                    child_color = child.copy()
                    for d, label in zip(date_values, date_cols):
                        val = equipment_pivot.loc[eq_key, d] if d in equipment_pivot.columns else np.nan
                        child[label] = val
                        child_color[label] = val
                    rows.append(child)
                    colors.append(child_color)

    value_pivot = pd.DataFrame(rows)
    color_pivot = pd.DataFrame(colors)
    ordered_cols = ['__row_type', '__row_key', '__parent_key'] + LEFT_COLS + date_cols
    value_pivot = value_pivot.reindex(columns=ordered_cols)
    color_pivot = color_pivot.reindex(columns=ordered_cols)
    return value_pivot, color_pivot


def color_from_value(value):
    if pd.isna(value):
        return '#ffffff'
    if value >= 1.0:
        return '#F7F8FA'
    elif value >= 0.95:
        return '#FAF1DD'
    else:
        return '#F8E5EC'

def render_frozen_html_table(value_df: pd.DataFrame, color_df: pd.DataFrame) -> str:
    meta_cols = {'__row_type', '__row_key', '__parent_key'}
    date_cols = [c for c in value_df.columns if c not in set(LEFT_COLS) | meta_cols]
    table_id = "cmp_daily_table_wrap"

    html = []
    html.append("""
    <style>
    .cmp-daily-wrap {
        max-height: 710px;
        overflow: auto;
        border: 1px solid #E5E7EB;
        border-radius: 0;
        background: #ffffff;
        box-shadow: 0 8px 24px rgba(31, 36, 48, 0.05);
    }
    table.cmp-daily {
        border-collapse: separate;
        border-spacing: 0;
        width: max-content;
        min-width: 100%;
        font-size: 13px;
    }
    table.cmp-daily th,
    table.cmp-daily td {
        border-right: 1px solid #E5E7EB;
        border-bottom: 1px solid #E5E7EB;
        padding: 7px 10px;
        white-space: nowrap;
        text-align: center;
    }
    table.cmp-daily thead th {
        position: sticky;
        top: 0;
        z-index: 20;
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
        font-weight: 800;
        color: #1f2430;
    }
    table.cmp-daily th:first-child,
    table.cmp-daily td:first-child { border-left: 1px solid #E5E7EB; }
    table.cmp-daily thead tr:first-child th { border-top: 1px solid #E5E7EB; }
    .cmp-sticky-1 { position: sticky; left: 0px; z-index: 12; background: #ffffff; }
    .cmp-sticky-2 { position: sticky; left: 96px; z-index: 12; background: #ffffff; }
    .cmp-sticky-3 { position: sticky; left: 216px; z-index: 12; background: #ffffff; }
    table.cmp-daily thead .cmp-sticky-1,
    table.cmp-daily thead .cmp-sticky-2,
    table.cmp-daily thead .cmp-sticky-3 {
        z-index: 25;
        background: linear-gradient(180deg, #F7F8FA 0%, #F1F3F5 100%);
    }
    .cmp-col-model { min-width: 96px; max-width: 96px; width: 96px; overflow: hidden; text-overflow: ellipsis; }
    .cmp-col-factory { min-width: 120px; max-width: 120px; width: 120px; }
    .cmp-col-process { min-width: 260px; max-width: 260px; width: 260px; text-align: left !important; }
    .cmp-col-date { min-width: 92px; max-width: 92px; width: 92px; }
    .cmp-left-text { text-align: left !important; }
    .cmp-parent-row .cmp-col-process { font-weight: 800; cursor: pointer; color: #1f2430; }
    .cmp-parent-row:hover td { filter: brightness(0.985); }
    .cmp-child-row { display: none; }
    .cmp-child-row td { background-color: #FFFFFF; color: #1F2430; }
    .cmp-child-row .cmp-col-process { padding-left: 24px; font-weight: 600; color: #6B7280; }
    .tree-toggle {
        display: inline-flex;
        width: 18px;
        height: 18px;
        align-items: center;
        justify-content: center;
        border: 1px solid #CBD0D6;
        border-radius: 0;
        margin-right: 6px;
        background: #ffffff;
        font-size: 11px;
        color: #1F2430;
        vertical-align: middle;
    }
    .tree-equipment-icon {
        color: #9CA3AF;
        font-weight: 800;
        margin-right: 4px;
    }
    </style>
    """)
    html.append(f"<div id='{table_id}' class='cmp-daily-wrap'><table class='cmp-daily'><thead><tr>")
    html.append(f"<th class='cmp-sticky-1 cmp-col-model'>{MODEL_COL}</th>")
    html.append(f"<th class='cmp-sticky-2 cmp-col-factory'>{FACTORY_COL}</th>")
    html.append(f"<th class='cmp-sticky-3 cmp-col-process'>{PROCESS_COL}</th>")
    for c in date_cols:
        html.append(f"<th class='cmp-col-date'>{html_lib.escape(str(c))}</th>")
    html.append("</tr></thead><tbody>")

    for i in range(len(value_df)):
        row = value_df.iloc[i]
        color_row = color_df.iloc[i]
        row_type = str(row.get('__row_type', 'parent'))
        row_key = html_lib.escape(str(row.get('__row_key', f'row_{i}')))
        parent_key = html_lib.escape(str(row.get('__parent_key', '')))
        model = '' if pd.isna(row[MODEL_COL]) else str(row[MODEL_COL])
        factory = '' if pd.isna(row[FACTORY_COL]) else str(row[FACTORY_COL])
        process = '' if pd.isna(row[PROCESS_COL]) else str(row[PROCESS_COL])

        if row_type == 'child':
            html.append(f"<tr class='cmp-child-row' data-parent='{parent_key}'>")
        else:
            html.append(f"<tr class='cmp-parent-row' data-row-key='{row_key}'>")

        html.append(f"<td class='cmp-sticky-1 cmp-col-model cmp-left-text' title='{html_lib.escape(model)}'>{html_lib.escape(model)}</td>")
        html.append(f"<td class='cmp-sticky-2 cmp-col-factory cmp-left-text'>{html_lib.escape(factory)}</td>")

        if row_type == 'parent':
            process_html = f"<span class='tree-toggle' data-state='closed'>+</span>{html_lib.escape(process)}"
        else:
            clean_equipment = process.replace('└ ', '', 1)
            process_html = f"<span class='tree-equipment-icon'>└</span>{html_lib.escape(clean_equipment)}"
        html.append(f"<td class='cmp-sticky-3 cmp-col-process cmp-left-text'>{process_html}</td>")

        for c in date_cols:
            v = row[c]
            bg = color_from_value(color_row[c])
            text_value = '' if pd.isna(v) else f'{v:.1%}'
            html.append(f"<td class='cmp-col-date' style='background:{bg};'>{text_value}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    html.append(f"""
    <script>
    const wrap = document.getElementById('{table_id}');
    if (wrap) {{
        requestAnimationFrame(() => {{ wrap.scrollLeft = wrap.scrollWidth; }});
        setTimeout(() => {{ wrap.scrollLeft = wrap.scrollWidth; }}, 120);

        wrap.querySelectorAll('tr.cmp-parent-row').forEach((row) => {{
            row.addEventListener('click', () => {{
                const key = row.getAttribute('data-row-key');
                const toggle = row.querySelector('.tree-toggle');
                const children = wrap.querySelectorAll(`tr.cmp-child-row[data-parent="${{key}}"]`);
                if (!children || children.length === 0) return;
                const isOpen = toggle && toggle.getAttribute('data-state') === 'open';
                children.forEach((child) => {{
                    child.style.display = isOpen ? 'none' : 'table-row';
                }});
                if (toggle) {{
                    toggle.textContent = isOpen ? '+' : '-';
                    toggle.setAttribute('data-state', isOpen ? 'closed' : 'open');
                }}
            }});
        }});
    }}
    </script>
    """)
    return ''.join(html)

def render_bottom_section(data_file: str):
    st.markdown("""
    <div class='section-wrap'>
      <div class='section-heading'>
        <div class='bar'></div>
        <div>
          <div class='title'>CMP 달성률 일별 현황</div>
          <div class='desc'>모델·영역·공정 기준의 일별 평균 CMP 달성률을 업무형 테이블로 조회하는 영역</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    try:
        raw = load_bottom_data(data_file)
    except Exception as e:
        st.error(f'하단 페이지 데이터 로딩 실패: {e}')
        return

    if raw.empty:
        st.warning('하단 페이지에 표시할 데이터가 없습니다.')
        return

    filtered, from_date, to_date = apply_bottom_filters(raw, prefix='bottom')
    c1, c2 = st.columns(2)
    c1.metric('조회 시작', str(from_date))
    c2.metric('조회 종료', str(to_date))

    if filtered.empty:
        st.warning('하단 페이지: 선택한 조건에 해당하는 데이터가 없습니다.')
        return

    value_pivot, color_pivot = build_bottom_pivot(filtered)
    if value_pivot.empty:
        st.warning('하단 페이지: 피벗 결과가 비어 있습니다.')
        return

    st.markdown("<div class='table-title' style='margin-top:8px;'>일별 평균 CMP 달성률</div>", unsafe_allow_html=True)
    components.html(render_frozen_html_table(value_pivot, color_pivot), height=730, scrolling=False)

    # STAGE 2 primitive — UTF-8 BOM 포함, Excel 한글 호환.
    from ui.vitals.components import render_csv_export
    render_csv_export(value_pivot, label='테이블 CSV 다운로드',
                      filename='cmp_daily_table.csv',
                      key='cmp_daily_csv_dl')

def render_home_button():
    """상단 우측 메뉴선택 화면 복귀 버튼.
    st.switch_page를 사용하므로 URL 직접 이동보다 로그인 세션 유지에 유리합니다.
    """
    st.markdown('<div class="home-button-wrap">', unsafe_allow_html=True)
    if st.button("🏠 메뉴선택 화면으로 가기", key="go_home"):
        st.switch_page("pages/0_Home.py")
    st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("공정별 상세 분석")
def render_cmp_process_detail_dialog(process_name: str, model_name: str, rate: float):
    uph_rate = max(rate - 2.2, 68)
    eff_rate = min(rate + 1.4, 99.8)
    st.markdown(
        f"""
        <style>
        .cmp-dialog-head {{
            display:flex;align-items:center;justify-content:space-between;
            border-left:4px solid var(--primary);border-bottom:1px solid var(--border);
            padding:10px 12px;margin:-8px 0 10px;background:#fff;
        }}
        .cmp-dialog-title {{
            font-family:var(--font-display);font-size:18px;font-weight:800;
            color:var(--ink-body);line-height:1.15;margin:0;
        }}
        .cmp-dialog-meta {{
            display:flex;gap:16px;align-items:center;
            font-family:var(--font-mono);font-size:10px;color:var(--ink-muted);
            text-transform:uppercase;letter-spacing:.04em;
        }}
        .cmp-dialog-meta b {{ color:var(--ink-body);font-weight:800; }}
        .cmp-dialog-metric {{
            min-height:126px;border:1px solid var(--border);border-left:3px solid var(--primary);
            background:var(--soft);padding:16px 12px;display:flex;flex-direction:column;justify-content:center;
        }}
        .cmp-dialog-metric.uph {{ border-left-color:var(--status-warn); }}
        .cmp-dialog-metric.eff {{ border-left-color:var(--status-good); }}
        .cmp-dialog-metric__label {{
            font-family:var(--font-mono);font-size:10px;font-weight:800;
            color:var(--ink-muted);letter-spacing:.08em;text-transform:uppercase;
        }}
        .cmp-dialog-metric__value {{
            font-family:var(--font-mono);font-size:26px;font-weight:900;
            color:var(--ink-body);line-height:1.2;margin-top:6px;
        }}
        .cmp-dialog-metric__delta {{
            font-family:var(--font-mono);font-size:10px;font-weight:800;color:var(--status-bad);margin-top:2px;
        }}
        .cmp-dialog-table {{
            width:100%;border-collapse:collapse;border:1px solid var(--border);
            font-family:var(--font-mono);font-size:11px;background:#fff;
        }}
        .cmp-dialog-table th {{
            background:var(--primary-tint);color:var(--primary-dark);
            border-bottom:2px solid var(--primary);text-align:left;padding:7px;font-weight:900;
        }}
        .cmp-dialog-table td {{ border-top:1px solid var(--border);padding:6px 7px; }}
        .cmp-dialog-table td.num {{ text-align:right; }}
        .cmp-dialog-good {{ color:var(--status-good);font-weight:900; }}
        .cmp-dialog-bad {{ color:var(--status-bad);font-weight:900; }}
        </style>
        <div class="cmp-dialog-head">
          <div>
            <div class="cmp-dialog-meta"><span>PROCESS</span></div>
            <h3 class="cmp-dialog-title">{process_name}</h3>
          </div>
          <div class="cmp-dialog-meta">
            <span>모델 <b>{model_name}</b></span><span>대분류 <b>FOL</b></span>
            <span>갱신 <b>2026-05-07 23:50</b></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    csv_df = pd.DataFrame([
        {"호기": "EQ-12", "CMP": round(rate + 9.0, 1), "UPH": round(uph_rate + 7.4, 1), "EFF": round(eff_rate + 5.5, 1)},
        {"호기": "EQ-08", "CMP": round(rate + 7.4, 1), "UPH": round(uph_rate + 5.2, 1), "EFF": round(eff_rate + 4.3, 1)},
        {"호기": "EQ-22", "CMP": round(rate - 7.8, 1), "UPH": round(uph_rate - 7.4, 1), "EFF": round(eff_rate - 8.4, 1)},
    ])
    st.download_button(
        "CSV 내려받기",
        csv_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"cmp_detail_{model_name}_{process_name}.csv",
        mime="text/csv",
        key=f"cmp_detail_csv_{model_name}_{process_name}",
    )

    trend_df = pd.DataFrame({
        "일자": pd.date_range("2026-04-22", periods=7, freq="D"),
        "CMP": [rate - 2.0, rate - 1.2, rate - .8, rate + .4, rate - .3, rate + .9, rate],
        "UPH": [uph_rate - 1.2, uph_rate + .5, uph_rate - .4, uph_rate + 1.3, uph_rate + .2, uph_rate - .6, uph_rate],
        "EFF": [eff_rate - 2.0, eff_rate - 1.1, eff_rate + .6, eff_rate + .1, eff_rate + 1.5, eff_rate + 2.0, eff_rate],
    })
    left, mid, right = st.columns([0.9, 3.3, 2.2], gap="small")
    with left:
        st.markdown(
            f"""
            <div class="cmp-dialog-metric"><div class="cmp-dialog-metric__label">CMP 평균</div><div class="cmp-dialog-metric__value">{rate:.1f}%</div><div class="cmp-dialog-metric__delta">▼ 1.4% vs 이전</div></div>
            <div class="cmp-dialog-metric uph"><div class="cmp-dialog-metric__label">UPH 평균</div><div class="cmp-dialog-metric__value">{uph_rate:.1f}%</div><div class="cmp-dialog-metric__delta">▼ 0.6% vs 이전</div></div>
            <div class="cmp-dialog-metric eff"><div class="cmp-dialog-metric__label">EFFICIENCY 평균</div><div class="cmp-dialog-metric__value">{eff_rate:.1f}%</div><div class="cmp-dialog-metric__delta">▼ 0.4% vs 이전</div></div>
            """,
            unsafe_allow_html=True,
        )
    with mid:
        st.caption("CMP 달성률 (%) · 30일")
        st.line_chart(trend_df.set_index("일자")[["CMP"]], use_container_width=True, height=135)
        st.caption("UPH 달성률 (%) · 30일")
        st.line_chart(trend_df.set_index("일자")[["UPH"]], use_container_width=True, height=135)
        st.caption("Efficiency (%) · 30일")
        st.line_chart(trend_df.set_index("일자")[["EFF"]], use_container_width=True, height=135)
    with right:
        st.markdown(
            """
            <table class="cmp-dialog-table">
              <thead><tr><th>#</th><th>호기</th><th>CMP</th><th>UPH</th><th>EFF</th></tr></thead>
              <tbody>
                <tr><td>1</td><td>EQ-12</td><td class="num cmp-dialog-good">71.4%</td><td class="num">78.6%</td><td class="num">82.3%</td></tr>
                <tr><td>2</td><td>EQ-08</td><td class="num cmp-dialog-good">69.8%</td><td class="num">76.4%</td><td class="num">81.1%</td></tr>
                <tr><td>3</td><td>EQ-03</td><td class="num">66.5%</td><td class="num">73.8%</td><td class="num">78.9%</td></tr>
                <tr><td>4</td><td>EQ-15</td><td class="num">64.1%</td><td class="num">72.0%</td><td class="num">77.6%</td></tr>
                <tr><td>5</td><td>EQ-07</td><td class="num">63.2%</td><td class="num">71.4%</td><td class="num">76.4%</td></tr>
              </tbody>
            </table>
            <br>
            <table class="cmp-dialog-table">
              <thead><tr><th>#</th><th>호기</th><th>CMP</th><th>UPH</th><th>EFF</th></tr></thead>
              <tbody>
                <tr><td>1</td><td>EQ-22</td><td class="num cmp-dialog-bad">54.6%</td><td class="num">63.8%</td><td class="num">68.4%</td></tr>
                <tr><td>2</td><td>EQ-19</td><td class="num cmp-dialog-bad">56.2%</td><td class="num">65.4%</td><td class="num">70.1%</td></tr>
                <tr><td>3</td><td>EQ-25</td><td class="num cmp-dialog-bad">58.8%</td><td class="num">67.2%</td><td class="num">72.0%</td></tr>
                <tr><td>4</td><td>EQ-17</td><td class="num cmp-dialog-bad">60.4%</td><td class="num">68.6%</td><td class="num">73.8%</td></tr>
                <tr><td>5</td><td>EQ-21</td><td class="num cmp-dialog-bad">61.7%</td><td class="num">70.0%</td><td class="num">75.2%</td></tr>
              </tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )


def render_cmp_interactive_preview_controls():
    st.markdown(
        """
        <style>
        .cmp-native-filter {
            border: 1px solid var(--border);
            background: var(--card-bg);
            padding: 12px;
            margin: 0 0 12px;
        }
        .cmp-process-actions .stButton > button {
            min-height: 56px !important;
            justify-content: flex-start !important;
            text-align: left !important;
            white-space: normal !important;
            font-family: var(--font-mono) !important;
            font-size: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    from ui.vitals.components import render_sub_head, render_csv_export, render_toast

    render_sub_head("필터", "모델 · 공정 대분류 · 공정 · 기간")
    st.markdown('<div class="cmp-native-filter">', unsafe_allow_html=True)
    with st.form("cmp_preview_filter_form", border=False):
        f1, f2, f3, f4 = st.columns([1.3, 1.3, 1.8, 1.5])
        with f1:
            models = st.multiselect("모델", ["CM모델A", "CM모델B", "CM모델C"], default=["CM모델A", "CM모델B", "CM모델C"])
        with f2:
            areas = st.multiselect("공정 대분류", ["FOL", "MOL", "EOL"], default=["FOL", "MOL", "EOL"])
        with f3:
            processes = st.multiselect(
                "공정",
                ["Lens AA", "Flip Chip", "FOL Adhesion", "Module AA", "MOL Bonding", "Sensor UF"],
                default=["Lens AA", "Flip Chip", "FOL Adhesion", "Module AA"],
            )
        with f4:
            period = st.date_input("기간", value=(pd.Timestamp("2026-04-07").date(), pd.Timestamp("2026-05-07").date()))
        a1, a2, _ = st.columns([.9, .9, 5])
        applied = a1.form_submit_button("필터 적용", type="primary")
        reset = a2.form_submit_button("초기화")
    st.markdown('</div>', unsafe_allow_html=True)

    if applied:
        render_toast("CMP 필터가 적용되었습니다.", kind="success")
    if reset:
        st.session_state.pop("cmp_preview_filter_form", None)
        render_toast("CMP 필터를 초기화했습니다.", kind="info")

    process_rows = [
        ("CM모델A", "Lens AA", 96.4),
        ("CM모델A", "FOL Adhesion", 62.4),
        ("CM모델B", "MOL Bonding", 79.6),
        ("CM모델C", "Sensor UF", 89.7),
    ]
    selected_models = set(models or ["CM모델A", "CM모델B", "CM모델C"])
    selected_processes = set(processes or [row[1] for row in process_rows])
    visible_rows = [row for row in process_rows if row[0] in selected_models and row[1] in selected_processes]

    # 사용자 피드백 (2026-05-11) — 4-card mini row 제거. 모델별 공정 grid 는
    # render_cmp_models_interactive_grid() 가 12×3 = 36 cards 풀 그리드로 렌더.
    # 여기서는 CSV export 만 유지.
    export_df = pd.DataFrame(visible_rows, columns=["모델", "공정", "CMP"])
    render_csv_export(export_df, label="CSV 내보내기", filename="cmp_dashboard_preview.csv", key="cmp_preview_csv")


def render_cmp_models_interactive_grid():
    """3-model × 12-process 인터랙티브 그리드 — 시안 sec-cmp .cmp-models 매칭.
    각 카드 클릭 시 render_cmp_process_detail_dialog 모달 오픈.
    사용자 피드백 (2026-05-11): 정적 HTML 카드 → 실 클릭 가능 카드.
    Streamlit 패턴: 카드 클릭 → session_state 에 _cmp_dialog_args 저장 → rerun
    → 함수 끝에서 dialog 호출. 이렇게 하면 dialog 가 안정적으로 열림.
    """
    from ui.vitals.components import render_sub_head
    render_sub_head("모델별 공정 달성률", "카드 클릭 시 상세 분석 팝업 · 마지막 갱신 2026-05-07 23:50")

    models_data = [
        ("CM모델A", [
            ("Lens AA", 96.4, "good"),
            ("Flip Chip", 93.8, ""),
            ("FOL Adhesion", 62.4, "bad"),
            ("Module AA", 95.7, "good"),
            ("FPC Bonding", 92.1, ""),
            ("Bracket Att.", 94.0, ""),
            ("Laser Mark", 97.2, "good"),
            ("VCM Attach", 93.5, ""),
            ("Pre Focus", 94.6, ""),
            ("APS Test", 95.3, "good"),
            ("Sensor UF", 92.9, ""),
            ("DCR Test", 89.4, "bad"),
        ]),
        ("CM모델B", [
            ("Lens AA", 97.1, "good"),
            ("Flip Chip", 95.8, "good"),
            ("MOL Bonding", 79.6, "warn"),
            ("Module AA", 96.4, "good"),
            ("FPC Bonding", 95.1, "good"),
            ("Bracket Att.", 94.7, ""),
            ("Laser Mark", 97.5, "good"),
            ("VCM Attach", 94.3, ""),
            ("Pre Focus", 95.6, "good"),
            ("APS Test", 96.0, "good"),
            ("Sensor UF", 93.8, ""),
            ("DCR Test", 92.4, ""),
        ]),
        ("CM모델C", [
            ("Lens AA", 96.8, "good"),
            ("Flip Chip", 95.2, "good"),
            ("IRCF Attach", 92.5, ""),
            ("Module AA", 96.1, "good"),
            ("FPC Bonding", 94.4, ""),
            ("Bracket Att.", 95.0, "good"),
            ("Laser Mark", 97.3, "good"),
            ("VCM Attach", 94.0, ""),
            ("Pre Focus", 94.8, ""),
            ("APS Test", 95.4, "good"),
            ("Sensor UF", 89.7, "bad"),
            ("DCR Test", 93.1, ""),
        ]),
    ]
    st.markdown(
        """
        <style>
        .cmp-grid-wrap { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 18px; }
        .cmp-grid-col__head { display:flex; justify-content:space-between; align-items:center; padding:8px 10px; border-bottom:2px solid var(--primary); font-size:12px; font-weight:800; color:var(--ink-body); margin-bottom:6px; }
        .cmp-grid-col__head span:last-child { font-family:var(--font-mono); font-size:10px; color:var(--ink-subtle); font-weight:600; letter-spacing:.04em; }
        /* 카드 컬럼 안 stButton 을 grid 처럼 강제 — 3열 grid 의 각 cell 에 카드 한 장씩 */
        div[data-testid="stHorizontalBlock"]:has(.cmp-grid-col__head) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 4px !important;
        }
        /* 그리드 안 카드 자체 — 시안 .cmp-proc 매칭 */
        div[data-testid="stHorizontalBlock"]:has(.cmp-grid-col__head) [data-testid="stButton"] button {
            min-height: 52px !important;
            padding: 6px 8px !important;
            border: 1px solid var(--border) !important;
            background: var(--soft) !important;
            color: var(--ink-body) !important;
            font-family: var(--font-body) !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            white-space: pre-line !important;
            text-align: left !important;
            justify-content: flex-start !important;
            line-height: 1.25 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.cmp-grid-col__head) [data-testid="stButton"] button:hover {
            border-color: var(--primary) !important;
            background: var(--primary-tint) !important;
            color: var(--primary-dark) !important;
        }
        /* 상태별 색상 — st.button 으로는 클래스 못 붙이므로 모든 카드 균일 톤.
           시안의 good/warn/bad 색상은 향후 components.html iframe 으로 교체 가능. */
        </style>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="small")
    for col_idx, (model_name, procs) in enumerate(models_data):
        with cols[col_idx]:
            st.markdown(
                f'<div class="cmp-grid-col__head"><span>{model_name}</span><span>{len(procs)} 공정</span></div>',
                unsafe_allow_html=True,
            )
            # 카드 12개를 2열 그리드로 — Streamlit 자동 stack 후 CSS 가 grid 변환
            for proc_idx, (proc_name, rate, status) in enumerate(procs):
                # 사용자 피드백 (2026-05-11) — 한글 + 공백 키가 Streamlit 에서
                # 클릭 인식 실패. ASCII safe key 로 변경.
                btn_key = f"cmp_grid_{col_idx}_{proc_idx}"
                if st.button(
                    f"{proc_name}\n{rate:.1f}%",
                    key=btn_key,
                    use_container_width=True,
                ):
                    # 사용자 피드백 (2026-05-11) — Streamlit st.dialog 는 column
                    # context 안에서 호출 시 modal 이 안 뜸. session_state 에 args
                    # 저장 후, with-block 밖 (페이지 레벨) 에서 dialog 호출.
                    st.session_state["_cmp_dialog_args"] = (proc_name, model_name, rate)

    # column context 밖 — page level 에서 dialog 호출 (modal 정상 렌더 보장).
    if "_cmp_dialog_args" in st.session_state:
        args = st.session_state.pop("_cmp_dialog_args")
        render_cmp_process_detail_dialog(*args)


def render_cmp_preview_mock():
    """No-data preview surface matching docs/design sec-cmp.

    The production DB path above is untouched. This only replaces the empty
    development state so the Streamlit clone keeps the HTML mock visual shape.
    """
    render_cmp_interactive_preview_controls()
    # 사용자 피드백 (2026-05-11) — 모델별 공정 grid 를 인터랙티브로 교체.
    # 이전 정적 HTML mock 은 카드 클릭 안됨 → 모달 진입 불가.
    render_cmp_models_interactive_grid()
    st.markdown(
        """
        <style>
        .cmp-preview-filter{
            border:1px solid var(--border);
            background:#fff;
            padding:12px;
            display:grid;
            grid-template-columns:1fr 1fr;
            gap:12px 14px;
            margin:10px 0 14px;
        }
        .cmp-preview-field__label{
            color:var(--ink-body);
            font-size:11px;
            font-weight:800;
            margin-bottom:5px;
        }
        .cmp-preview-select{
            min-height:34px;
            border:1px solid var(--border);
            background:#fff;
            display:flex;
            align-items:center;
            gap:6px;
            padding:5px 8px;
        }
        .cmp-preview-chip{
            display:inline-flex;
            align-items:center;
            min-height:20px;
            padding:0 8px;
            background:var(--primary-tint);
            border:1px solid rgba(165,0,52,.18);
            color:var(--primary-dark);
            font-size:10px;
            font-weight:800;
        }
        .cmp-preview-actions{
            grid-column:1 / 3;
            display:flex;
            justify-content:flex-end;
            gap:8px;
        }
        .cmp-preview-btn{
            min-width:78px;
            height:34px;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            border:1px solid var(--border);
            background:#fff;
            color:var(--ink-body);
            font-size:12px;
            font-weight:800;
        }
        .cmp-preview-btn--primary{
            background:var(--primary);
            border-color:var(--primary);
            color:#fff;
        }
        .cmp-preview-kpis{
            display:grid;
            grid-template-columns:repeat(4, 1fr);
            gap:10px;
            margin:12px 0 18px;
        }
        .cmp-preview-kpi{
            border:1px solid var(--border);
            border-left:3px solid var(--primary);
            background:#fff;
            padding:13px 14px;
        }
        .cmp-preview-kpi__label{font-size:11px;font-weight:800;color:var(--ink-subtle);}
        .cmp-preview-kpi__value{font-family:var(--font-mono);font-size:24px;font-weight:800;color:var(--ink-body);line-height:1.15;}
        .cmp-preview-kpi__delta{font-family:var(--font-mono);font-size:11px;font-weight:800;color:var(--status-good);}
        .cmp-preview-section{
            display:flex;
            align-items:center;
            justify-content:space-between;
            border-bottom:1px solid var(--border);
            margin:8px 0 10px;
            padding-bottom:7px;
        }
        .cmp-preview-section__title{
            display:flex;
            align-items:center;
            gap:8px;
            font-size:14px;
            font-weight:800;
            color:var(--ink-body);
        }
        .cmp-preview-section__title::before{
            content:"";
            width:4px;
            height:18px;
            background:var(--primary);
        }
        .cmp-preview-section__meta{
            font-family:var(--font-mono);
            font-size:10px;
            color:var(--ink-subtle);
        }
        .cmp-preview-models{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            gap:10px;
            margin-bottom:18px;
        }
        .cmp-preview-model{
            border:1px solid var(--border);
            background:#fff;
            padding:9px;
        }
        .cmp-preview-model__head{
            display:flex;
            justify-content:space-between;
            align-items:center;
            font-size:12px;
            font-weight:800;
            margin-bottom:8px;
        }
        .cmp-preview-procs{
            display:grid;
            grid-template-columns:repeat(3,1fr);
            gap:4px;
        }
        .cmp-preview-proc{
            min-height:42px;
            border:1px solid var(--border);
            background:var(--soft);
            padding:5px 7px;
        }
        .cmp-preview-proc.good{background:#EEF8F2;border-color:#CFE8DA;}
        .cmp-preview-proc.warn{background:#FFF6E6;border-color:#EBDCBF;}
        .cmp-preview-proc.bad{background:#FBE8EF;border-color:#E8C5D2;}
        .cmp-preview-proc__name{font-size:10px;font-weight:700;color:var(--ink-body);}
        .cmp-preview-proc__val{font-family:var(--font-mono);font-size:13px;font-weight:800;}
        .cmp-preview-proc.good .cmp-preview-proc__val{color:var(--status-good);}
        .cmp-preview-proc.warn .cmp-preview-proc__val{color:var(--status-warn);}
        .cmp-preview-proc.bad .cmp-preview-proc__val{color:#B23A48;}
        .cmp-preview-table{
            width:100%;
            border-collapse:collapse;
            background:#fff;
            border:1px solid var(--border);
            font-size:11px;
        }
        .cmp-preview-table th{
            background:var(--primary-tint);
            color:var(--primary-dark);
            border-bottom:2px solid var(--primary);
            text-align:left;
            padding:8px;
            font-weight:800;
        }
        .cmp-preview-table td{
            border-top:1px solid var(--border);
            padding:7px 8px;
        }
        .cmp-preview-table td.num{text-align:right;font-family:var(--font-mono);}
        .cmp-preview-table .good{color:var(--status-good);font-weight:800;}
        .cmp-preview-table .bad{color:#B23A48;font-weight:800;}
        </style>
        <div class="cmp-preview-filter">
            <div class="cmp-preview-field"><div class="cmp-preview-field__label">모델</div><div class="cmp-preview-select"><span class="cmp-preview-chip">CM모델A ×</span><span class="cmp-preview-chip">CM모델B ×</span><span class="cmp-preview-chip">CM모델C ×</span></div></div>
            <div class="cmp-preview-field"><div class="cmp-preview-field__label">공정 대분류 (영역)</div><div class="cmp-preview-select"><span class="cmp-preview-chip">FOL ×</span><span class="cmp-preview-chip">MOL ×</span><span class="cmp-preview-chip">EOL ×</span></div></div>
            <div class="cmp-preview-field"><div class="cmp-preview-field__label">공정</div><div class="cmp-preview-select"><span class="cmp-preview-chip">Lens AA ×</span><span class="cmp-preview-chip">Flip Chip ×</span><span class="cmp-preview-chip">Module AA ×</span><span class="cmp-preview-chip">APS Test ×</span></div></div>
            <div class="cmp-preview-field"><div class="cmp-preview-field__label">기간</div><div class="cmp-preview-select">2026-04-07 ~ 2026-05-07</div></div>
            <div class="cmp-preview-actions"><span class="cmp-preview-btn">초기화</span><span class="cmp-preview-btn cmp-preview-btn--primary">필터 적용</span></div>
        </div>
        <div class="cmp-preview-kpis">
            <div class="cmp-preview-kpi"><div class="cmp-preview-kpi__label">전체 달성률</div><div class="cmp-preview-kpi__value">94.2%</div><div class="cmp-preview-kpi__delta">▲ +1.8% vs 이전</div></div>
            <div class="cmp-preview-kpi"><div class="cmp-preview-kpi__label">CM모델A 달성률</div><div class="cmp-preview-kpi__value">92.7%</div><div class="cmp-preview-kpi__delta" style="color:#B23A48;">▼ -0.4%</div></div>
            <div class="cmp-preview-kpi"><div class="cmp-preview-kpi__label">CM모델B 달성률</div><div class="cmp-preview-kpi__value">95.1%</div><div class="cmp-preview-kpi__delta">▲ +2.1%</div></div>
            <div class="cmp-preview-kpi"><div class="cmp-preview-kpi__label">CM모델C 달성률</div><div class="cmp-preview-kpi__value">94.8%</div><div class="cmp-preview-kpi__delta">▲ +1.5%</div></div>
        </div>
        <!-- 사용자 피드백 (2026-05-11) — 정적 모델별 공정 grid 는 위
             render_cmp_models_interactive_grid() 가 인터랙티브로 처리.
             여기서는 KPI row 와 공정 요약표만 표시. -->
        <div class="cmp-preview-section"><div class="cmp-preview-section__title">공정 요약표</div><div class="cmp-preview-section__meta">모델 × 공정 × 호기 × 기간 매트릭스</div></div>
        <table class="cmp-preview-table">
            <thead><tr><th>모델</th><th>공장</th><th>공정명</th><th>기간</th><th>CMP</th><th>UPH</th><th>EFF.</th><th>Δ</th></tr></thead>
            <tbody>
                <tr><td>CM모델A</td><td>Gumi Campus 1</td><td>Lens AA</td><td>2026-04-22 - 28</td><td class="num">96.4%</td><td class="num">94.2%</td><td class="num">95.0%</td><td class="num good">+1.1</td></tr>
                <tr><td>CM모델A</td><td>Gumi Campus 3</td><td>FOL Adhesion</td><td>2026-04-22 - 28</td><td class="num bad">62.4%</td><td class="num">71.2%</td><td class="num">76.8%</td><td class="num bad">-1.4</td></tr>
                <tr><td>CM모델B</td><td>Gumi Campus 3</td><td>MOL Bonding</td><td>2026-04-22 - 28</td><td class="num" style="color:var(--status-warn);font-weight:800;">79.6%</td><td class="num">82.3%</td><td class="num">85.1%</td><td class="num bad">-0.8</td></tr>
                <tr><td>CM모델C</td><td>Gumi Campus 3</td><td>Sensor Underfill</td><td>2026-04-22 - 28</td><td class="num bad">89.7%</td><td class="num">87.2%</td><td class="num">88.4%</td><td class="num bad">-0.8</td></tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def main():
    set_korean_font()
    apply_common_css()
    data_file = resolve_data_file()
    try:
        _preview_probe = read_csv_flex(data_file)
    except Exception:
        _preview_probe = pd.DataFrame()

    if _preview_probe.empty:
        render_cmp_preview_mock()
        return

    try:
        _top_probe = load_top_data(data_file)
    except Exception:
        _top_probe = pd.DataFrame()
    try:
        _bottom_probe = load_bottom_data(data_file)
    except Exception:
        _bottom_probe = pd.DataFrame()

    if _top_probe.empty and _bottom_probe.empty:
        render_cmp_preview_mock()
        return

    render_home_button()
    st.markdown("""
    <ul class="vit-note-list">
      <li>CMP 대비 Capa / UPH / Efficiency 달성률을 확인할 수 있는 Dashboard입니다.</li>
    </ul>
    """, unsafe_allow_html=True)

    render_top_section(data_file)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    render_bottom_section(data_file)

if __name__ == '__main__':
    main()
