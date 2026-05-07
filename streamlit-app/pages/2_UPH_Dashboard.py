from __future__ import annotations

import os
import re
import json
import requests
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from plotly.subplots import make_subplots
from access_logger import log_page_access

import configparser
from auth_guard import require_login
require_login(
    page_name="UPH_dashboard",
    page_path="pages/2_UPH_Dashboard.py"
)

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

log_page_access("2_UPH_Dashboard")

from ui.analytics import inject_tracker
inject_tracker(page_name="2_UPH_Dashboard", page_path="pages/2_UPH_Dashboard.py")

DEFAULT_DB_HOST = 'localhost'
DEFAULT_DB_PORT = 5432
DEFAULT_DB_NAME = 'I-TAS_Data'
DEFAULT_DB_USER = 'postgres'
DEFAULT_DB_PASSWORD = None  # Resolved at runtime from env / secrets only.
DEFAULT_DB_SCHEMA = 'public'

UPH_TABLE = 'itas_uph_result'
MOTION_TABLE = 'itas_motion_result'
SUMMARY_TABLE = 'itas_motion_daily_summary'
DEFAULT_MES_DB_NAME = 'MES_UPH'
MES_UPH_TABLE = 'uph_input_runtime_daily_model'
DIM_SELECTOR_TABLE = 'dim_mes_selector_map'
CACHE_TTL_SEC = 60

EXCLUDE_ACTION_PREFIXES = ('Y',)
MAX_ALLOWED_NULLS_PER_ACTION_ROW = 5
MIN_ACTION_AVG_DURATION_SEC = 0.015

UPH_DECIMALS = 0
DURATION_DECIMALS = 3
GAP_DECIMALS = 3
PERCENT_DECIMALS = 1

MOTION_CP_FILTER_VALUE = 'Y'
APP_TITLE = 'UPH / 동작시간 분석 Dashboard'
APP_CAPTION = 'PostgreSQL 기반 조회 (SQL 집계형 v3): itas_uph_result / itas_motion_result'

VLLM_BASE_URL = "http://150.150.83.26:8000/v1"
VLLM_MODEL_NAME = "/home/rgkorea/models/Qwen2.5-3B-Instruct"
AI_MAX_ROWS = 100

# Y축 고정/범위 설정
UPH_DEVIATION_Y_AXIS_MAX_PERCENT = 15.0
UPH_MACHINE_TREND_Y_RANGE_RATIO = 0.20

# Dashboard visual constants
# 그래프는 빨간색 계열 대신 제조 대시보드에서 무난한 Blue/Teal 계열을 사용합니다.
DASHBOARD_FONT_FAMILY = 'Malgun Gothic, 맑은 고딕, Arial, sans-serif'
CHART_PRIMARY_COLOR = '#A50034'   # main blue
CHART_SECONDARY_COLOR = '#1F8B4C' # teal
CHART_REFERENCE_COLOR = '#1F8B4C' # green reference/target line
CHART_MUTED_COLOR = '#9CA3AF'     # muted gray-blue
# 성능 최적화 포인트: 불필요한 선행 쿼리 제거, BW 전체테이블 세션 캐시 재사용


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    schema: str


def configure_page():
    st.set_page_config(
        page_title='UPH/동작시간 분석 대시보드 (PostgreSQL SQL 집계형 v4)',
        layout='wide',
        initial_sidebar_state='collapsed',
    )



def inject_vitals_theme():
    """
    VITALS UPH HTML 시안 기반 Streamlit 전역 디자인 패치.
    - Streamlit 기본 좌측 메뉴/상단 툴바 숨김
    - 상단 header 영역 투명 처리
    - 기존 요소 배치/로직은 유지하고 CSS로 모양/색상만 변경
    """
    st.markdown(
        """
<style>

:root{
  --v-primary:#A50034;
  --v-accent:#A50034;
  --v-primary-dark:#7E0027;
  --v-bg:#F7F8FA;
  --v-card:#FFFFFF;
  --v-border:#E5E7EB;
  --v-soft:#F1F3F5;
  --v-ink:#1F2430;
  --v-body:#1F2430;
  --v-muted:#6B7280;
  /* Vitals 정식 토큰 alias — components 점수 + 외부 일관성 */
  --page-bg:#F7F8FA;
  --card-bg:#FFFFFF;
  --soft:#F1F3F5;
  --border:#E5E7EB;
  --ink-body:#1F2430;
  --ink-muted:#6B7280;
  /* Status 시맨틱 — UPH 달성률 임계값 라벨 */
  --status-good:#1F8B4C;
  --status-warn:#B57F1B;
  --status-bad:#B23A48;
  --v-subtle:#9CA3AF;
  --v-good:#1F8B4C;
  --v-bad:#B23A48;
  --v-shadow:0 1px 2px rgba(17,24,39,.04), 0 8px 24px rgba(17,24,39,.035);
  --v-radius:8px;
}

/* 폰트는 ui.vitals.theme 의 LG EI Text/Headline 스택을 사용. 본 페이지에서는
   override 하지 않음 — 디자인 일관성 유지. */

body, .stApp{
  background:var(--v-bg) !important;
  color:var(--v-body) !important;
}

/* 1. Streamlit 기본 왼쪽 메뉴바 삭제 */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebar"],
div[data-testid="collapsedControl"]{
  display:none !important;
  width:0 !important;
  min-width:0 !important;
  visibility:hidden !important;
}

/* 2. Streamlit 기본 상단 영역 투명 처리 */
[data-testid="stHeader"]{
  background:transparent !important;
  height:0 !important;
  min-height:0 !important;
  box-shadow:none !important;
  border:0 !important;
}
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu, footer{
  display:none !important;
  visibility:hidden !important;
}

.block-container{
  max-width:none !important;
  padding-top:18px !important;
  padding-left:20px !important;
  padding-right:20px !important;
  padding-bottom:28px !important;
}

/* Page head - HTML 시안의 PERFORMANCE · UPH 헤더 */
.vitals-page-head{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:16px;
  margin:0 0 14px 0;
}
.vitals-eyebrow{
  font-size:10px;
  line-height:1;
  font-weight:800;
  letter-spacing:.11em;
  color:var(--v-primary);
  text-transform:uppercase;
  margin-bottom:8px;
}
.vitals-page-head h1{
  margin:0;
  font-size:26px;
  line-height:1.15;
  font-weight:800;
  letter-spacing:-.03em;
  color:var(--v-ink);
}
.vitals-page-head .vitals-sub{
  margin:7px 0 0 0;
  font-size:13px;
  color:var(--v-muted);
  font-weight:500;
}

/* 기본 제목/구분선 톤 정리 */
h1, h2, h3, h4{color:var(--v-ink) !important; letter-spacing:-.02em !important;}
h2, h3{font-weight:800 !important;}
hr{margin:12px 0 14px 0 !important; border:0 !important; border-top:1px solid var(--v-border) !important;}

/* 필터/컨텍스트 바 느낌: 기존 컬럼 배치는 유지, 위젯 외형만 변환 */
div[data-testid="stSelectbox"],
div[data-testid="stDateInput"],
div[data-testid="stSlider"],
div[data-testid="stCheckbox"]{
  background:var(--v-card);
  border:1px solid var(--v-border);
  border-radius:var(--v-radius);
  padding:8px 10px 7px 10px;
  box-shadow:0 1px 2px rgba(0,0,0,.035);
}
label[data-testid="stWidgetLabel"] p,
div[data-testid="stCheckbox"] label p{
  font-size:10px !important;
  line-height:1.1 !important;
  font-weight:800 !important;
  color:var(--v-muted) !important;
  letter-spacing:.06em !important;
}
div[data-baseweb="select"] > div,
input,
textarea{
  border-color:var(--v-border) !important;
  border-radius:6px !important;
  background:#fff !important;
  font-size:12px !important;
}

/* Streamlit button / download style */
.stButton > button, .stDownloadButton > button{
  border:1px solid var(--v-border) !important;
  background:#fff !important;
  color:var(--v-body) !important;
  border-radius:7px !important;
  height:32px !important;
  padding:0 12px !important;
  font-size:12px !important;
  font-weight:700 !important;
  box-shadow:0 1px 2px rgba(0,0,0,.04) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  border-color:var(--v-primary) !important;
  color:var(--v-primary) !important;
}

/* 카드형 섹션: 기존 st.container/plot/dataframe 위치는 유지 */
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"]{
  background:var(--v-card) !important;
  border:1px solid var(--v-border) !important;
  border-left:3px solid var(--v-accent) !important;
  border-radius:var(--v-radius) !important;
  padding:10px !important;
  box-shadow:var(--v-shadow) !important;
  overflow:hidden !important;
}

/* dataframe 내부를 HTML dev-row 느낌으로 */
div[data-testid="stDataFrame"] [role="grid"],
div[data-testid="stDataFrame"] canvas{
  border-radius:6px !important;
}

/* Metric이 존재할 경우 HTML KPI 카드와 유사하게 */
div[data-testid="metric-container"]{
  position:relative;
  background:var(--v-card) !important;
  border:1px solid var(--v-border) !important;
  border-radius:var(--v-radius) !important;
  padding:14px 16px 14px 18px !important;
  box-shadow:var(--v-shadow) !important;
  overflow:hidden !important;
}
div[data-testid="metric-container"]::before{
  content:"";
  position:absolute;
  left:0; top:0; bottom:0;
  width:3px;
  background:var(--v-accent);
}
div[data-testid="metric-container"] label{
  color:var(--v-muted) !important;
  font-size:10px !important;
  font-weight:800 !important;
  letter-spacing:.08em !important;
  text-transform:uppercase !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{
  color:var(--v-ink) !important;
  font-size:24px !important;
  font-weight:800 !important;
}

/* caption/info/warning */
.stCaption, [data-testid="stCaptionContainer"]{
  color:var(--v-muted) !important;
  font-size:11px !important;
}
div[data-testid="stAlert"]{
  border-radius:var(--v-radius) !important;
  border:1px solid var(--v-border) !important;
  border-left:3px solid var(--v-accent) !important;
  background:#fff !important;
}

/* expander 등 보조 요소 */
details[data-testid="stExpander"]{
  border:1px solid var(--v-border) !important;
  border-left:3px solid var(--v-accent) !important;
  border-radius:var(--v-radius) !important;
  background:var(--v-card) !important;
  box-shadow:var(--v-shadow) !important;
}
details[data-testid="stExpander"] summary{
  font-weight:800 !important;
  color:var(--v-ink) !important;
}

/* radio/segmented 느낌 */
div[role="radiogroup"]{
  gap:0 !important;
}
div[role="radiogroup"] label{
  background:#fff !important;
  border:1px solid var(--v-border) !important;
  padding:5px 9px !important;
  border-radius:6px !important;
  font-size:12px !important;
}

/* Plotly modebar를 미세하게 정리 */
.modebar{
  opacity:.16;
  transition:opacity .15s ease;
}
div[data-testid="stPlotlyChart"]:hover .modebar{opacity:.75;}



/* 우측 상단 Home 이동 버튼 */
.home-menu-button{
  position:fixed;
  top:16px;
  right:22px;
  z-index:999999;
  display:inline-flex;
  align-items:center;
  gap:7px;
  height:34px;
  padding:0 13px;
  border:1px solid var(--v-border);
  border-radius:999px;
  background:rgba(255,255,255,.94);
  color:var(--v-ink) !important;
  text-decoration:none !important;
  font-size:12px;
  font-weight:700;
  box-shadow:0 6px 18px rgba(15,23,42,.08);
  backdrop-filter:blur(8px);
}
.home-menu-button:hover{
  border-color:var(--v-primary);
  color:var(--v-primary) !important;
  transform:translateY(-1px);
  box-shadow:0 10px 24px rgba(37,99,235,.14);
}
.home-menu-icon{font-size:15px; line-height:1;}
.home-menu-text{white-space:nowrap;}

@media (max-width:1280px){
  .block-container{padding-left:14px !important; padding-right:14px !important;}
  .vitals-page-head{display:block;}
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_vitals_page_head():
    # preview sec-uph 와 정렬 — vit-top-strip 6px wine + flat eyebrow + h1.
    from ui.vitals.components import render_top_strip
    render_top_strip()
    st.markdown(
        """
<div class="vitals-page-head">
  <div class="vitals-page-head__eyebrow"
       style="display:flex;align-items:center;gap:8px;
              font-family:'IBM Plex Mono','SF Mono',Consolas,monospace;
              font-size:11px;font-weight:700;letter-spacing:.08em;
              text-transform:uppercase;color:var(--ink-muted,#6B7280);
              margin-bottom:6px;">
    <span style="display:inline-block;width:4px;height:14px;background:var(--primary);"></span>
    PRODUCTIVITY · UPH
  </div>
  <div>
    <h1>UPH / 동작시간 분석 Dashboard</h1>
    <p class="vitals-sub">조회 조건을 선택하세요.</p>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_home_button():
    # Streamlit 1.18 이상에서만 동작
    if st.button("🏠 메뉴선택 화면으로 가기", key="go_home"):
        st.switch_page("pages/0_Home.py")  # 또는 "pages/0_Home.py" 등 실제 Home 페이지 경로



def parse_date_text(text: str) -> Optional[pd.Timestamp]:
    text = (text or '').strip()
    if not text:
        return None
    try:
        return pd.to_datetime(text, errors='raise').normalize()
    except Exception:
        return None


def natural_machine_sort(values) -> list[str]:
    def key_func(v):
        s = str(v)
        nums = re.findall(r'\d+', s)
        num = int(nums[0]) if nums else 10**9
        return (num, s)

    return sorted(pd.Series(list(values)).astype(str).unique(), key=key_func)


def ensure_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.normalize()
    return df


def to_numeric_safe(df: pd.DataFrame, cols) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def format_float(v, digits=2):
    if pd.isna(v):
        return '-'
    return f'{float(v):,.{digits}f}'


def format_percent(v, digits=2):
    if pd.isna(v):
        return '-'
    return f'{float(v) * 100:.{digits}f}%'


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _resolve_required_password(secrets: dict) -> str:
    pw = secrets.get('password') or os.getenv('ITAS_DB_PASSWORD')
    if not pw:
        raise RuntimeError(
            "ITAS_DB_PASSWORD not configured. Set the env var or "
            "[postgres].password in .streamlit/secrets.toml. "
            "Hardcoded fallback removed."
        )
    return str(pw)


def load_db_config() -> DbConfig:
    secrets = {}
    if hasattr(st, 'secrets'):
        try:
            secrets = st.secrets.get('postgres', {})
        except Exception:
            secrets = {}

    return DbConfig(
        host=str(secrets.get('host', os.getenv('ITAS_DB_HOST', DEFAULT_DB_HOST))),
        port=int(secrets.get('port', os.getenv('ITAS_DB_PORT', DEFAULT_DB_PORT))),
        dbname=str(secrets.get('dbname', os.getenv('ITAS_DB_NAME', DEFAULT_DB_NAME))),
        user=str(secrets.get('user', os.getenv('ITAS_DB_USER', DEFAULT_DB_USER))),
        password=_resolve_required_password(secrets),
        schema=str(secrets.get('schema', os.getenv('ITAS_DB_SCHEMA', DEFAULT_DB_SCHEMA))),
    )


def get_db_connection(db: DbConfig):
    conn = psycopg2.connect(
        host=db.host,
        port=db.port,
        dbname=db.dbname,
        user=db.user,
        password=db.password,
        connect_timeout=10,
        application_name='UPH_Dashboard_ReadOnly',
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


def read_sql_df(query: str, db: DbConfig, params: Optional[dict] = None) -> pd.DataFrame:
    conn = get_db_connection(db)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def build_action_prefix_filter_sql(column_name: str) -> str:
    conditions = [f"{column_name} NOT LIKE '{prefix}%%'" for prefix in EXCLUDE_ACTION_PREFIXES]
    return ' AND '.join(conditions) if conditions else '1=1'


def filter_rows_by_null_count(df: pd.DataFrame, protected_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    value_cols = [c for c in df.columns if c not in protected_cols]
    if not value_cols:
        return df
    null_count = df[value_cols].isna().sum(axis=1)
    return df[null_count <= MAX_ALLOWED_NULLS_PER_ACTION_ROW].copy()


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def load_master_uph() -> pd.DataFrame:
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / 'Master' / 'Master_CMP.csv',
        base_dir / 'Master_UPH.csv',
        base_dir / 'Master_CMP.csv',
    ]
    target = next((p for p in candidates if p.exists()), None)
    if target is None:
        return pd.DataFrame(columns=['공정명', '기준 UPH'])

    df = pd.read_csv(target, encoding='utf-8-sig')
    cols = {str(c).strip(): c for c in df.columns}
    process_col = next((cols[n] for n in ['공정명', 'process_name', '공정', '시트명'] if n in cols), None)
    uph_col = next((cols[n] for n in ['기준 UPH', '기준UPH', 'target_uph', 'UPH 기준'] if n in cols), None)
    if process_col is None or uph_col is None:
        return pd.DataFrame(columns=['공정명', '기준 UPH'])

    out = df[[process_col, uph_col]].copy()
    out.columns = ['공정명', '기준 UPH']
    out['공정명'] = out['공정명'].astype(str).str.strip()
    out['기준 UPH'] = pd.to_numeric(out['기준 UPH'], errors='coerce')
    return out.dropna(subset=['공정명']).drop_duplicates(subset=['공정명'])



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def load_master_selector_map() -> pd.DataFrame:
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / 'Master' / 'Master_CMP.csv',
        base_dir / 'master_uph.csv',
        base_dir / 'Master_CMP.csv',
    ]
    target = next((p for p in candidates if p.exists()), None)
    required = ['area_name', 'process_name', 'customer_model', '공정명', '기준 UPH']
    if target is None:
        return pd.DataFrame(columns=required)
    df = pd.read_csv(target, encoding='utf-8-sig')
    cols = {str(c).strip(): c for c in df.columns}
    missing = [c for c in required if c not in cols]
    if missing:
        return pd.DataFrame(columns=required)
    out = df[[cols[c] for c in required]].copy()
    out.columns = required
    for c in ['area_name', 'process_name', 'customer_model', '공정명']:
        out[c] = out[c].astype(str).str.strip()
    out['기준 UPH'] = pd.to_numeric(out['기준 UPH'], errors='coerce')
    return out.dropna(subset=['area_name', 'process_name', 'customer_model', '공정명']).reset_index(drop=True)


def load_mes_db_config(config_path: str = 'setting.ini') -> DbConfig:
    base = load_db_config()
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding='utf-8')
    s = cfg['config'] if 'config' in cfg else {}
    mes_name = s.get('mes_db_name', os.getenv('MES_DB_NAME', DEFAULT_MES_DB_NAME))
    return DbConfig(
        host=base.host,
        port=base.port,
        dbname=mes_name,
        user=base.user,
        password=base.password,
        schema=base.schema,
    )



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_mes_selector_dim(db: DbConfig) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    dim_q = quote_ident(DIM_SELECTOR_TABLE)
    query = f'''    SELECT area_name, process_name, customer_model
    FROM {schema_q}.{dim_q}
    WHERE active_yn = 'Y'
      AND area_name IS NOT NULL
      AND process_name IS NOT NULL
      AND customer_model IS NOT NULL
    ORDER BY area_name, process_name, customer_model;
    '''
    df = read_sql_df(query, db)
    if df.empty:
        return pd.DataFrame(columns=['area_name', 'process_name', 'customer_model'])
    for c in ['area_name', 'process_name', 'customer_model']:
        df[c] = df[c].astype(str).str.strip()
    return df.drop_duplicates().reset_index(drop=True)

def get_itas_process_names_by_selection(master_df: pd.DataFrame, area_name: str, process_name: str, customer_model: str) -> list[str]:
    if master_df.empty:
        return []
    matched = master_df[
        (master_df['area_name'] == str(area_name))
        & (master_df['process_name'] == str(process_name))
        & (master_df['customer_model'] == str(customer_model))
    ]
    return matched['공정명'].dropna().astype(str).drop_duplicates().tolist()


def get_reference_uph_by_selection(master_df: pd.DataFrame, area_name: str, process_name: str, customer_model: str) -> Optional[float]:
    if master_df.empty:
        return None
    matched = master_df[
        (master_df['area_name'] == str(area_name))
        & (master_df['process_name'] == str(process_name))
        & (master_df['customer_model'] == str(customer_model))
    ]
    vals = pd.to_numeric(matched['기준 UPH'], errors='coerce').dropna()
    if vals.empty:
        return None
    return float(vals.sum())


def compute_uph_metrics(uph_day: pd.DataFrame) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    if uph_day is None or uph_day.empty or 'UPH' not in uph_day.columns:
        return None, None, None, None
    series = pd.to_numeric(uph_day['UPH'], errors='coerce').dropna()
    if series.empty:
        return None, None, None, None
    best = float(series.max())
    min_v = float(series.min())
    avg = float(series.mean())
    bw_gap = best - min_v
    deviation = None if best <= 0 else 1.0 - (avg / best)
    return deviation, bw_gap, best, avg


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_itas_latest_date(db: DbConfig):
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    q = f"SELECT MAX(work_date) AS latest_date FROM {schema_q}.{uph_table_q};"
    v = read_sql_df(q, db)['latest_date'].iloc[0]
    return pd.to_datetime(v).normalize() if pd.notna(v) else None


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_mes_latest_date(db: DbConfig):
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)
    q = f"SELECT MAX(work_date) AS latest_date FROM {schema_q}.{table_q};"
    v = read_sql_df(q, db)['latest_date'].iloc[0]
    return pd.to_datetime(v).normalize() if pd.notna(v) else None


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_itas_uph_day_multi(db: DbConfig, process_names: tuple[str, ...], selected_date: pd.Timestamp) -> pd.DataFrame:
    if not process_names:
        return pd.DataFrame(columns=['날짜', '호기', 'UPH'])
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", machine_no AS "호기", SUM(uph) AS "UPH"
    FROM {schema_q}.{uph_table_q}
    WHERE process_name = ANY(%(process_names)s)
      AND work_date = %(work_date)s
    GROUP BY work_date, machine_no
    ORDER BY machine_no;
    """
    df = read_sql_df(query, db, params={'process_names': list(process_names), 'work_date': selected_date.date()})
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH'])


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_itas_uph_machine_trend_multi(db: DbConfig, process_names: tuple[str, ...], machine_no: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    if not process_names:
        return pd.DataFrame(columns=['날짜', '호기', 'UPH'])
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", machine_no AS "호기", SUM(uph) AS "UPH"
    FROM {schema_q}.{uph_table_q}
    WHERE process_name = ANY(%(process_names)s)
      AND machine_no = %(machine_no)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date, machine_no
    ORDER BY work_date;
    """
    df = read_sql_df(query, db, params={
        'process_names': list(process_names),
        'machine_no': machine_no,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    })
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH'])


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_mes_uph_day(db: DbConfig, area_name: str, process_name: str, customer_model: str, selected_date: pd.Timestamp) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", equipment_name AS "호기", SUM(uph) AS "UPH"
    FROM {schema_q}.{table_q}
    WHERE area_name = %(area_name)s
      AND process_name = %(process_name)s
      AND customer_model = %(customer_model)s
      AND work_date = %(work_date)s
    GROUP BY work_date, equipment_name
    ORDER BY equipment_name;
    """
    df = read_sql_df(query, db, params={
        'area_name': area_name,
        'process_name': process_name,
        'customer_model': customer_model,
        'work_date': selected_date.date(),
    })
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH'])


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_mes_uph_machine_trend(db: DbConfig, area_name: str, process_name: str, customer_model: str, machine_no: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", equipment_name AS "호기", SUM(uph) AS "UPH"
    FROM {schema_q}.{table_q}
    WHERE area_name = %(area_name)s
      AND process_name = %(process_name)s
      AND customer_model = %(customer_model)s
      AND equipment_name = %(machine_no)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date, equipment_name
    ORDER BY work_date;
    """
    df = read_sql_df(query, db, params={
        'area_name': area_name,
        'process_name': process_name,
        'customer_model': customer_model,
        'machine_no': machine_no,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    })
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH'])


def get_reference_uph(master_df: pd.DataFrame, process_name: str) -> Optional[float]:
    if master_df.empty or not process_name:
        return None
    matched = master_df.loc[master_df['공정명'] == str(process_name).strip(), '기준 UPH']
    if matched.empty:
        return None
    v = pd.to_numeric(matched.iloc[0], errors='coerce')
    return None if pd.isna(v) else float(v)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_processes_and_latest_date(db: DbConfig):
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    q_processes = f"SELECT DISTINCT process_name FROM {schema_q}.{uph_table_q} WHERE process_name IS NOT NULL ORDER BY process_name;"
    q_latest = f"SELECT MAX(work_date) AS latest_date FROM {schema_q}.{uph_table_q};"
    processes = read_sql_df(q_processes, db)['process_name'].astype(str).tolist()
    latest_date = read_sql_df(q_latest, db)['latest_date'].iloc[0]
    latest_date = pd.to_datetime(latest_date).normalize() if pd.notna(latest_date) else None
    return processes, latest_date


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_uph_day(db: DbConfig, process_name: str, selected_date: pd.Timestamp) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", process_name AS "공정명", machine_no AS "호기", uph AS "UPH"
    FROM {schema_q}.{uph_table_q}
    WHERE process_name = %(process_name)s AND work_date = %(work_date)s
    ORDER BY machine_no;
    """
    df = read_sql_df(query, db, params={'process_name': process_name, 'work_date': selected_date.date()})
    df = ensure_datetime(df, '날짜')
    df = to_numeric_safe(df, ['UPH'])
    dev, bw_gap, _, _ = compute_uph_metrics(df)
    df['UPH 편차율'] = dev
    df['BestWorst Gap'] = bw_gap
    return df


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_uph_trend_sql(db: DbConfig, process_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜",
           AVG(uph) AS "UPH",
           CASE WHEN MAX(uph) > 0 THEN 1 - (AVG(uph) / MAX(uph)) END AS "UPH 편차율",
           (MAX(uph) - MIN(uph)) AS "BestWorst Gap"
    FROM {schema_q}.{uph_table_q}
    WHERE process_name = %(process_name)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date
    ORDER BY work_date;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    })
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH', 'UPH 편차율', 'BestWorst Gap'])


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_uph_machine_trend_sql(db: DbConfig, process_name: str, machine_no: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    SELECT work_date AS "날짜", machine_no AS "호기", uph AS "UPH"
    FROM {schema_q}.{uph_table_q}
    WHERE process_name = %(process_name)s
      AND machine_no = %(machine_no)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY work_date;
    """
    df = read_sql_df(
        query,
        db,
        params={
            'process_name': process_name,
            'machine_no': machine_no,
            'start_date': start_date.date(),
            'end_date': end_date.date(),
        },
    )
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['UPH'])


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_best_worst_machine_sql(db: DbConfig, process_name: str, selected_date: pd.Timestamp):
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    uph_table_q = quote_ident(UPH_TABLE)
    query = f"""
    WITH ranked AS (
        SELECT machine_no, uph,
               ROW_NUMBER() OVER (ORDER BY uph DESC NULLS LAST, machine_no) AS rn_best,
               ROW_NUMBER() OVER (ORDER BY uph ASC NULLS LAST, machine_no) AS rn_worst
        FROM {schema_q}.{uph_table_q}
        WHERE process_name = %(process_name)s AND work_date = %(work_date)s AND uph IS NOT NULL
    )
    SELECT MAX(CASE WHEN rn_best = 1 THEN machine_no END) AS best_machine,
           MAX(CASE WHEN rn_worst = 1 THEN machine_no END) AS worst_machine
    FROM ranked;
    """
    df = read_sql_df(query, db, params={'process_name': process_name, 'work_date': selected_date.date()})
    if df.empty:
        return None, None
    return (
        str(df.iloc[0]['best_machine']) if pd.notna(df.iloc[0]['best_machine']) else None,
        str(df.iloc[0]['worst_machine']) if pd.notna(df.iloc[0]['worst_machine']) else None,
    )


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_best_worst_action_gap_top5_sql(db: DbConfig, process_name: str, selected_date: pd.Timestamp, best_machine: str, worst_machine: str) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'
    query = f"""
    SELECT action_name AS "동작명",
           MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) AS "{best_col}",
           MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) AS "{worst_col}",
           AVG(avg_duration_sec) AS "전체호기 평균",
           ABS(MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END)
             - MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END)) AS "Worst-Best"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
      AND cp_yn = %(cp_yn)s
    GROUP BY action_name
    HAVING AVG(avg_duration_sec) > %(min_avg_duration)s
       AND MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) IS NOT NULL
       AND MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) IS NOT NULL
    ORDER BY "Worst-Best" DESC NULLS LAST
    LIMIT 20;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'work_date': selected_date.date(),
        'best_machine': best_machine,
        'worst_machine': worst_machine,
        'min_avg_duration': MIN_ACTION_AVG_DURATION_SEC,
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    df = to_numeric_safe(df, [best_col, worst_col, '전체호기 평균', 'Worst-Best'])
    df = filter_rows_by_null_count(df, ['동작명'])
    return df.head(5).reset_index(drop=True)



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_best_worst_action_gap_all_sql(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    best_machine: str,
    worst_machine: str,
) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'
    query = f"""
    SELECT action_name AS "동작명",
           MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) AS "{best_col}",
           MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) AS "{worst_col}",
           AVG(avg_duration_sec) AS "전체호기 평균",
           ABS(MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END)
             - MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END)) AS "Worst-Best"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
      AND cp_yn = %(cp_yn)s
    GROUP BY action_name
    HAVING AVG(avg_duration_sec) > %(min_avg_duration)s
       AND MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) IS NOT NULL
       AND MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) IS NOT NULL
    ORDER BY "Worst-Best" DESC NULLS LAST, action_name;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'work_date': selected_date.date(),
        'best_machine': best_machine,
        'worst_machine': worst_machine,
        'min_avg_duration': MIN_ACTION_AVG_DURATION_SEC,
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    df = to_numeric_safe(df, [best_col, worst_col, '전체호기 평균', 'Worst-Best'])
    df = filter_rows_by_null_count(df, ['동작명'])
    return df.reset_index(drop=True)



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_top_metric_action_rows_sql(db: DbConfig, process_name: str, selected_date: pd.Timestamp, metric_expr: str, metric_alias: str, top_n: int = 5) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    metric_col_map = {
        'deviation_rate': 'avg_deviation_rate',
        'bestworst_gap': 'avg_bestworst_gap',
    }
    metric_col = metric_col_map[metric_expr]
    query = f"""
    WITH valid_actions AS (
        SELECT action_name
        FROM {schema_q}.{summary_table_q}
        WHERE process_name = %(process_name)s
          AND work_date = %(work_date)s
          AND cp_yn = %(cp_yn)s
        GROUP BY action_name
        HAVING AVG(avg_duration_sec) > %(min_avg_duration)s
    ),
    top_actions AS (
        SELECT s.action_name, AVG(s.{metric_col}) AS metric_value
        FROM {schema_q}.{summary_table_q} s
        JOIN valid_actions v ON s.action_name = v.action_name
        WHERE s.process_name = %(process_name)s
          AND s.work_date = %(work_date)s
          AND s.cp_yn = %(cp_yn)s
        GROUP BY s.action_name
        ORDER BY metric_value DESC NULLS LAST
        LIMIT {int(top_n)}
    )
    SELECT s.action_name AS "동작명",
           s.machine_no AS "호기",
           AVG(s.avg_duration_sec) AS "소요시간",
           t.metric_value AS "{metric_alias}"
    FROM {schema_q}.{summary_table_q} s
    JOIN top_actions t ON s.action_name = t.action_name
    WHERE s.process_name = %(process_name)s
      AND s.work_date = %(work_date)s
      AND s.cp_yn = %(cp_yn)s
    GROUP BY s.action_name, s.machine_no, t.metric_value
    ORDER BY t.metric_value DESC NULLS LAST, s.action_name, s.machine_no;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'work_date': selected_date.date(),
        'min_avg_duration': MIN_ACTION_AVG_DURATION_SEC,
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    return to_numeric_safe(df, ['소요시간', metric_alias])



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_action_slopes_sql(db: DbConfig, process_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp, ascending: bool, top_n: int = 3) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    order_sql = 'ASC' if ascending else 'DESC'
    limit_n = int(top_n)
    query = f"""
    SELECT machine_no AS "호기",
           action_name AS "동작명",
           REGR_SLOPE(avg_duration_sec, EXTRACT(EPOCH FROM work_date::timestamp) / 86400.0) AS "Slope",
           COUNT(*) AS "데이터포인트"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
      AND cp_yn = %(cp_yn)s
    GROUP BY machine_no, action_name
    HAVING COUNT(*) >= 2
    ORDER BY "Slope" {order_sql} NULLS LAST
    LIMIT {limit_n};
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    return to_numeric_safe(df, ['Slope', '데이터포인트'])



@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_action_line_sql(db: DbConfig, process_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp, machine_no: str, action_name: str) -> pd.DataFrame:
    conn = get_db_connection(db)
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    query = f"""
    SELECT work_date AS "날짜", AVG(avg_duration_sec) AS "소요시간"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
      AND cp_yn = %(cp_yn)s
      AND machine_no = %(machine_no)s
      AND action_name = %(action_name)s
    GROUP BY work_date
    ORDER BY work_date;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'cp_yn': MOTION_CP_FILTER_VALUE,
        'machine_no': machine_no,
        'action_name': action_name,
    })
    df = ensure_datetime(df, '날짜')
    return to_numeric_safe(df, ['소요시간'])



def apply_plot_theme(fig: go.Figure) -> go.Figure:
    """Plotly 그래프 전체 폰트/배경/격자 스타일 통일."""
    fig.update_layout(
        font=dict(family=DASHBOARD_FONT_FAMILY, color='#1F2430'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='white',
    )
    fig.update_xaxes(
        tickfont=dict(family=DASHBOARD_FONT_FAMILY, color='#6B7280'),
        title_font=dict(family=DASHBOARD_FONT_FAMILY, color='#1F2430'),
        gridcolor='#E5E7EB',
        zerolinecolor='#E5E7EB',
    )
    fig.update_yaxes(
        tickfont=dict(family=DASHBOARD_FONT_FAMILY, color='#6B7280'),
        title_font=dict(family=DASHBOARD_FONT_FAMILY, color='#1F2430'),
        gridcolor='#E5E7EB',
        zerolinecolor='#E5E7EB',
    )
    return fig


def get_uph_summary_table(uph_day: pd.DataFrame, reference_uph: Optional[float]) -> pd.DataFrame:
    if uph_day.empty:
        return pd.DataFrame()
    tmp = uph_day[['호기', 'UPH']].copy()
    tmp['호기'] = tmp['호기'].astype(str)
    ordered = natural_machine_sort(tmp['호기'].tolist())
    value_map = tmp.set_index('호기')['UPH'].to_dict()
    rows = {'UPH': {m: value_map.get(m) for m in ordered}}
    if reference_uph is not None:
        rows['기준 UPH'] = {m: reference_uph for m in ordered}
    return pd.DataFrame(rows).T


def plot_uph_summary_bar(uph_day: pd.DataFrame, reference_uph: Optional[float]):
    df = uph_day[['호기', 'UPH']].copy()
    df['호기'] = df['호기'].astype(str)
    ordered = natural_machine_sort(df['호기'].tolist())
    df['호기'] = pd.Categorical(df['호기'], categories=ordered, ordered=True)
    df = df.sort_values('호기')
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df['호기'].astype(str),
            y=df['UPH'],
            customdata=df['호기'].astype(str),
            marker_color=CHART_PRIMARY_COLOR,
            text=df['UPH'].round(UPH_DECIMALS),
            textposition='outside',
            name='UPH',
            hovertemplate='호기: %{customdata}<br>UPH: %{y}<extra></extra>',
        )
    )
    if reference_uph is not None:
        fig.add_hline(
            y=reference_uph,
            line_width=2,
            line_dash='dash',
            line_color=CHART_REFERENCE_COLOR,
            annotation_text=f'기준 UPH: {reference_uph:,.0f}',
            annotation_position='top left',
        )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        template='plotly_white',
        xaxis_title='호기',
        yaxis_title='UPH',
        showlegend=False,
        clickmode='event+select',
    )
    fig.update_yaxes(rangemode='tozero')
    return apply_plot_theme(fig)


def extract_selected_machine(plot_event) -> Optional[str]:
    if plot_event is None:
        return None

    points = []
    if isinstance(plot_event, dict):
        selection = plot_event.get('selection', plot_event)
        if isinstance(selection, dict):
            points = selection.get('points', []) or []
    else:
        selection = getattr(plot_event, 'selection', None)
        if selection is not None:
            points = getattr(selection, 'points', []) or []

    if not points:
        return None

    first_point = points[0]
    if isinstance(first_point, dict):
        custom = first_point.get('customdata')
        if isinstance(custom, (list, tuple)) and custom:
            return str(custom[0])
        if custom is not None:
            return str(custom)
        x_val = first_point.get('x')
        return None if x_val is None else str(x_val)

    custom = getattr(first_point, 'customdata', None)
    if isinstance(custom, (list, tuple)) and custom:
        return str(custom[0])
    if custom is not None:
        return str(custom)
    x_val = getattr(first_point, 'x', None)
    return None if x_val is None else str(x_val)


def get_machine_trend_y_range(df_line: pd.DataFrame, selected_date: pd.Timestamp, reference_uph: Optional[float]) -> Optional[list[float]]:
    if reference_uph is not None and reference_uph > 0:
        base_value = float(reference_uph)
    else:
        base_value = None
        if not df_line.empty:
            tmp = ensure_datetime(df_line, '날짜')
            matched = tmp.loc[tmp['날짜'] == pd.Timestamp(selected_date).normalize(), 'UPH']
            matched = pd.to_numeric(matched, errors='coerce').dropna()
            if not matched.empty:
                base_value = float(matched.iloc[0])
            else:
                uph_series = pd.to_numeric(tmp['UPH'], errors='coerce').dropna()
                if not uph_series.empty:
                    base_value = float(uph_series.iloc[-1])

    if base_value is None or base_value <= 0:
        return None

    lower = base_value * (1 - UPH_MACHINE_TREND_Y_RANGE_RATIO)
    upper = base_value * (1 + UPH_MACHINE_TREND_Y_RANGE_RATIO)

    if lower == upper:
        lower = lower * 0.95
        upper = upper * 1.05

    return [lower, upper]


def plot_uph_machine_trend(df_line: pd.DataFrame, machine_no: str, y_range: Optional[list[float]] = None):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_line['날짜'],
            y=df_line['UPH'],
            mode='lines+markers',
            line=dict(width=3, color=CHART_PRIMARY_COLOR),
            name=machine_no,
        )
    )
    fig.update_layout(
        title=f'{machine_no} UPH Trend',
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title='날짜',
        yaxis_title='UPH',
        template='plotly_white',
        showlegend=False,
    )
    if y_range is not None:
        fig.update_yaxes(range=y_range)
    else:
        fig.update_yaxes(rangemode='tozero')
    return apply_plot_theme(fig)


def plot_empty_machine_trend_box():
    fig = go.Figure()
    fig.update_layout(
        title='호기 UPH Trend',
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
        template='plotly_white',
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    for axis in ['xaxis', 'yaxis']:
        fig['layout'][axis]['showline'] = True
        fig['layout'][axis]['linecolor'] = '#CBD0D6'
        fig['layout'][axis]['mirror'] = True
    return apply_plot_theme(fig)


def build_best_worst_action_gap_with_uph_row(
    bw_table: pd.DataFrame,
    uph_day: pd.DataFrame,
    best_machine: str,
    worst_machine: str,
    action_limit: Optional[int] = 5,
) -> pd.DataFrame:
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'

    if bw_table is not None and not bw_table.empty:
        action_rows = bw_table.copy()
        if action_limit is not None:
            action_rows = action_rows.head(action_limit)
    else:
        action_rows = pd.DataFrame(
            columns=['동작명', best_col, worst_col, '전체호기 평균', 'Worst-Best']
        )

    uph_row = pd.DataFrame(columns=['동작명', best_col, worst_col, '전체호기 평균', 'Worst-Best'])
    if uph_day is not None and not uph_day.empty:
        tmp = uph_day[['호기', 'UPH']].copy()
        tmp['호기'] = tmp['호기'].astype(str)
        tmp['UPH'] = pd.to_numeric(tmp['UPH'], errors='coerce')

        best_uph = tmp.loc[tmp['호기'] == str(best_machine), 'UPH']
        worst_uph = tmp.loc[tmp['호기'] == str(worst_machine), 'UPH']
        best_uph = float(best_uph.iloc[0]) if not best_uph.empty and pd.notna(best_uph.iloc[0]) else None
        worst_uph = float(worst_uph.iloc[0]) if not worst_uph.empty and pd.notna(worst_uph.iloc[0]) else None
        avg_uph = float(tmp['UPH'].mean()) if tmp['UPH'].notna().any() else None
        gap_uph = abs(best_uph - worst_uph) if best_uph is not None and worst_uph is not None else None

        uph_row = pd.DataFrame([{
            '동작명': 'UPH',
            best_col: best_uph,
            worst_col: worst_uph,
            '전체호기 평균': avg_uph,
            'Worst-Best': gap_uph,
        }])

    return pd.concat([uph_row, action_rows], ignore_index=True)


def get_value_centered_y_range(base_value: Optional[float], ratio: float = 0.20) -> Optional[list[float]]:
    if base_value is None:
        return None
    try:
        base_value = float(base_value)
    except Exception:
        return None
    if pd.isna(base_value):
        return None
    if base_value == 0:
        return [-1.0, 1.0]
    lower = base_value * (1 - ratio)
    upper = base_value * (1 + ratio)
    if lower == upper:
        lower = lower * 0.95
        upper = upper * 1.05
    if lower > upper:
        lower, upper = upper, lower
    return [lower, upper]


def plot_empty_bw_trend_box():
    fig = go.Figure()
    fig.update_layout(
        title='Best/Worst 선택 Trend',
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
        template='plotly_white',
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    for axis in ['xaxis', 'yaxis']:
        fig['layout'][axis]['showline'] = True
        fig['layout'][axis]['linecolor'] = '#CBD0D6'
        fig['layout'][axis]['mirror'] = True
    return apply_plot_theme(fig)


def extract_selected_bw_cell(df_event, df_display: pd.DataFrame):
    if df_event is None or df_display is None or df_display.empty:
        return None

    selection = None
    if isinstance(df_event, dict):
        selection = df_event.get('selection', df_event)
    else:
        selection = getattr(df_event, 'selection', None)

    if not selection:
        return None

    rows = []
    columns = []
    cells = []
    if isinstance(selection, dict):
        rows = selection.get('rows', []) or []
        columns = selection.get('columns', []) or []
        cells = selection.get('cells', []) or []
    else:
        rows = getattr(selection, 'rows', []) or []
        columns = getattr(selection, 'columns', []) or []
        cells = getattr(selection, 'cells', []) or []

    row_idx = None
    col_name = None

    if cells:
        first_cell = cells[0]
        if isinstance(first_cell, dict):
            row_idx = first_cell.get('row')
            col_name = first_cell.get('column')
        elif isinstance(first_cell, (list, tuple)) and len(first_cell) >= 2:
            row_idx, col_name = first_cell[0], first_cell[1]
        else:
            row_idx = getattr(first_cell, 'row', None)
            col_name = getattr(first_cell, 'column', None)

    if row_idx is None and rows:
        row_idx = rows[0]
    if col_name is None and columns:
        col_name = columns[0]

    if row_idx is None or col_name is None:
        return None

    try:
        row_idx = int(row_idx)
    except Exception:
        return None

    if row_idx < 0 or row_idx >= len(df_display):
        return None
    if col_name not in df_display.columns:
        return None

    value = df_display.iloc[row_idx][col_name]
    action_name = str(df_display.iloc[row_idx]['동작명']) if '동작명' in df_display.columns else None
    return {'row_idx': row_idx, 'column': col_name, 'value': value, 'action_name': action_name}


def parse_machine_from_bw_column(col_name: str) -> Optional[str]:
    if not col_name:
        return None
    text = str(col_name)
    if text.startswith('Best(') and text.endswith(')'):
        return text[5:-1]
    if text.startswith('Worst(') and text.endswith(')'):
        return text[6:-1]
    return None


def plot_bw_selected_trend(
    bw_selection: dict,
    process_name: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    db: DbConfig,
):
    if not bw_selection:
        return plot_empty_bw_trend_box()

    col_name = bw_selection.get('column')
    action_name = bw_selection.get('action_name')
    selected_value = bw_selection.get('value')
    selected_machine = parse_machine_from_bw_column(col_name)

    # 전체호기 평균 / Gap 컬럼은 특정 호기 트렌드가 아님
    if selected_machine is None or action_name is None:
        return plot_empty_bw_trend_box()

    y_range = get_value_centered_y_range(selected_value, ratio=0.20)

    if action_name == 'UPH':
        line_df = fetch_uph_machine_trend_sql(
            db=db,
            process_name=process_name,
            machine_no=selected_machine,
            start_date=start_date,
            end_date=end_date,
        )
        if line_df.empty:
            return plot_empty_bw_trend_box()
        return plot_uph_machine_trend(line_df, selected_machine, y_range=y_range)

    line_df = fetch_action_line_sql(
        db=db,
        process_name=process_name,
        start_date=start_date,
        end_date=end_date,
        machine_no=selected_machine,
        action_name=action_name,
    )
    if line_df.empty:
        return plot_empty_bw_trend_box()

    title = f'{selected_machine} {action_name}'
    fig = plot_single_action_trend(line_df, title)
    if y_range is not None:
        fig.update_yaxes(range=y_range)
    return apply_plot_theme(fig)


def get_session_cache_dict(name: str) -> dict:
    if name not in st.session_state:
        st.session_state[name] = {}
    return st.session_state[name]


def get_cached_bw_table_all(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    best_machine: str,
    worst_machine: str,
) -> pd.DataFrame:
    cache = get_session_cache_dict('bw_table_all_cache')
    key = (str(process_name), str(pd.Timestamp(selected_date).date()), str(best_machine), str(worst_machine))
    if key not in cache:
        cache[key] = fetch_best_worst_action_gap_all_sql(db, process_name, selected_date, best_machine, worst_machine)
    return cache[key]


def build_top_metric_pivot(rows_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    if rows_df.empty:
        return pd.DataFrame()
    pivot = rows_df.pivot_table(index='동작명', columns='호기', values='소요시간', aggfunc='mean')
    ordered_cols = natural_machine_sort(pivot.columns) if len(pivot.columns) > 0 else []
    pivot = pivot.reindex(columns=ordered_cols).reset_index()
    metric_df = rows_df[['동작명', metric_col]].drop_duplicates().copy()
    merged = pivot.merge(metric_df, on='동작명', how='left')
    machine_cols = [c for c in merged.columns if c not in ['동작명', metric_col]]
    merged = merged[['동작명', metric_col] + machine_cols]
    merged = filter_rows_by_null_count(merged, ['동작명', metric_col])
    return merged.sort_values(metric_col, ascending=False).reset_index(drop=True)


def plot_uph_dual_axis(trend_df: pd.DataFrame):
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(
        go.Scatter(
            x=trend_df['날짜'],
            y=trend_df['UPH'],
            mode='lines+markers',
            name='UPH',
            line=dict(width=3, color=CHART_PRIMARY_COLOR),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=trend_df['날짜'],
            y=trend_df['UPH 편차율'] * 100.0,
            mode='lines+markers',
            name='편차율(%)',
            line=dict(width=3, color=CHART_SECONDARY_COLOR, dash='dot'),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis_title='날짜',
        template='plotly_white',
    )
    fig.update_yaxes(title_text='UPH', secondary_y=False)
    fig.update_yaxes(title_text='편차율(%)', range=[0, UPH_DEVIATION_Y_AXIS_MAX_PERCENT], secondary_y=True)
    return apply_plot_theme(fig)


def plot_single_action_trend(df_line: pd.DataFrame, title: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_line['날짜'],
            y=df_line['소요시간'],
            mode='lines+markers',
            line=dict(width=3),
            name=title,
        )
    )
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title='날짜',
        yaxis_title='소요시간',
        template='plotly_white',
        showlegend=False,
    )
    return apply_plot_theme(fig)

def call_vllm_chat(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 300) -> str:
    """
    OpenAI 호환 vLLM chat completion 호출
    """
    url = f"{VLLM_BASE_URL}/chat/completions"

    payload = {
        "model": VLLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(url, json=payload, timeout=60)

    if not response.ok:
        raise RuntimeError(f"vLLM 요청 실패: status={response.status_code}, body={response.text}")

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def normalize_df_for_llm(
    df: pd.DataFrame,
    max_rows: int = AI_MAX_ROWS,
    is_time_series: bool = False,
    x_col: str | None = None,
) -> dict:
    if df is None or df.empty:
        return {
            "has_data": False,
            "row_count": 0,
            "columns": [],
            "rows": [],
        }

    safe_df = df.copy()

    # is_time_series가 명시된 경우에만 x_col 기준 정렬
    if is_time_series and x_col and x_col in safe_df.columns:
        safe_df[x_col] = pd.to_datetime(safe_df[x_col], errors='coerce')
        safe_df = safe_df.sort_values(by=x_col)

    for c in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[c]):
            safe_df[c] = safe_df[c].dt.strftime('%Y-%m-%d')

    if is_time_series:
        preview_df = safe_df.tail(max_rows).copy()
    else:
        preview_df = safe_df.head(max_rows).copy()

    preview_df = preview_df.where(pd.notna(preview_df), None)

    return {
        "has_data": True,
        "row_count": int(len(df)),
        "columns": [str(c) for c in preview_df.columns],
        "rows": preview_df.to_dict(orient="records"),
    }


def build_ai_payload(
    title: str,
    df: pd.DataFrame,
    data_type: str = "chart",
    x_col: str | None = None,
    y_col: str | None = None,
    is_time_series: bool = False,
) -> dict:
    return {
        "title": title,
        "data_type": data_type,
        "axis_type": "time" if is_time_series else "category",
        "summary": build_generic_series_summary(
            df=df,
            title=title,
            x_col=x_col,
            y_col=y_col,
            is_time_series=is_time_series,
        ),
        "content": normalize_df_for_llm(
            df,
            max_rows=AI_MAX_ROWS,
            is_time_series=is_time_series,
            x_col=x_col,
        ),
    }

def build_generic_series_summary(
    df: pd.DataFrame,
    title: str,
    x_col: str | None = None,
    y_col: str | None = None,
    is_time_series: bool = False,
) -> dict:
    """
    공통 숫자형 summary 생성
    - max_point / min_point
    - avg_y
    - deviation
    - range_gap
    - time series일 때 first/latest/change/half averages/trend_direction 추가
    """
    summary = {
        "chart_title": title,
        "row_count": 0,
        "x_name": x_col,
        "y_name": y_col,
        "max_point": None,
        "min_point": None,
        "avg_y": None,
        "deviation": None,
        "range_gap": None,
    }

    if df is None or df.empty:
        return summary

    summary["row_count"] = int(len(df))

    if not x_col or not y_col:
        return summary

    if x_col not in df.columns or y_col not in df.columns:
        return summary

    work = df[[x_col, y_col]].copy()
    work[y_col] = pd.to_numeric(work[y_col], errors='coerce')
    work = work.dropna(subset=[y_col])

    if work.empty:
        return summary

    max_idx = work[y_col].idxmax()
    min_idx = work[y_col].idxmin()

    max_y = float(work.loc[max_idx, y_col])
    min_y = float(work.loc[min_idx, y_col])
    avg_y = float(work[y_col].mean())
    deviation = None if max_y <= 0 else 1.0 - (avg_y / max_y)

    range_gap = max_y - min_y
    range_gap_ratio = None if avg_y == 0 else range_gap / avg_y
    variation_threshold_ratio = 0.05
    has_meaningful_variation = (
            range_gap_ratio is not None and range_gap_ratio >= variation_threshold_ratio
    )

    if range_gap_ratio is None:
        variation_level = None
    elif range_gap_ratio >= 0.10:
        variation_level = "high"
    elif range_gap_ratio >= 0.05:
        variation_level = "medium"
    else:
        variation_level = "low"

    summary.update({
        "row_count": int(len(work)),
        "max_point": {
            "x": str(work.loc[max_idx, x_col]),
            "y": round(max_y, 4),
        },
        "min_point": {
            "x": str(work.loc[min_idx, x_col]),
            "y": round(min_y, 4),
        },
        "avg_y": round(avg_y, 4),
        "deviation": round(deviation, 6) if deviation is not None else None,
        "range_gap": round(range_gap, 4),
        "range_gap_ratio": round(range_gap_ratio, 6) if range_gap_ratio is not None else None,
        "variation_threshold_ratio": variation_threshold_ratio,
        "has_meaningful_variation": has_meaningful_variation,
        "variation_level": variation_level,
    })

    # 시간축 추가 summary
    if is_time_series:
        try:
            tmp = df[[x_col, y_col]].copy()
            tmp[x_col] = pd.to_datetime(tmp[x_col], errors='coerce')
            tmp[y_col] = pd.to_numeric(tmp[y_col], errors='coerce')
            tmp = tmp.dropna(subset=[x_col, y_col]).sort_values(x_col).reset_index(drop=True)

            if not tmp.empty:
                first_row = tmp.iloc[0]
                latest_row = tmp.iloc[-1]

                first_y = float(first_row[y_col])
                latest_y = float(latest_row[y_col])

                summary["first_point"] = {
                    "x": str(first_row[x_col].date()) if hasattr(first_row[x_col], 'date') else str(first_row[x_col]),
                    "y": round(first_y, 4),
                }
                summary["latest_point"] = {
                    "x": str(latest_row[x_col].date()) if hasattr(latest_row[x_col], 'date') else str(latest_row[x_col]),
                    "y": round(latest_y, 4),
                }

                change_from_first = latest_y - first_y
                change_rate_from_first = None if first_y == 0 else change_from_first / first_y

                summary["change_from_first"] = round(change_from_first, 4)
                summary["change_rate_from_first"] = round(change_rate_from_first, 6) if change_rate_from_first is not None else None

                # 전반/후반 평균 비교
                n = len(tmp)
                if n >= 4:
                    mid = n // 2
                    first_half_avg = float(tmp.iloc[:mid][y_col].mean())
                    second_half_avg = float(tmp.iloc[mid:][y_col].mean())
                    half_avg_diff = second_half_avg - first_half_avg

                    summary["first_half_avg"] = round(first_half_avg, 4)
                    summary["second_half_avg"] = round(second_half_avg, 4)
                    summary["half_avg_diff"] = round(half_avg_diff, 4)

                    base = abs(first_half_avg) if first_half_avg != 0 else 1.0
                    threshold = base * 0.01  # 1%

                    if half_avg_diff > threshold:
                        summary["trend_direction"] = "increase"
                    elif half_avg_diff < -threshold:
                        summary["trend_direction"] = "decrease"
                    else:
                        summary["trend_direction"] = "flat"
        except Exception:
            pass

    return summary

def make_category_analysis_prompt(payload: dict) -> tuple[str, str]:
    system_prompt = """
당신은 제조 데이터 분석가입니다.
반드시 한국어로 답변하세요.
범주형 비교 데이터만 해석하세요.
시간축 개념은 절대 사용하지 마세요.
'최근', '최신', '추세', '상승', '하락', '기간', '전반', '후반' 표현을 사용하면 안 됩니다.
최대/최소/평균/편차는 summary를 우선 사용하세요.
"""

    user_prompt = f"""
다음은 범주형 비교 데이터입니다.

제목:
{payload['title']}

summary:
{json.dumps(payload['summary'], ensure_ascii=False, indent=2)}

data:
{json.dumps(payload['content'], ensure_ascii=False, indent=2)}

형식:
[전체 요약]
- 제목과 데이터 개수 표현
- 최대값, 최소값, 평균, 편차, 차이 표현

[주요 포인트]
- 최대 항목/최소 항목
- 항목 간 차이 수준
- 편차 수준
위 3가지 범위 안에서만 2줄 이내 작성

허용 표현:
- 최대, 최소, 평균, 편차, 차이, 항목 간 편차, 분포, 차이 큼, 차이 작음

금지 표현:
- 최근, 최신, 추세, 상승, 하락, 기간, 전반, 후반, 변화, 감소, 증가

규칙:
1. x값(호기, 설비, 동작명)을 시점으로 해석하지 말 것
2. 시간 관련 해석을 하면 안 됨
3. 평균을 중앙값이라고 바꿔 쓰지 말 것
4. 최대/최소/평균/편차는 summary만 사용
5. summary의 has_meaningful_variation와 variation_level을 편차 판단 기준으로 사용할 것
6. range_gap_ratio가 크다면 원인 분석이 필요하다고 명시 할 것
6. 최대 4줄
"""
    return system_prompt, user_prompt

def make_timeseries_analysis_prompt(payload: dict) -> tuple[str, str]:
    system_prompt = """
당신은 제조 데이터 분석가입니다.
반드시 한국어로 답변하세요.
시계열 데이터의 변화를 해석하세요.
최대/최소/평균/편차는 summary를 우선 사용하세요.
"""

    user_prompt = f"""
다음은 시계열 데이터입니다.

제목:
{payload['title']}

summary:
{json.dumps(payload['summary'], ensure_ascii=False, indent=2)}

data:
{json.dumps(payload['content'], ensure_ascii=False, indent=2)}

형식:
[전체 요약]
- 제목과 데이터 개수 정보 표현
- 최대값, 최소값, 평균, 편차, 차이, 추세 정보 표현

[주요 포인트]
- first_point, latest_point, change_from_first, first_half_avg, second_half_avg, trend_direction 기반으로
  전체 기간 변화와 최근 상태를 2줄 이내로 설명

규칙:
1. first_point와 latest_point를 함께 보고 초기 대비 최근 변화를 설명
2. second_half_avg와 first_half_avg를 비교해 상승/하락/flat 판단
3. 평균을 중앙값이라고 바꿔 쓰지 말 것
4. summary에 없는 값을 임의로 만들지 말 것
5. summary의 variation_level이 high이면 편차가 큰 것으로 해석
6. summary의 variation_level이 medium이면 일정 수준 편차가 있는 것으로 해석
7. summary의 variation_level이 low이면 편차가 크지 않은 것으로 해석
8. 최대 4줄
"""
    return system_prompt, user_prompt

def generate_ai_comment(
    title: str,
    df: pd.DataFrame,
    data_type: str = "chart",
    x_col: str | None = None,
    y_col: str | None = None,
    is_time_series: bool = False,
) -> str:
    payload = build_ai_payload(
        title=title,
        df=df,
        data_type=data_type,
        x_col=x_col,
        y_col=y_col,
        is_time_series=is_time_series,
    )

    if payload.get("axis_type") == "time":
        system_prompt, user_prompt = make_timeseries_analysis_prompt(payload)
    else:
        system_prompt, user_prompt = make_category_analysis_prompt(payload)

    return call_vllm_chat(system_prompt, user_prompt, temperature=0.1, max_tokens=300)

def render_ai_comment_button(
    title: str,
    df: pd.DataFrame,
    key_prefix: str,
    data_type: str = "chart",
    x_col: str | None = None,
    y_col: str | None = None,
    is_time_series: bool = False,
):
    safe_title = re.sub(r'[^0-9a-zA-Z가-힣_]+', '_', str(title))[:40]
    btn_key = f"{key_prefix}_{safe_title}_ai_btn"
    result_key = f"{key_prefix}_{safe_title}_ai_result"

    if result_key not in st.session_state:
        st.session_state[result_key] = None

    if st.button("AI 분석 의견", key=btn_key):
        with st.spinner("AI 분석 생성 중..."):
            try:
                st.session_state[result_key] = generate_ai_comment(
                    title=title,
                    df=df,
                    data_type=data_type,
                    x_col=x_col,
                    y_col=y_col,
                    is_time_series=is_time_series,
                )
            except Exception as e:
                st.session_state[result_key] = f"AI 분석 생성 중 오류 발생: {e}"

    if st.session_state.get(result_key):
        st.info(st.session_state[result_key])

def clear_ai_result_outputs():
    """
    AI 분석 관련 session_state 초기화
    """
    keys_to_delete = [
        k for k in list(st.session_state.keys())
        if (
            k.endswith('_ai_result')
            or k in (
                '_prev_selected_machine',
                '_prev_bw_selection_key',
            )
        )
    ]
    for k in keys_to_delete:
        if k in st.session_state:
            del st.session_state[k]

def clear_ai_result_by_prefix(key_prefix: str):
    """
    특정 key_prefix를 가진 AI 결과만 초기화
    예: uph_machine_trend -> uph_machine_trend_ai_result 삭제
    """
    result_key = f"{key_prefix}_ai_result"
    if result_key in st.session_state:
        del st.session_state[result_key]

def render_page(show_global_title: bool = True):
    render_home_button()
    if show_global_title:
        render_vitals_page_head()
    else:
        st.markdown('## UPH / 동작시간 분석')

    db = load_db_config()
    mes_db = load_mes_db_config()
    master_selector = load_master_selector_map()
    master_uph = load_master_uph()
    mes_selector_dim = fetch_mes_selector_dim(mes_db)

    if mes_selector_dim.empty:
        st.warning('MES 선택용 차원 테이블(dim_mes_selector_map)에 표시할 데이터가 없습니다.')
        st.stop()
    if master_selector.empty:
        st.info('Master_UPH.csv 매핑 데이터가 없어 I-TAS 매핑/기준 UPH는 비활성 상태로 동작합니다.')

    latest_itas = fetch_itas_latest_date(db)
    latest_mes = fetch_mes_latest_date(mes_db)
    latest_candidates = [d for d in [latest_itas, latest_mes] if d is not None]
    latest_date = max(latest_candidates) if latest_candidates else None
    if latest_date is None:
        st.warning('DB에 표시할 데이터가 없습니다.')
        st.stop()

    area_options = sorted(mes_selector_dim['area_name'].dropna().astype(str).unique().tolist())

    c1_1, c1_2,c1_3,c1_4 = st.columns([1,1,1,2])
    with c1_1:
        selected_area = st.selectbox('공장 선택', options=area_options, index=0, key='selected_area')
    with c1_2:
        process_options = sorted(
            mes_selector_dim.loc[
                mes_selector_dim['area_name'] == selected_area,
                'process_name'
            ].dropna().astype(str).unique().tolist()
        )
        selected_process_group = st.selectbox('공정 선택', options=process_options, index=0, key='selected_process_group')
    with c1_3:
        model_options = sorted(
            mes_selector_dim.loc[
                (mes_selector_dim['area_name'] == selected_area) &
                (mes_selector_dim['process_name'] == selected_process_group),
                'customer_model'
            ].dropna().astype(str).unique().tolist()
        )
        selected_model = st.selectbox('모델 선택', options=model_options, index=0, key='selected_model')
    with c1_4:
        st.empty()

    c2_1, c2_2,c2_3,c2_4 = st.columns([1,1,1,2])
    with c2_1:
        date_input = st.date_input('날짜 선택', value=latest_date.to_pydatetime(), help='달력 클릭으로 선택')
    with c2_2:
        selected_date = pd.Timestamp(date_input).normalize()
        lookback_days = st.slider('Trend 분석 기간(일)', min_value=3, max_value=90, value=30, step=1)
    with c2_3:
        st.caption(f'선택 날짜: {selected_date.date()}')
        st.caption(f'선택 공장/공정/모델: {selected_area} / {selected_process_group} / {selected_model}')
    with c2_4:
        st.empty()

    st.checkbox(
        'I-TAS 가능만 보기',
        key=FILTER_CHECKBOX_KEY,
        value=False,
        help='체크 시 I-TAS 데이터가 있는 공장/공정/모델 조합만 선택 목록에 표시합니다.',
    )
    st.markdown('---')

    start_date = selected_date - pd.Timedelta(days=lookback_days - 1)
    mapped_itas_processes = get_itas_process_names_by_selection(master_selector, selected_area, selected_process_group, selected_model)
    print("=============================",mapped_itas_processes)
    selected_process = mapped_itas_processes[0] if mapped_itas_processes else None
    if len(mapped_itas_processes) > 1:
        st.caption(f'참고: UPH 요약의 I-TAS 기준은 매핑된 공정 {len(mapped_itas_processes)}개의 호기별 UPH 합산 기준이며, 나머지 섹션은 대표 공정명 {selected_process} 기준으로 유지합니다.')

    uph_day_itas_summary = fetch_itas_uph_day_multi(db, tuple(mapped_itas_processes), selected_date) if mapped_itas_processes else pd.DataFrame()
    uph_day_mes = fetch_mes_uph_day(mes_db, selected_area, selected_process_group, selected_model, selected_date)
    reference_uph = get_reference_uph_by_selection(master_selector, selected_area, selected_process_group, selected_model)

    selection_key = (
        selected_area,
        selected_process_group,
        selected_model,
        str(selected_date.date()),
        int(lookback_days),
        bool(st.session_state.get(FILTER_CHECKBOX_KEY, False)),
    )
    default_source = 'ITAS' if (mapped_itas_processes and not uph_day_itas_summary.empty) else 'MES'

    prev_selection_key = st.session_state.get('_uph_source_selection_key')

    if prev_selection_key != selection_key:
        clear_ai_result_outputs()
        st.session_state['_uph_source_selection_key'] = selection_key
        st.session_state['uph_source_mode'] = default_source
        st.rerun()

    source_mode = st.session_state.get('uph_source_mode', default_source)

    active_uph_day = uph_day_itas_summary if source_mode == 'ITAS' else uph_day_mes
    if active_uph_day.empty and source_mode == 'ITAS' and not uph_day_mes.empty:
        source_mode = 'MES'
        st.session_state['uph_source_mode'] = 'MES'
        active_uph_day = uph_day_mes

    st.subheader(f'분석 결과 {selected_date.date()} {selected_area} / {selected_process_group} / {selected_model}')

    trend_df = fetch_uph_trend_sql(db, selected_process, start_date, selected_date) if selected_process else pd.DataFrame()
    best_ho, worst_ho = fetch_best_worst_machine_sql(db, selected_process, selected_date) if selected_process else (None, None)
    top_var_rows = fetch_top_metric_action_rows_sql(db, selected_process, selected_date, 'deviation_rate', '편차율', top_n=5) if selected_process else pd.DataFrame()
    top_gap_rows = fetch_top_metric_action_rows_sql(db, selected_process, selected_date, 'bestworst_gap', 'BestWorst Gap', top_n=5) if selected_process else pd.DataFrame()
    top_var_table = build_top_metric_pivot(top_var_rows, '편차율') if not top_var_rows.empty else pd.DataFrame()
    top_gap_table = build_top_metric_pivot(top_gap_rows, 'BestWorst Gap') if not top_gap_rows.empty else pd.DataFrame()
    inc_top3 = fetch_action_slopes_sql(db, selected_process, start_date, selected_date, ascending=False, top_n=3) if selected_process else pd.DataFrame()
    dec_top3 = fetch_action_slopes_sql(db, selected_process, start_date, selected_date, ascending=True, top_n=3) if selected_process else pd.DataFrame()

    title_col, metric_col = st.columns([2, 5])
    with title_col:
        # preview sec-uph 패턴 — left wine bar + h3 (render_sub_head 와 시각 동등).
        from ui.vitals.components import render_sub_head
        render_sub_head(f"1. UPH 요약 ({'I-TAS' if source_mode == 'ITAS' else 'MES'})", "8 KPI")
        dev, bw_gap, _, _ = compute_uph_metrics(active_uph_day)
        ref_text = '-' if reference_uph is None else format_float(reference_uph, UPH_DECIMALS)
        st.markdown(
            f"<div style='text-align:left; padding-top:8px;'><b>편차율:</b> {format_percent(dev, PERCENT_DECIMALS)} "
            f"<b>Best/Worst Gap:</b> {format_float(bw_gap, UPH_DECIMALS)} "
            f"<b>기준 UPH:</b> {ref_text}</div>",
            unsafe_allow_html=True,
        )
    with metric_col:
        st.space(1)
        button_label = 'MES 데이터로 보기' if source_mode == 'ITAS' else 'I-TAS 데이터보기'
        if st.button(button_label, key='uph_source_toggle'):
            st.session_state['uph_source_mode'] = 'MES' if source_mode == 'ITAS' else 'ITAS'
            clear_ai_result_outputs()
            st.rerun()

    if active_uph_day.empty:
        st.info('선택한 조건에 대한 UPH 데이터가 없습니다.')
        tbl = pd.DataFrame()
    else:
        tbl = get_uph_summary_table(active_uph_day, reference_uph)

    fmt_map = {c: f'{{:.{UPH_DECIMALS}f}}' for c in tbl.columns} if not tbl.empty else {}
    st.dataframe(
        tbl.style.format(fmt_map, na_rep='-') if not tbl.empty else tbl,
        use_container_width=True,
        height=130
    )

    render_ai_comment_button(
        title=f"UPH 요약 테이블 ({'I-TAS' if source_mode == 'ITAS' else 'MES'})",
        df=tbl,
        key_prefix="uph_summary_table",
        data_type="table",
    )

    uph_chart_col, uph_trend_col = st.columns([6, 4])

    with uph_chart_col:
        plot_event = st.plotly_chart(
            plot_uph_summary_bar(active_uph_day,
                                 reference_uph) if not active_uph_day.empty else plot_empty_machine_trend_box(),
            use_container_width=True,
            key='uph_summary_bar',
            on_select='rerun',
            selection_mode='points',
        )

        uph_bar_df = (
            active_uph_day[['호기', 'UPH']].copy()
            if not active_uph_day.empty and {'호기', 'UPH'}.issubset(active_uph_day.columns)
            else pd.DataFrame()
        )

        render_ai_comment_button(
            title=f"UPH 요약 Bar Chart ({'I-TAS' if source_mode == 'ITAS' else 'MES'})",
            df=uph_bar_df,
            key_prefix="uph_summary_bar",
            data_type="chart",
            x_col="호기",
            y_col="UPH",
            is_time_series=False,
        )

    selected_machine = extract_selected_machine(plot_event)

    prev_selected_machine = st.session_state.get('_prev_selected_machine')
    if prev_selected_machine != selected_machine:
        clear_ai_result_by_prefix("uph_machine_trend")
        st.session_state['_prev_selected_machine'] = selected_machine

    machine_trend_df = pd.DataFrame()

    with uph_trend_col:
        if selected_machine and not active_uph_day.empty:
            if source_mode == 'ITAS':
                machine_trend_df = fetch_itas_uph_machine_trend_multi(
                    db,
                    tuple(mapped_itas_processes),
                    selected_machine,
                    start_date,
                    selected_date
                )
            else:
                machine_trend_df = fetch_mes_uph_machine_trend(
                    mes_db,
                    selected_area,
                    selected_process_group,
                    selected_model,
                    selected_machine,
                    start_date,
                    selected_date
                )

            if machine_trend_df.empty:
                st.plotly_chart(plot_empty_machine_trend_box(), use_container_width=True)
            else:
                y_range = get_machine_trend_y_range(machine_trend_df, selected_date, reference_uph)
                st.plotly_chart(
                    plot_uph_machine_trend(machine_trend_df, selected_machine, y_range=y_range),
                    use_container_width=True
                )
        else:
            st.plotly_chart(plot_empty_machine_trend_box(), use_container_width=True)

        render_ai_comment_button(
            title=f"{selected_machine} UPH Trend" if selected_machine else "호기 UPH Trend",
            df=machine_trend_df,
            key_prefix="uph_machine_trend",
            data_type="chart",
            x_col="날짜",
            y_col="UPH",
            is_time_series=True,
        )

    st.markdown('---')
    render_sub_head("2. Best Worst 동작차이", "동작별 평균 vs Best/Worst")
    machine_options = natural_machine_sort(uph_day_itas_summary['호기'].astype(str).tolist()) if not uph_day_itas_summary.empty else []
    if selected_process is None or best_ho is None or worst_ho is None or not machine_options:
        st.info('Best/Worst 동작차이 테이블을 계산할 수 없습니다.')
    else:
        default_best = str(best_ho) if str(best_ho) in machine_options else machine_options[0]
        default_worst = str(worst_ho) if str(worst_ho) in machine_options else machine_options[min(1, len(machine_options) - 1)]
        if 'bw_show_all' not in st.session_state:
            st.session_state['bw_show_all'] = False
        bw_table_col, bw_trend_col = st.columns([6, 4])
        with bw_table_col:
            ctrl_col1, ctrl_col2 = st.columns([1, 1])
            with ctrl_col1:
                selected_best_ho = st.selectbox('Best', options=machine_options, index=machine_options.index(default_best), key='bw_manual_best')
            with ctrl_col2:
                selected_worst_ho = st.selectbox('Worst', options=machine_options, index=machine_options.index(default_worst), key='bw_manual_worst')
            st.caption(f'자동선정 Best: {best_ho} / Worst: {worst_ho}')
            bw_table_all = get_cached_bw_table_all(db, selected_process, selected_date, selected_best_ho, selected_worst_ho)
            show_all = st.session_state.get('bw_show_all', False)
            bw_table_display = build_best_worst_action_gap_with_uph_row(bw_table_all, uph_day_itas_summary, selected_best_ho, selected_worst_ho, action_limit=None if show_all else 5)
            best_col = f'Best({selected_best_ho})'
            worst_col = f'Worst({selected_worst_ho})'
            bw_event = st.dataframe(
                bw_table_display.style.format(
                    {
                        best_col: f'{{:.{DURATION_DECIMALS}f}}',
                        worst_col: f'{{:.{DURATION_DECIMALS}f}}',
                        '전체호기 평균': f'{{:.{DURATION_DECIMALS}f}}',
                        'Worst-Best': f'{{:.{GAP_DECIMALS}f}}'
                    },
                    na_rep='-'
                ),
                use_container_width=True,
                height=260,
                key='bw_gap_table',
                on_select='rerun',
                selection_mode='single-cell'
            )

            bw_table_for_ai = bw_table_display.copy()
            if '동작명' in bw_table_for_ai.columns:
                bw_table_for_ai = bw_table_for_ai[bw_table_for_ai['동작명'].astype(str) != 'UPH'].reset_index(drop=True)

            render_ai_comment_button(
                title=f"Best Worst 동작차이 테이블 (UPH 참고행 제외, {selected_best_ho} vs {selected_worst_ho})",
                df=bw_table_for_ai,
                key_prefix="bw_gap_table_ai",
                data_type="table",
                x_col="동작명",
                y_col="Worst-Best",
                is_time_series=False,
            )

            toggle_label = '-' if show_all else '+'
            if st.button(toggle_label, key='bw_toggle_all', help='전체 동작 펼치기/접기'):
                st.session_state['bw_show_all'] = not show_all
                st.rerun()
        with bw_trend_col:
            bw_selection = extract_selected_bw_cell(bw_event, bw_table_display)
            bw_fig = plot_bw_selected_trend(
                bw_selection=bw_selection,
                process_name=selected_process,
                start_date=start_date,
                end_date=selected_date,
                db=db
            )
            st.plotly_chart(bw_fig, use_container_width=True)

            bw_trend_df = pd.DataFrame()
            if bw_selection:
                action_name = bw_selection.get('action_name')
                col_name = bw_selection.get('column')
                selected_machine_bw = parse_machine_from_bw_column(col_name)

                if selected_machine_bw and action_name:
                    if action_name == 'UPH':
                        bw_trend_df = fetch_uph_machine_trend_sql(
                            db=db,
                            process_name=selected_process,
                            machine_no=selected_machine_bw,
                            start_date=start_date,
                            end_date=selected_date,
                        )
                    else:
                        bw_trend_df = fetch_action_line_sql(
                            db=db,
                            process_name=selected_process,
                            start_date=start_date,
                            end_date=selected_date,
                            machine_no=selected_machine_bw,
                            action_name=action_name,
                        )

            bw_y_col = "UPH" if "UPH" in bw_trend_df.columns else ("소요시간" if "소요시간" in bw_trend_df.columns else None)

            render_ai_comment_button(
                title="Best/Worst 선택 Trend",
                df=bw_trend_df,
                key_prefix="bw_selected_trend",
                data_type="chart",
                x_col="날짜" if "날짜" in bw_trend_df.columns else None,
                y_col=bw_y_col,
                is_time_series=True if "날짜" in bw_trend_df.columns else False,
            )

    st.markdown('---')
    render_sub_head("3. UPH / 편차율 Trend", "기간별 추이")
    if trend_df.empty:
        st.info('선택 기간의 Trend 데이터가 없습니다.')
    else:
        st.plotly_chart(plot_uph_dual_axis(trend_df), use_container_width=True)

    render_ai_comment_button(
        title="UPH / 편차율 Trend",
        df=trend_df,
        key_prefix="uph_dual_trend",
        data_type="chart",
        x_col="날짜",
        y_col="UPH",
        is_time_series=True,
    )

    st.markdown('---')
    render_sub_head("4. 주요 편차동작", "이상치 식별")
    var_col, gap_col = st.columns(2)
    with var_col:
        st.markdown('**편차율 상위 5개 동작**')
        if top_var_table.empty:
            st.info('표시할 데이터가 없습니다.')
        else:
            format_map = {'편차율': lambda v: f'{v:.{PERCENT_DECIMALS}f}%' if pd.notna(v) else '-'}
            for c in top_var_table.columns:
                if c not in ['동작명', '편차율']:
                    format_map[c] = f'{{:.{DURATION_DECIMALS}f}}'
            st.dataframe(top_var_table.style.format(format_map, na_rep='-'), use_container_width=True, height=260)

        render_ai_comment_button(
            title="편차율 상위 5개 동작",
            df=top_var_table,
            key_prefix="top_var_table",
            data_type="table",
            x_col="동작명",
            y_col="편차율",
            is_time_series=False,
        )
    with gap_col:
        st.markdown('**Best Worst Gap 상위 5개 동작**')
        if top_gap_table.empty:
            st.info('표시할 데이터가 없습니다.')
        else:
            format_map = {'BestWorst Gap': f'{{:.{GAP_DECIMALS}f}}'}
            for c in top_gap_table.columns:
                if c not in ['동작명', 'BestWorst Gap']:
                    format_map[c] = f'{{:.{DURATION_DECIMALS}f}}'
            st.dataframe(top_gap_table.style.format(format_map, na_rep='-'), use_container_width=True, height=260)

        render_ai_comment_button(
            title="Best Worst Gap 상위 5개 동작",
            df=top_gap_table,
            key_prefix="top_gap_table",
            data_type="table",
            x_col="동작명",
            y_col="BestWorst Gap",
            is_time_series=False,
        )

    st.markdown('---')
    render_sub_head("5. 동작시간이 증가 추세인 동작", "악화 신호")
    if inc_top3.empty:
        st.info('증가 추세를 계산할 수 있는 데이터가 부족합니다.')
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(inc_top3.iterrows()):
            line_df = fetch_action_line_sql(
                db,
                selected_process,
                start_date,
                selected_date,
                row['호기'],
                row['동작명']
            )
            title = f"{row['호기']} {row['동작명']}<br><sup>Slope: {row['Slope']:.4f}/day</sup>"
            display_title = f"{row['호기']} {row['동작명']} 증가 추세"

            with cols[i]:
                st.plotly_chart(plot_single_action_trend(line_df, title), use_container_width=True)

                render_ai_comment_button(
                    title=display_title,
                    df=line_df,
                    key_prefix=f"inc_trend_{i}",
                    data_type="chart",
                    x_col="날짜",
                    y_col="소요시간",
                    is_time_series=True,
                )

    st.markdown('---')
    render_sub_head("6. 동작시간이 하락 추세인 동작", "개선 신호")
    if dec_top3.empty:
        st.info('하락 추세를 계산할 수 있는 데이터가 부족합니다.')
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(dec_top3.iterrows()):
            line_df = fetch_action_line_sql(
                db,
                selected_process,
                start_date,
                selected_date,
                row['호기'],
                row['동작명']
            )
            title = f"{row['호기']} {row['동작명']}<br><sup>Slope: {row['Slope']:.4f}/day</sup>"
            display_title = f"{row['호기']} {row['동작명']} 하락 추세"

            with cols[i]:
                st.plotly_chart(plot_single_action_trend(line_df, title), use_container_width=True)

                render_ai_comment_button(
                    title=display_title,
                    df=line_df,
                    key_prefix=f"dec_trend_{i}",
                    data_type="chart",
                    x_col="날짜",
                    y_col="소요시간",
                    is_time_series=True,
                )

def main():
    configure_page()
    inject_vitals_theme()
    render_page(show_global_title=True)




# =========================
# Patch: I-TAS 가능만 보기 + Worst-Best 부호 유지 정렬
# =========================
_ORIG_RENDER_PAGE = render_page
_ORIG_FETCH_MES_SELECTOR_DIM = fetch_mes_selector_dim
FILTER_CHECKBOX_KEY = 'itas_only_master_selector'


def _get_master_selector_keys() -> pd.DataFrame:
    master_selector = load_master_selector_map()
    if master_selector is None or master_selector.empty:
        return pd.DataFrame(columns=['area_name', 'process_name', 'customer_model'])
    cols = ['area_name', 'process_name', 'customer_model']
    missing = [c for c in cols if c not in master_selector.columns]
    if missing:
        return pd.DataFrame(columns=cols)
    keys = master_selector[cols].copy()
    for c in cols:
        keys[c] = keys[c].astype(str).str.strip()
    return keys.drop_duplicates().reset_index(drop=True)


def fetch_mes_selector_dim(db: DbConfig) -> pd.DataFrame:
    df = _ORIG_FETCH_MES_SELECTOR_DIM(db)
    if df is None or df.empty:
        return df
    if not st.session_state.get(FILTER_CHECKBOX_KEY, False):
        return df
    keys = _get_master_selector_keys()
    if keys.empty:
        return df.iloc[0:0].copy()
    work = df.copy()
    for c in ['area_name', 'process_name', 'customer_model']:
        work[c] = work[c].astype(str).str.strip()
    filtered = work.merge(keys, on=['area_name', 'process_name', 'customer_model'], how='inner')
    return filtered.drop_duplicates().reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_best_worst_action_gap_top5_sql(db: DbConfig, process_name: str, selected_date: pd.Timestamp, best_machine: str, worst_machine: str) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'
    query = f"""
    SELECT action_name AS "동작명",
           MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) AS "{best_col}",
           MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) AS "{worst_col}",
           AVG(avg_duration_sec) AS "전체호기 평균",
           (MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END)
             - MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END)) AS "Worst-Best"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
      AND cp_yn = %(cp_yn)s
    GROUP BY action_name
    HAVING AVG(avg_duration_sec) > %(min_avg_duration)s
       AND MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) IS NOT NULL
       AND MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) IS NOT NULL
    ORDER BY "Worst-Best" DESC NULLS LAST, action_name
    LIMIT 20;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'work_date': selected_date.date(),
        'best_machine': best_machine,
        'worst_machine': worst_machine,
        'min_avg_duration': MIN_ACTION_AVG_DURATION_SEC,
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    df = to_numeric_safe(df, [best_col, worst_col, '전체호기 평균', 'Worst-Best'])
    df = filter_rows_by_null_count(df, ['동작명'])
    return df.head(5).reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SEC)
def fetch_best_worst_action_gap_all_sql(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    best_machine: str,
    worst_machine: str,
) -> pd.DataFrame:
    schema_q = quote_ident(db.schema)
    summary_table_q = quote_ident(SUMMARY_TABLE)
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'
    query = f"""
    SELECT action_name AS "동작명",
           MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) AS "{best_col}",
           MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) AS "{worst_col}",
           AVG(avg_duration_sec) AS "전체호기 평균",
           (MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END)
             - MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END)) AS "Worst-Best"
    FROM {schema_q}.{summary_table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
      AND cp_yn = %(cp_yn)s
    GROUP BY action_name
    HAVING AVG(avg_duration_sec) > %(min_avg_duration)s
       AND MAX(CASE WHEN machine_no = %(best_machine)s THEN avg_duration_sec END) IS NOT NULL
       AND MAX(CASE WHEN machine_no = %(worst_machine)s THEN avg_duration_sec END) IS NOT NULL
    ORDER BY "Worst-Best" DESC NULLS LAST, action_name;
    """
    df = read_sql_df(query, db, params={
        'process_name': process_name,
        'work_date': selected_date.date(),
        'best_machine': best_machine,
        'worst_machine': worst_machine,
        'min_avg_duration': MIN_ACTION_AVG_DURATION_SEC,
        'cp_yn': MOTION_CP_FILTER_VALUE,
    })
    df = to_numeric_safe(df, [best_col, worst_col, '전체호기 평균', 'Worst-Best'])
    df = filter_rows_by_null_count(df, ['동작명'])
    return df.reset_index(drop=True)


def build_best_worst_action_gap_with_uph_row(
    bw_table: pd.DataFrame,
    uph_day: pd.DataFrame,
    best_machine: str,
    worst_machine: str,
    action_limit: Optional[int] = 5,
) -> pd.DataFrame:
    best_col = f'Best({best_machine})'
    worst_col = f'Worst({worst_machine})'
    gap_col = 'Worst-Best'

    if bw_table is not None and not bw_table.empty:
        action_rows = bw_table.copy()
        if gap_col in action_rows.columns:
            action_rows = action_rows.sort_values(gap_col, ascending=False, na_position='last').reset_index(drop=True)
        if action_limit is not None:
            action_rows = action_rows.head(action_limit)
    else:
        action_rows = pd.DataFrame(columns=['동작명', best_col, worst_col, '전체호기 평균', gap_col])

    uph_row = pd.DataFrame(columns=['동작명', best_col, worst_col, '전체호기 평균', gap_col])
    if uph_day is not None and not uph_day.empty:
        tmp = uph_day[['호기', 'UPH']].copy()
        tmp['호기'] = tmp['호기'].astype(str)
        tmp['UPH'] = pd.to_numeric(tmp['UPH'], errors='coerce')

        best_uph = tmp.loc[tmp['호기'] == str(best_machine), 'UPH']
        worst_uph = tmp.loc[tmp['호기'] == str(worst_machine), 'UPH']
        best_uph = float(best_uph.iloc[0]) if not best_uph.empty and pd.notna(best_uph.iloc[0]) else None
        worst_uph = float(worst_uph.iloc[0]) if not worst_uph.empty and pd.notna(worst_uph.iloc[0]) else None
        avg_uph = float(tmp['UPH'].mean()) if tmp['UPH'].notna().any() else None
        # UPH 행은 정렬 고정 + Best-Worst 값 유지
        gap_uph = (best_uph - worst_uph) if best_uph is not None and worst_uph is not None else None

        uph_row = pd.DataFrame([{
            '동작명': 'UPH',
            best_col: best_uph,
            worst_col: worst_uph,
            '전체호기 평균': avg_uph,
            gap_col: gap_uph,
        }])

    return pd.concat([uph_row, action_rows], ignore_index=True)


def render_page(show_global_title: bool = True):
    # 체크박스는 원본 render_page 내부(모델 선택 바로 아래)에 배치되도록 변경
    _ORIG_RENDER_PAGE(show_global_title=show_global_title)

def main():
    configure_page()
    inject_vitals_theme()
    render_page(show_global_title=True)


if __name__ == '__main__':
    main()
