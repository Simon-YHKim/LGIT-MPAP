# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import hashlib
import json
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text

from auth_guard import require_login

# Streamlit 기본 페이지 설정: 좌측 메뉴는 접은 상태로 시작하고, 실제 숨김은 CSS에서 처리합니다.
#st.set_page_config(
#    page_title="CMP 달성률 Dashboard",
#    layout="wide",
#    initial_sidebar_state="collapsed",
#)
require_login(
    page_name="CMP_dashboard",
    page_path="pages/1_CMP_Dashboard.py"
)


try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False
    AgGrid = GridOptionsBuilder = GridUpdateMode = DataReturnMode = JsCode = None

from db import get_engine

st.set_page_config(page_title='MTBA Detail View', layout='wide')

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

from ui.analytics import inject_tracker
inject_tracker(page_name="4_MTBA_Detail_View", page_path="pages/4_MTBA_Detail_View.py")

engine = get_engine()

ALLOWED_MODELS = ['R53A', 'R53B', 'R50', 'R63A', 'R63B', 'R70']
MASTER_MV = 'mtba.mv_detail_page_daily_master'
FALLBACK_MV = 'mtba.mv_detail_page_daily'
DIM_EQUIPMENT = 'mtba.dim_equipment'
COMMENT_TABLE = 'mtba.alarm_comment_history'
WHITELIST_TABLE = 'mtba.alarm_whitelist'

# Vitals 팔레트 정렬 — legacy 상수명 보존, 값만 통일
PRIMARY            = '#A50034'  # Vitals primary
PRIMARY_2          = '#7E0027'  # Vitals primary-dark
BG                 = '#F7F8FA'  # Vitals page-bg
CARD               = '#FFFFFF'  # Vitals card-bg
ROSE               = '#F8E5EC'  # Vitals primary-tint
MIST               = '#F1F3F5'  # Vitals soft
BORDER             = '#E5E7EB'  # Vitals border
TEXT               = '#1F2430'  # Vitals ink-body
SUB                = '#6B7280'  # Vitals ink-muted
PASTEL_RED         = '#FDECEF'  # Vitals bad-tint
PASTEL_RED_STRONG  = '#FDECEF'  # Vitals bad-tint (이전 off-token #FDECEF → 정식 토큰)
PASTEL_YELLOW      = '#FAF1DD'  # Vitals warn-tint
PASTEL_GREEN       = '#E6F4EA'  # Vitals good-tint

st.markdown(f"""
<style>
/* Vitals 토큰 — apply_vitals_theme 의 root 변수에 fallback 으로 결합.
   하드코딩된 f-string hex 와 var() 를 함께 두어, 테마 변경 시 var() 우선 적용. */
.block-container {{padding-top: 1rem; padding-bottom: 2rem;}}
.main {{background: linear-gradient(180deg, var(--page-bg, #FFFFFF) 0%, var(--page-bg, {BG}) 100%);}}
.soft-card {{
    background: var(--card-bg, rgba(255,255,255,.92));
    border: 1px solid var(--border, {BORDER});
    border-radius: 0;
    padding: 14px 18px;
    box-shadow: 0 10px 24px rgba(109,16,40,.05);
    color: var(--ink-body, {TEXT});
}}
.section-title {{color:var(--primary, {PRIMARY}); font-weight:800; font-size:1.15rem;}}
.panel-title {{color:var(--primary, {PRIMARY}); font-weight:800; font-size:1.05rem; margin-bottom: .2rem;}}
.helper {{color:var(--ink-muted, {SUB}); font-size:.9rem;}}
.filter-wrap {{
    background: var(--card-bg, rgba(255,255,255,.9));
    border: 1px solid var(--border, {BORDER});
    border-radius: 0;
    padding: 14px 16px;
    margin-top: 10px;
}}
.legend-wrap {{display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 6px 0;}}
.legend-chip {{border:1px solid var(--border, {BORDER}); border-radius:999px; padding:6px 10px; font-size:.82rem; background:var(--card-bg, white);}}
.legend-red    {{background:var(--status-bad-tint,  {PASTEL_RED});}}
.legend-yellow {{background:var(--status-warn-tint, {PASTEL_YELLOW});}}
.legend-green  {{background:var(--status-good-tint, {PASTEL_GREEN});}}
.legend-prod   {{background:{PASTEL_RED_STRONG};}}
.badge-chip {{display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid var(--border, {BORDER}); background:var(--primary-tint, {ROSE}); color:var(--primary, {PRIMARY}); font-size:.8rem; font-weight:700;}}
div.stButton > button {{border-radius: 0!important; border:1px solid var(--border, {BORDER}) !important;}}
div.stButton > button[kind="primary"] {{background:var(--primary, {PRIMARY}) !important; color:white !important;}}
.popup-meta {{border:1px solid var(--border, {BORDER}); border-radius:0; padding:12px 14px; background:var(--card-bg, #fff); margin-bottom:10px;}}
.popup-title {{color:var(--primary, {PRIMARY}); font-weight:800; font-size:1.05rem; margin-bottom:4px;}}
.popup-sub {{color:{SUB}; font-size:.9rem; line-height:1.5;}}
.page-hero {{
    background: linear-gradient(135deg, {PRIMARY_2} 0%, {PRIMARY} 100%);
    border-radius: 0;
    padding: 40px 28px 24px 28px;
    box-shadow: 0 10px 24px rgba(109,16,40,.18);
    margin: 0 0 14px 0;
    overflow: visible;
}}


.page-hero-title {{
    color: #FFFFFF;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 8px;
}}

.page-hero-sub {{
    color: #FFFFFF;
    font-size: .95rem;
    line-height: 1.5;
}}


div[data-testid="stTextInput"] input {{
    border-radius: 0!important;
    border: 1px solid #F8E5EC !important;
    background: #FFFFFF !important;
    color: #A50034 !important;
    font-weight: 700 !important;
    min-height: 42px !important;
    padding-left: 14px !important;
}}

.query-panel-title {{
    color: #A50034;
    font-size: 1.05rem;
    font-weight: 800;
    line-height: 1.3;
    margin: 8px 0 10px 4px;
}}

.panel-edit-wrap {{
    margin-bottom: 8px;
}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def round_int(v, default=0):
    try:
        if pd.isna(v):
            return default
        return int(Decimal(str(float(v))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except Exception:
        return default


def round_rate(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(Decimal(str(float(v))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))
    except Exception:
        return default


def fmt_int(v):
    return f"{round_int(v):,}"


def fmt_rate(v):
    return f"{round_rate(v):.1f}"


def safe_float(v, default=0.0):
    try:
        return default if pd.isna(v) else float(v)
    except Exception:
        return default


def to_py_date(v, fallback=None):
    if v is None:
        return fallback
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        ts = pd.to_datetime(v, errors='coerce')
        return ts.date() if not pd.isna(ts) else fallback
    except Exception:
        return fallback


def parse_relation_name(full_name: str):
    return tuple(full_name.split('.', 1)) if '.' in full_name else ('public', full_name)


def build_date_cols(start_d, end_d):
    if start_d is None or end_d is None:
        return []
    return [d.date() for d in pd.date_range(start=start_d, end=end_d, freq='D')][::-1]


def get_default_this_week_range(min_date, max_date):
    today = pd.Timestamp.today().date()
    end = min(today, max_date)
    monday = end - timedelta(days=end.weekday())
    return max(min_date, monday), end


def parse_int_text(value, default=0):
    s = str(value).strip().replace(',', '')
    if s == '':
        return default
    if re.fullmatch(r'\d+', s):
        return int(s)
    return default


def int_text_input(label: str, key: str, default: int):
    if key not in st.session_state:
        st.session_state[key] = str(default)
    raw = st.text_input(label, key=key)
    return parse_int_text(raw, default)


def make_query_signature(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def popup_key_standard(equipment_id, base_date):
    return f"{equipment_id}|{base_date}"


def popup_key_fol(segment_name, process_name, base_date):
    return f"{segment_name}|{process_name}|{base_date}"


def render_heatmap_legend():
    st.markdown(
        """
        <div class='legend-wrap'>
            <div class='legend-chip legend-red'>0 ~ 60 미만</div>
            <div class='legend-chip legend-yellow'>60 ~ 120 미만</div>
            <div class='legend-chip legend-green'>120 이상</div>
            <div class='legend-chip legend-prod'>Target 미만 생산수량</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# State
# ---------------------------------------------------------
def ensure_state():
    panels = st.session_state.get('detail_panels')
    valid = isinstance(panels, list) and len(panels) > 0 and all(isinstance(p, dict) and 'id' in p for p in panels)
    if not valid:
        st.session_state.detail_panels = [{'id': 1, 'query': None, 'sig': None}]
    defaults = {
        'detail_next_panel_id': max((int(p.get('id', 0)) for p in st.session_state.detail_panels), default=1) + 1,
        'detail_popup_request': {},
        'detail_popup_suppressed': {},
        'detail_last_grid_click': {},
        'detail_selected_row': {},
        'detail_grid_nonce': {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_detail_page_state():
    for key in list(st.session_state.keys()):
        if key.startswith('detail_') or key.startswith('mode_') or key.startswith('fol_checkbox_'):
            st.session_state.pop(key, None)
    st.session_state.detail_panels = [{'id': 1, 'query': None, 'sig': None}]
    st.session_state.detail_next_panel_id = 2
    st.session_state.detail_popup_request = {}
    st.session_state.detail_popup_suppressed = {}
    st.session_state.detail_last_grid_click = {}
    st.session_state.detail_selected_row = {}
    st.session_state.detail_grid_nonce = {}


def clear_panel_popup(panel_id: int):
    panel_key = str(panel_id)
    st.session_state.detail_popup_request.pop(panel_key, None)
    st.session_state.detail_popup_suppressed.pop(panel_key, None)
    st.session_state.detail_last_grid_click.pop(panel_key, None)
    st.session_state.detail_selected_row.pop(panel_key, None)
    st.session_state.detail_grid_nonce[panel_key] = int(st.session_state.detail_grid_nonce.get(panel_key, 0)) + 1
    for k in list(st.session_state.keys()):
        if k.startswith(f'comment_alarm_select_{panel_id}') or k.startswith(f'comment_text_{panel_id}'):
            st.session_state.pop(k, None)


def clear_panel_query(panel_id: int):
    for p in st.session_state.detail_panels:
        if int(p['id']) == int(panel_id):
            p['query'] = None
            p['sig'] = None
            break
    clear_panel_popup(panel_id)


def save_panel_query(panel_id: int, query: dict):
    sig = make_query_signature(query)
    for p in st.session_state.detail_panels:
        if int(p['id']) == int(panel_id):
            p['query'] = query
            p['sig'] = sig
            break
    clear_panel_popup(panel_id)


def insert_panel_after(current_panel_id: int):
    panels = st.session_state.detail_panels[:]
    idx = 0
    for i, p in enumerate(panels):
        if int(p['id']) == int(current_panel_id):
            idx = i
            break
    new_id = int(st.session_state.detail_next_panel_id)
    st.session_state.detail_next_panel_id = new_id + 1
    panels.insert(idx + 1, {'id': new_id, 'query': None, 'sig': None})
    st.session_state.detail_panels = panels


def remove_panel(panel_id: int):
    if len(st.session_state.detail_panels) <= 1:
        return
    st.session_state.detail_panels = [p for p in st.session_state.detail_panels if int(p['id']) != int(panel_id)]
    clear_panel_popup(panel_id)


def request_panel_popup(panel_id: int, popup_key: str):
    if popup_key:
        st.session_state.detail_popup_request[str(panel_id)] = popup_key


def consume_panel_popup_request(panel_id: int):
    return st.session_state.detail_popup_request.pop(str(panel_id), None)


def suppress_popup_once(panel_id: int, popup_key: str | None):
    if popup_key:
        st.session_state.detail_popup_suppressed[str(panel_id)] = popup_key


def get_suppressed_popup(panel_id: int):
    return st.session_state.detail_popup_suppressed.get(str(panel_id))

# ---------------------------------------------------------
# DB helpers
# ---------------------------------------------------------
def relation_exists(full_name: str) -> bool:
    df = pd.read_sql(text('SELECT to_regclass(:name) AS regname'), engine, params={'name': full_name})
    return (not df.empty) and (df.loc[0, 'regname'] is not None)


@st.cache_data(ttl=300, show_spinner=False)
def resolve_source_view():
    sql = text('SELECT to_regclass(:name) AS regname')
    for mv_name in [MASTER_MV, FALLBACK_MV]:
        df = pd.read_sql(sql, engine, params={'name': mv_name})
        if not df.empty and df.loc[0, 'regname'] is not None:
            return mv_name
    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_relation_columns(full_name):
    schema_name, rel_name = parse_relation_name(full_name)
    sql = text('SELECT column_name FROM information_schema.columns WHERE table_schema=:schema_name AND table_name=:rel_name ORDER BY ordinal_position')
    df = pd.read_sql(sql, engine, params={'schema_name': schema_name, 'rel_name': rel_name})
    return set(df['column_name'].dropna().astype(str).tolist()) if not df.empty else set()


@st.cache_data(ttl=300, show_spinner=False)
def get_alarm_whitelist_names():
    if not relation_exists(WHITELIST_TABLE):
        return set()
    cols = get_relation_columns(WHITELIST_TABLE)
    if 'alarm_name' not in cols:
        return set()
    df = pd.read_sql(text(f"SELECT DISTINCT TRIM(alarm_name) AS alarm_name FROM {WHITELIST_TABLE} WHERE alarm_name IS NOT NULL"), engine)
    return set(df['alarm_name'].dropna().astype(str).str.strip().tolist()) if not df.empty else set()


def apply_whitelist_filter(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    whitelist = get_alarm_whitelist_names()
    if not whitelist:
        return df
    work = df.copy()
    work['alarm_name'] = work['alarm_name'].astype(str).str.strip()
    return work[work['alarm_name'].isin(whitelist)].copy()


@st.cache_data(ttl=300, show_spinner=False)
def get_date_range_for_view(source_view):
    df = pd.read_sql(text(f'SELECT MIN(base_date) AS min_d, MAX(base_date) AS max_d FROM {source_view}'), engine)
    return (to_py_date(df.loc[0, 'min_d']), to_py_date(df.loc[0, 'max_d'])) if not df.empty else (None, None)


@st.cache_data(ttl=300, show_spinner=False)
def get_models_for_view(source_view):
    df = pd.read_sql(text(f'SELECT DISTINCT model_name FROM {source_view} WHERE model_name IS NOT NULL ORDER BY model_name'), engine)
    models = df['model_name'].dropna().astype(str).tolist() if not df.empty else []
    return [m for m in models if m in ALLOWED_MODELS]


@st.cache_data(ttl=300, show_spinner=False)
def get_processes_for_view(source_view, model_name, start_d, end_d):
    sql = text(f'SELECT DISTINCT process_name FROM {source_view} WHERE model_name=:m AND base_date BETWEEN :s AND :e AND process_name IS NOT NULL ORDER BY process_name')
    df = pd.read_sql(sql, engine, params={'m': model_name, 's': start_d, 'e': end_d})
    return df['process_name'].dropna().astype(str).tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def get_processes_all_for_view(source_view, model_name):
    sql = text(f'SELECT DISTINCT process_name FROM {source_view} WHERE model_name=:m AND process_name IS NOT NULL ORDER BY process_name')
    df = pd.read_sql(sql, engine, params={'m': model_name})
    return df['process_name'].dropna().astype(str).tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def load_detail_base(source_view, model_name, process_name, start_d, end_d):
    cols = get_relation_columns(source_view)
    alarm_code_expr = 'alarm_code' if 'alarm_code' in cols else 'NULL::text AS alarm_code'
    runtime_col = next((c for c in ['runtime_minutes', 'runtime', 'daily_runtime_minutes', 'daily_runtime'] if c in cols), None)
    runtime_expr = f'{runtime_col} AS runtime_minutes' if runtime_col else 'NULL::numeric AS runtime_minutes'
    sql = text(
        f"SELECT base_date, process_name, model_name, equipment_id, equipment_name, equipment_no, {alarm_code_expr}, alarm_name, alarm_count, output_qty, daily_mtba, {runtime_expr} "
        f"FROM {source_view} "
        "WHERE model_name=:m AND process_name=:p AND base_date BETWEEN :s AND :e AND alarm_name IS NOT NULL "
        "ORDER BY base_date DESC, equipment_no, alarm_name"
    )
    df = pd.read_sql(sql, engine, params={'m': model_name, 'p': process_name, 's': start_d, 'e': end_d})
    if df.empty:
        return df
    df['base_date'] = pd.to_datetime(df['base_date'], errors='coerce').dt.date
    for c in ['alarm_count', 'output_qty', 'daily_mtba', 'runtime_minutes']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df['alarm_name'] = df['alarm_name'].astype(str).str.strip()
    df = apply_whitelist_filter(df)
    if df.empty:
        return df
    eq_mtba = (
        df.groupby(['equipment_id', 'equipment_no', 'equipment_name'], dropna=False)['daily_mtba']
        .mean().reset_index().rename(columns={'daily_mtba': 'mtba'})
    )
    return df.merge(eq_mtba[['equipment_id', 'mtba']], on='equipment_id', how='left')


@st.cache_data(ttl=300, show_spinner=False)
def load_fol_inline_base(source_view, model_name, target_date):
    cols = get_relation_columns(source_view)
    alarm_code_expr = 'v.alarm_code' if 'alarm_code' in cols else 'NULL::text AS alarm_code'
    runtime_col = next((c for c in ['runtime_minutes', 'runtime', 'daily_runtime_minutes', 'daily_runtime'] if c in cols), None)
    runtime_expr = f'v.{runtime_col} AS runtime_minutes' if runtime_col else 'NULL::numeric AS runtime_minutes'
    sql = text(
        f"SELECT v.base_date, v.process_name, v.model_name, v.equipment_id, v.equipment_name, v.equipment_no, de.segment_name AS equipment_segment_name, {alarm_code_expr}, v.alarm_name, v.alarm_count, v.output_qty, v.daily_mtba, {runtime_expr} "
        f"FROM {source_view} v LEFT JOIN {DIM_EQUIPMENT} de ON v.equipment_id = de.equipment_id "
        "WHERE v.model_name=:m AND v.base_date=:d "
        "ORDER BY v.process_name, equipment_segment_name, v.equipment_no, v.alarm_name"
    )
    df = pd.read_sql(sql, engine, params={'m': model_name, 'd': target_date})
    if df.empty:
        return df
    df['base_date'] = pd.to_datetime(df['base_date'], errors='coerce').dt.date
    df['equipment_segment_name'] = df['equipment_segment_name'].fillna('').astype(str).str.strip()
    for c in ['alarm_count', 'output_qty', 'daily_mtba', 'runtime_minutes']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df['alarm_name'] = df['alarm_name'].astype(str).str.strip()
    return apply_whitelist_filter(df)

# ---------------------------------------------------------
# Comment history
# ---------------------------------------------------------
def ensure_alarm_comment_history_table():
    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS mtba;
    CREATE TABLE IF NOT EXISTS {COMMENT_TABLE} (
        id BIGSERIAL PRIMARY KEY,
        popup_scope TEXT NOT NULL DEFAULT 'standard',
        equipment_id BIGINT NULL,
        segment_name TEXT NULL,
        base_date DATE NOT NULL,
        alarm_code TEXT,
        alarm_name TEXT NOT NULL,
        model_name TEXT,
        process_name TEXT,
        equipment_name TEXT,
        equipment_no TEXT,
        comment_text TEXT NOT NULL,
        created_by TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with engine.begin() as conn:
        for stmt in [s.strip() for s in ddl.split(';') if s.strip()]:
            conn.execute(text(stmt))


def insert_alarm_comment(payload: dict):
    sql = text(f"""
        INSERT INTO {COMMENT_TABLE}
        (
            popup_scope, equipment_id, segment_name, base_date,
            alarm_code, alarm_name, model_name, process_name,
            equipment_name, equipment_no, comment_text, created_by
        ) VALUES (
            :popup_scope, :equipment_id, :segment_name, :base_date,
            :alarm_code, :alarm_name, :model_name, :process_name,
            :equipment_name, :equipment_no, :comment_text, :created_by
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql, payload)


def load_alarm_comment_history(popup_payload: dict, alarm_name: str, alarm_code: str | None = None, limit: int = 100):
    popup_scope = str(popup_payload.get('popup_scope', 'standard'))
    params = {'popup_scope': popup_scope, 'base_date': popup_payload.get('base_date'), 'alarm_name': alarm_name, 'alarm_code': alarm_code, 'limit': int(limit)}
    where_sql = ['popup_scope = :popup_scope', 'base_date = :base_date', 'alarm_name = :alarm_name']
    if popup_scope == 'fol':
        where_sql += ["COALESCE(segment_name,'') = COALESCE(:segment_name,'')", "COALESCE(process_name,'') = COALESCE(:process_name,'')"]
        params['segment_name'] = popup_payload.get('segment_name')
        params['process_name'] = popup_payload.get('process_name')
    else:
        where_sql += ["COALESCE(equipment_id,-1) = COALESCE(:equipment_id,-1)"]
        params['equipment_id'] = popup_payload.get('equipment_id')
    if alarm_code:
        where_sql += ["COALESCE(alarm_code,'') = COALESCE(:alarm_code,'')"]
    sql = text(f"""
        SELECT id, created_at, COALESCE(created_by,'-') AS created_by, alarm_code, alarm_name, comment_text
        FROM {COMMENT_TABLE}
        WHERE {' AND '.join(where_sql)}
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
    """)
    return pd.read_sql(sql, engine, params=params)


def add_comment_section_to_popup(popup_payload: dict, panel_id: int):
    rows = popup_payload.get('rows', []) or []
    if not rows:
        st.info('Comment를 남길 알람 정보가 없습니다.')
        return
    alarm_options, option_map = [], {}
    for r in rows:
        code = str(r.get('alarm_code') or '').strip()
        name = str(r.get('alarm_name') or '').strip()
        label = f"[{code}] {name}" if code else name
        if label not in option_map:
            alarm_options.append(label)
            option_map[label] = {'alarm_code': code, 'alarm_name': name}
    st.markdown('### Comment 입력 / 이력')
    selected_label = st.selectbox('알람 선택', alarm_options, key=f'comment_alarm_select_{panel_id}')
    selected_alarm = option_map[selected_label]
    latest_df = load_alarm_comment_history(popup_payload, selected_alarm['alarm_name'], selected_alarm['alarm_code'], limit=1)
    default_text = '' if latest_df.empty else str(latest_df.iloc[0]['comment_text'])
    text_key = f'comment_text_{panel_id}_{selected_alarm["alarm_name"]}'
    if text_key not in st.session_state:
        st.session_state[text_key] = default_text
    st.text_area('Comment', key=text_key, height=140, placeholder='알람 원인, 조치 내용, 재발 방지 대책 등을 입력하세요.')
    c1, c2 = st.columns([1,3])
    with c1:
        save_clicked = st.button('Comment 저장', key=f'comment_save_{panel_id}', type='primary', use_container_width=True)
    with c2:
        st.caption('저장 시 수정이 아니라 이력으로 누적됩니다.')
    if save_clicked:
        text_value = (st.session_state.get(text_key) or '').strip()
        if not text_value:
            st.warning('저장할 Comment 내용을 입력해 주세요.')
        else:
            payload = {
                'popup_scope': popup_payload.get('popup_scope', 'standard'),
                'equipment_id': popup_payload.get('equipment_id'),
                'segment_name': popup_payload.get('segment_name'),
                'base_date': popup_payload.get('base_date'),
                'alarm_code': selected_alarm['alarm_code'] or None,
                'alarm_name': selected_alarm['alarm_name'],
                'model_name': popup_payload.get('model_name'),
                'process_name': popup_payload.get('process_name'),
                'equipment_name': popup_payload.get('equipment_name'),
                'equipment_no': popup_payload.get('equipment_no'),
                'comment_text': text_value,
                'created_by': st.session_state.get('user_name', None),
            }
            insert_alarm_comment(payload)
            st.success('Comment가 저장되었습니다.')
            st.rerun()
    hist_df = load_alarm_comment_history(popup_payload, selected_alarm['alarm_name'], selected_alarm['alarm_code'], limit=100)
    st.markdown('#### Comment 이력')
    if hist_df.empty:
        st.info('저장된 Comment 이력이 없습니다.')
    else:
        hist_df = hist_df.copy()
        hist_df['created_at'] = pd.to_datetime(hist_df['created_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        hist_df = hist_df.rename(columns={'created_at': '저장일시', 'created_by': '작성자', 'alarm_code': '알람코드', 'alarm_name': '알람명', 'comment_text': 'Comment'})
        st.dataframe(hist_df[['저장일시', '작성자', '알람코드', '알람명', 'Comment']], use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# Builders
# ---------------------------------------------------------
def filter_inline_segments(df):
    if df.empty:
        return df
    return df[df['equipment_segment_name'].astype(str).str.contains(r'inline|in-line|fol', case=False, regex=True, na=False)].copy()


def build_fol_inline_segment_options(df):
    if df.empty:
        return []
    vals = sorted(df['equipment_segment_name'].dropna().astype(str).str.strip().unique().tolist())
    return [x for x in vals if x and re.search(r'inline|in-line|fol', x, flags=re.I)]


def build_production_maps(base_df):
    if base_df.empty:
        return {}, {}
    prod_daily = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['output_qty'].max().reset_index()
    prod_daily_map = {(r['equipment_id'], r['base_date']): safe_float(r['output_qty']) for _, r in prod_daily.iterrows()}
    eq_total_prod = prod_daily.groupby('equipment_id', dropna=False)['output_qty'].sum().reset_index()
    eq_total_prod_map = {r['equipment_id']: safe_float(r['output_qty']) for _, r in eq_total_prod.iterrows()}
    return prod_daily_map, eq_total_prod_map


def build_daily_mtba_map(base_df):
    if base_df.empty:
        return {}
    mtba_daily = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['daily_mtba'].max().reset_index()
    return {(r['equipment_id'], r['base_date']): safe_float(r['daily_mtba']) for _, r in mtba_daily.iterrows()}


def build_process_mtba_stats(base_df):
    empty = {'mtba_avg': 0.0, 'mtba_min': 0.0, 'mtba_max': 0.0, 'mtba_std': 0.0}
    if base_df.empty or 'mtba' not in base_df.columns:
        return empty
    s = pd.to_numeric(base_df[['equipment_id', 'mtba']].drop_duplicates()['mtba'], errors='coerce').dropna()
    if s.empty:
        return empty
    return {'mtba_avg': float(s.mean()), 'mtba_min': float(s.min()), 'mtba_max': float(s.max()), 'mtba_std': float(s.std(ddof=0))}


def build_popup_maps(base_df):
    if base_df.empty:
        return {}
    prod_daily_map, _ = build_production_maps(base_df)
    day_total_alarm = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['alarm_count'].sum().reset_index().rename(columns={'alarm_count': 'total_alarm_count'})
    day_runtime = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['runtime_minutes'].max().reset_index() if 'runtime_minutes' in base_df.columns else pd.DataFrame(columns=['equipment_id', 'base_date', 'runtime_minutes'])
    day_mtba = base_df.groupby(['equipment_id', 'base_date'], dropna=False)['daily_mtba'].max().reset_index().rename(columns={'daily_mtba': 'daily_mtba_max'})
    day_info = base_df.groupby(['equipment_id', 'base_date'], dropna=False).agg(equipment_name=('equipment_name', 'first'), equipment_no=('equipment_no', 'first'), model_name=('model_name', 'first'), process_name=('process_name', 'first')).reset_index()
    day_info = day_total_alarm.merge(day_runtime, on=['equipment_id','base_date'], how='left').merge(day_mtba, on=['equipment_id','base_date'], how='left').merge(day_info, on=['equipment_id','base_date'], how='left')
    day_alarm = base_df.groupby(['equipment_id', 'base_date', 'alarm_code', 'alarm_name'], dropna=False)['alarm_count'].sum().reset_index().rename(columns={'alarm_count': 'alarm_count_sum'})
    popup_map = {}
    for _, info in day_info.iterrows():
        eq_id = info['equipment_id']
        base_date = info['base_date']
        total_alarm = safe_float(info.get('total_alarm_count'))
        runtime_min = safe_float(info.get('runtime_minutes'))
        if runtime_min <= 0 and total_alarm > 0:
            runtime_min = safe_float(info.get('daily_mtba_max')) * total_alarm
        output_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))
        sub = day_alarm[(day_alarm['equipment_id'] == eq_id) & (day_alarm['base_date'] == base_date)].copy().sort_values(['alarm_count_sum', 'alarm_name'], ascending=[False, True]).head(5)
        rows = []
        for idx, arow in enumerate(sub.itertuples(index=False), start=1):
            cnt = safe_float(getattr(arow, 'alarm_count_sum'))
            rows.append({'rank': idx, 'alarm_name': str(getattr(arow, 'alarm_name')), 'alarm_code': str(getattr(arow, 'alarm_code')) if pd.notna(getattr(arow, 'alarm_code')) else '', 'alarm_count': round_int(cnt), 'alarm_rate_pct': round_rate(0 if output_qty <= 0 else (cnt / output_qty) * 100.0), 'share_pct': round_rate(0 if total_alarm <= 0 else (cnt / total_alarm) * 100.0)})
        popup_map[popup_key_standard(eq_id, base_date)] = {'popup_scope': 'standard', 'equipment_id': int(eq_id) if pd.notna(eq_id) else None, 'segment_name': None, 'base_date': base_date, 'model_name': info.get('model_name'), 'process_name': info.get('process_name'), 'equipment_name': info.get('equipment_name'), 'equipment_no': info.get('equipment_no'), 'title': str(info.get('equipment_name') or info.get('equipment_no') or '-'), 'runtime_min': round_int(runtime_min), 'output_qty': round_int(output_qty), 'total_alarm_count': round_int(total_alarm), 'rows': rows}
    return popup_map


def filter_by_mtba(base_df, mtba_worst, mtba_limit, only_below):
    if base_df.empty:
        return base_df, pd.DataFrame()
    eq_mtba = base_df[['equipment_id', 'equipment_no', 'equipment_name', 'mtba']].drop_duplicates().copy()
    eq_mtba['mtba_sort'] = pd.to_numeric(eq_mtba['mtba'], errors='coerce').fillna(999999)
    if mtba_worst > 0:
        worst_ids = eq_mtba.sort_values(['mtba_sort', 'equipment_no'], ascending=[True, True]).head(mtba_worst)['equipment_id'].tolist()
        eq_mtba = eq_mtba[eq_mtba['equipment_id'].isin(worst_ids)].copy()
        base_df = base_df[base_df['equipment_id'].isin(worst_ids)].copy()
    if only_below:
        valid_ids = eq_mtba[eq_mtba['mtba_sort'] <= float(mtba_limit)]['equipment_id'].tolist()
        eq_mtba = eq_mtba[eq_mtba['equipment_id'].isin(valid_ids)].copy()
        base_df = base_df[base_df['equipment_id'].isin(valid_ids)].copy()
    return base_df, eq_mtba


def build_alarm_priority_rows(base_df, top_n, result_metric, selected_end_date, process_mtba_stats):
    if base_df.empty:
        return []
    prod_daily_map, eq_total_prod_map = build_production_maps(base_df)
    mtba_daily_map = build_daily_mtba_map(base_df)
    top_alarm_df = base_df.groupby('alarm_name', as_index=False)['alarm_count'].sum().rename(columns={'alarm_count': 'total_alarm_count'}).sort_values(['total_alarm_count', 'alarm_name'], ascending=[False, True]).head(top_n).reset_index(drop=True)
    rows = []
    for idx, alarm_name in enumerate(top_alarm_df['alarm_name'].tolist(), start=1):
        sub = base_df[base_df['alarm_name'] == alarm_name].copy()
        if sub.empty:
            continue
        eq_summary = sub.groupby(['equipment_id', 'equipment_no', 'equipment_name', 'mtba'], dropna=False).agg(total_alarm_count=('alarm_count', 'sum')).reset_index().sort_values(['total_alarm_count', 'equipment_no'], ascending=[False, True])
        for _, eq in eq_summary.iterrows():
            eq_id = eq['equipment_id']
            sub_eq = sub[sub['equipment_id'] == eq_id].copy()
            eq_dates = sorted(pd.Series(sub_eq['base_date'].dropna().unique()).tolist())
            day_alarm_agg = sub_eq.groupby('base_date', as_index=False).agg(alarm_count=('alarm_count', 'sum'))
            day_map, popup_key_map = {}, {}
            for base_date in eq_dates:
                match = day_alarm_agg[day_alarm_agg['base_date'] == base_date]
                alarm_cnt = safe_float(match['alarm_count'].iloc[0], 0.0) if not match.empty else 0.0
                prod_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))
                day_mtba = safe_float(mtba_daily_map.get((eq_id, base_date), 0.0))
                if result_metric == '알람율':
                    val = round_rate(0 if prod_qty <= 0 else (alarm_cnt / prod_qty) * 100.0)
                elif result_metric == '알람수':
                    val = round_int(alarm_cnt)
                elif result_metric == 'MTBA':
                    val = round_int(day_mtba)
                elif result_metric == '생산수량':
                    val = round_int(prod_qty)
                else:
                    val = round_int(alarm_cnt)
                day_map[base_date] = val
                popup_key_map[base_date] = popup_key_standard(eq_id, base_date)
            rows.append({'process_name': sub_eq['process_name'].iloc[0], 'group_label': f'Worst{idx}', 'alarm_name': alarm_name, 'equipment_id': eq_id, 'equipment_no': str(eq['equipment_no']), 'equipment_name': str(eq['equipment_name']), 'mtba': round_int(eq.get('mtba')), 'mtba_avg': round_int(process_mtba_stats.get('mtba_avg')), 'mtba_min': round_int(process_mtba_stats.get('mtba_min')), 'mtba_max': round_int(process_mtba_stats.get('mtba_max')), 'mtba_std': round_int(process_mtba_stats.get('mtba_std')), 'alarm_count_total': round_int(eq['total_alarm_count']), 'output_qty_total': round_int(eq_total_prod_map.get(eq_id, 0.0)), 'output_qty_latest': round_int(prod_daily_map.get((eq_id, selected_end_date), 0.0)), 'daily_map': day_map, 'popup_key_map': popup_key_map})
    return rows


def build_equipment_priority_rows(base_df, top_n, result_metric, selected_end_date, process_mtba_stats):
    if base_df.empty:
        return []
    prod_daily_map, eq_total_prod_map = build_production_maps(base_df)
    mtba_daily_map = build_daily_mtba_map(base_df)
    eq_summary = base_df.groupby(['equipment_id', 'equipment_no', 'equipment_name', 'mtba'], dropna=False).agg(total_alarm_count=('alarm_count', 'sum')).reset_index().sort_values(['total_alarm_count', 'equipment_no'], ascending=[False, True])
    rows = []
    for _, eq in eq_summary.iterrows():
        eq_id = eq['equipment_id']
        sub_eq = base_df[base_df['equipment_id'] == eq_id].copy()
        if sub_eq.empty:
            continue
        top_alarm_df = sub_eq.groupby('alarm_name', as_index=False)['alarm_count'].sum().rename(columns={'alarm_count': 'total_alarm_count'}).sort_values(['total_alarm_count', 'alarm_name'], ascending=[False, True]).head(top_n).reset_index(drop=True)
        eq_dates = sorted(pd.Series(sub_eq['base_date'].dropna().unique()).tolist())
        for idx, arow in top_alarm_df.iterrows():
            alarm_name = arow['alarm_name']
            sub_alarm = sub_eq[sub_eq['alarm_name'] == alarm_name].copy()
            day_alarm_agg = sub_alarm.groupby('base_date', as_index=False).agg(alarm_count=('alarm_count', 'sum'))
            day_map, popup_key_map = {}, {}
            for base_date in eq_dates:
                match = day_alarm_agg[day_alarm_agg['base_date'] == base_date]
                alarm_cnt = safe_float(match['alarm_count'].iloc[0], 0.0) if not match.empty else 0.0
                prod_qty = safe_float(prod_daily_map.get((eq_id, base_date), 0.0))
                day_mtba = safe_float(mtba_daily_map.get((eq_id, base_date), 0.0))
                if result_metric == '알람율':
                    val = round_rate(0 if prod_qty <= 0 else (alarm_cnt / prod_qty) * 100.0)
                elif result_metric == '알람수':
                    val = round_int(alarm_cnt)
                elif result_metric == 'MTBA':
                    val = round_int(day_mtba)
                elif result_metric == '생산수량':
                    val = round_int(prod_qty)
                else:
                    val = round_int(alarm_cnt)
                day_map[base_date] = val
                popup_key_map[base_date] = popup_key_standard(eq_id, base_date)
            rows.append({'process_name': sub_eq['process_name'].iloc[0], 'equipment_id': eq_id, 'equipment_no': str(eq['equipment_no']), 'equipment_name': str(eq['equipment_name']), 'mtba': round_int(eq.get('mtba')), 'mtba_avg': round_int(process_mtba_stats.get('mtba_avg')), 'mtba_min': round_int(process_mtba_stats.get('mtba_min')), 'mtba_max': round_int(process_mtba_stats.get('mtba_max')), 'mtba_std': round_int(process_mtba_stats.get('mtba_std')), 'group_label': f'Worst{idx+1}', 'alarm_name': str(alarm_name), 'alarm_count_total': round_int(arow['total_alarm_count']), 'output_qty_total': round_int(eq_total_prod_map.get(eq_id, 0.0)), 'output_qty_latest': round_int(prod_daily_map.get((eq_id, selected_end_date), 0.0)), 'daily_map': day_map, 'popup_key_map': popup_key_map})
    return rows


def build_grid_dataframe(rows, date_cols, view_priority):
    out_rows = []
    last_proc = last_eq = last_group = None
    for row in rows:
        proc = row['process_name']
        eq = row['equipment_no']
        grp = row['group_label']
        show_proc = proc if proc != last_proc else ''
        show_eq = eq if (view_priority == '설비 호기' and eq != last_eq) else (eq if view_priority != '설비 호기' else '')
        show_grp = grp if grp != last_group or proc != last_proc or (view_priority == '설비 호기' and eq != last_eq) else ''
        base = {'공정명': show_proc, '구분': show_grp, '알람명': row['alarm_name'], '호기': show_eq if view_priority == '설비 호기' else row['equipment_no'], 'MTBA': round_int(row.get('mtba')), '알람수': round_int(row['alarm_count_total']), '생산수량': round_int(row.get('output_qty_latest')), 'MTBA Avg': round_int(row.get('mtba_avg')), 'MTBA Min': round_int(row.get('mtba_min')), 'MTBA Max': round_int(row.get('mtba_max')), 'MTBA Std': round_int(row.get('mtba_std'))}
        if view_priority != '설비 호기':
            base['호기'] = row['equipment_no']
        for d in date_cols:
            label = pd.to_datetime(d).strftime('%Y-%m-%d')
            base[f'd_{label}'] = row['daily_map'].get(d, 0)
            base[f'pk_{label}'] = row.get('popup_key_map', {}).get(d, '')
        out_rows.append(base)
        last_proc, last_eq, last_group = proc, eq, grp
    return pd.DataFrame(out_rows)


def build_standard_bundle(query, source_view):
    base_df = load_detail_base(source_view, query['model_name'], query['process_name'], query['start_date'], query['end_date'])
    if base_df.empty:
        return {'base_df': base_df, 'rows': [], 'date_cols': build_date_cols(query['start_date'], query['end_date']), 'popup_map': {}}
    stats = build_process_mtba_stats(base_df)
    filtered_df, _ = filter_by_mtba(base_df, query['mtba_worst'], query['mtba_limit'], query['only_below'])
    popup_map = build_popup_maps(filtered_df)
    rows = build_alarm_priority_rows(filtered_df, query['alarm_worst'], query['result_metric'], query['end_date'], stats) if query['view_priority'] == '알람명' else build_equipment_priority_rows(filtered_df, query['alarm_worst'], query['result_metric'], query['end_date'], stats)
    return {'base_df': filtered_df, 'rows': rows, 'date_cols': build_date_cols(query['start_date'], query['end_date']), 'popup_map': popup_map}


def build_fol_inline_bundle(base_df, model_name, target_date, selected_segments, prod_process, result_metric, mtba_limit, only_below):
    df = filter_inline_segments(base_df)
    if selected_segments:
        df = df[df['equipment_segment_name'].isin(selected_segments)].copy()
    if df.empty:
        return {'grid_df': pd.DataFrame(), 'popup_map': {}, 'process_cols': []}
    proc_agg = df.groupby(['equipment_segment_name', 'process_name'], dropna=False).agg(metric_mtba=('daily_mtba', 'mean'), metric_prod_qty=('output_qty', 'sum'), runtime_minutes=('runtime_minutes', 'sum'), total_alarm_count=('alarm_count', 'sum')).reset_index()
    if only_below:
        seg_mtba = proc_agg.groupby('equipment_segment_name', dropna=False)['metric_mtba'].mean().reset_index()
        keep = seg_mtba[seg_mtba['metric_mtba'] <= float(mtba_limit)]['equipment_segment_name'].tolist()
        proc_agg = proc_agg[proc_agg['equipment_segment_name'].isin(keep)].copy()
        df = df[df['equipment_segment_name'].isin(keep)].copy()
    if proc_agg.empty:
        return {'grid_df': pd.DataFrame(), 'popup_map': {}, 'process_cols': []}
    process_cols = sorted(proc_agg['process_name'].dropna().astype(str).unique().tolist())
    if not prod_process or prod_process not in process_cols:
        prod_process = process_cols[0] if process_cols else None
    popup_map = {}
    group_alarm = df.groupby(['equipment_segment_name', 'process_name', 'alarm_code', 'alarm_name'], dropna=False)['alarm_count'].sum().reset_index().rename(columns={'alarm_count': 'alarm_count_sum'})
    for _, info in proc_agg.iterrows():
        seg = str(info['equipment_segment_name'])
        proc = str(info['process_name'])
        total_alarm = safe_float(info['total_alarm_count'])
        output_qty = safe_float(info['metric_prod_qty'])
        sub = group_alarm[(group_alarm['equipment_segment_name'] == seg) & (group_alarm['process_name'] == proc)].copy().sort_values(['alarm_count_sum', 'alarm_name'], ascending=[False, True]).head(5)
        rows = []
        for i, arow in enumerate(sub.itertuples(index=False), start=1):
            cnt = safe_float(getattr(arow, 'alarm_count_sum'))
            rows.append({'rank': i, 'alarm_name': str(getattr(arow, 'alarm_name')), 'alarm_code': str(getattr(arow, 'alarm_code')) if pd.notna(getattr(arow, 'alarm_code')) else '', 'alarm_count': round_int(cnt), 'alarm_rate_pct': round_rate(0 if output_qty <= 0 else (cnt / output_qty) * 100.0), 'share_pct': round_rate(0 if total_alarm <= 0 else (cnt / total_alarm) * 100.0)})
        popup_map[popup_key_fol(seg, proc, target_date)] = {'popup_scope': 'fol', 'equipment_id': None, 'segment_name': seg, 'base_date': target_date, 'model_name': model_name, 'process_name': proc, 'equipment_name': None, 'equipment_no': None, 'title': f'{seg} / {proc}', 'runtime_min': round_int(info.get('runtime_minutes')), 'output_qty': round_int(output_qty), 'total_alarm_count': round_int(total_alarm), 'rows': rows}
    rows = []
    for seg in sorted(proc_agg['equipment_segment_name'].dropna().astype(str).unique().tolist()):
        sub = proc_agg[proc_agg['equipment_segment_name'] == seg].copy()
        row = {'모델명': model_name, '설비세그먼트명': seg, result_metric: 0, '생산수량': 0}
        metric_vals = []
        selected_proc_qty = 0.0
        for proc in process_cols:
            match = sub[sub['process_name'] == proc]
            metric_val = 0.0
            prod_qty = 0.0
            if not match.empty:
                metric_val = safe_float(match['metric_mtba'].iloc[0]) if result_metric == 'MTBA' else safe_float(match['metric_prod_qty'].iloc[0])
                prod_qty = safe_float(match['metric_prod_qty'].iloc[0])
            row[f'p_{proc}'] = round_int(metric_val)
            row[f'pk_{proc}'] = popup_key_fol(seg, proc, target_date)
            metric_vals.append(metric_val)
            if prod_process == proc:
                selected_proc_qty = prod_qty
        total_val = float(pd.Series(metric_vals, dtype='float64').mean()) if result_metric == 'MTBA' and metric_vals else (sum(metric_vals) if metric_vals else 0.0)
        row[result_metric] = round_int(total_val)
        row['생산수량'] = round_int(selected_proc_qty)
        rows.append(row)
    return {'grid_df': pd.DataFrame(rows), 'popup_map': popup_map, 'process_cols': process_cols}

# ---------------------------------------------------------
# Grid rendering
# ---------------------------------------------------------
def _grid_update_mode():
    if not AGGRID_AVAILABLE:
        return None
    try:
        return ['cellClicked', 'cellDoubleClicked', 'cellValueChanged', 'selectionChanged', 'modelUpdated']
    except Exception:
        try:
            return GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED
        except Exception:
            return GridUpdateMode.SELECTION_CHANGED


def value_formatter_int():
    return JsCode("function(params){ const v=Number(params.value); return isNaN(v)?(params.value ?? ''):Math.round(v).toString(); }") if AGGRID_AVAILABLE else None


def value_formatter_rate():
    return JsCode("function(params){ const v=Number(params.value); return isNaN(v)?(params.value ?? ''):v.toFixed(1); }") if AGGRID_AVAILABLE else None


def mtba_cell_style():
    return JsCode(f"function(params){{ const v=Number(params.value); if(isNaN(v)) return {{borderRight:'1px solid {BORDER}'}}; if(v<60) return {{backgroundColor:'{PASTEL_RED}',borderRight:'1px solid {BORDER}'}}; if(v<120) return {{backgroundColor:'{PASTEL_YELLOW}',borderRight:'1px solid {BORDER}'}}; return {{backgroundColor:'{PASTEL_GREEN}',borderRight:'1px solid {BORDER}'}}; }}") if AGGRID_AVAILABLE else None


def qty_cell_style(target_qty: float):
    return JsCode(f"function(params){{ const v=Number(params.value); if(isNaN(v)) return {{borderRight:'1px solid {BORDER}'}}; if(v<{float(target_qty):.6f}) return {{backgroundColor:'{PASTEL_RED_STRONG}',borderRight:'1px solid {BORDER}'}}; return {{borderRight:'1px solid {BORDER}'}}; }}") if AGGRID_AVAILABLE else None


def default_cell_style():
    return JsCode(f"function(params){{ return {{borderRight:'1px solid {BORDER}'}}; }}") if AGGRID_AVAILABLE else None


def build_common_grid_css_dict():
    return {
        '.ag-root-wrapper': {'border': f'1px solid {BORDER} !important', 'border-radius': '0 !important', 'overflow': 'hidden !important'},
        '.ag-header': {'background': f'linear-gradient(180deg, {ROSE}, #FFFFFF) !important'},
        '.ag-header-cell': {'font-weight': '800 !important', 'color': f'{PRIMARY} !important', 'justify-content': 'center !important', 'text-align': 'center !important', 'border-right': f'1px solid {BORDER} !important'},
        '.ag-cell': {'font-size': '12px !important', 'display': 'flex !important', 'align-items': 'center !important', 'justify-content': 'center !important', 'color': f'{TEXT} !important', 'border-right': f'1px solid {BORDER} !important'},
        '.ag-row': {'border-bottom': '1px solid #F8E5EC !important'},
        '.ag-row-hover': {'background-color': '#F8E5EC !important'},
    }


def _resp_current_rows(resp, fallback_df: pd.DataFrame):
    data = None if resp is None else resp.get('data')
    if data is None:
        return fallback_df.reset_index(drop=True).to_dict('records')
    if isinstance(data, pd.DataFrame):
        return data.reset_index(drop=True).to_dict('records')
    if isinstance(data, list):
        return data
    try:
        return pd.DataFrame(data).reset_index(drop=True).to_dict('records')
    except Exception:
        return fallback_df.reset_index(drop=True).to_dict('records')


def _resolve_clicked_popup_key(resp, grid_df: pd.DataFrame):
    if resp is None:
        return None, None, None
    rows = _resp_current_rows(resp, grid_df)
    for row in rows:
        if not isinstance(row, dict):
            continue
        marker = str(row.get('__popup_click__') or '').strip()
        if not marker:
            continue
        popup_key = marker.split('||', 1)[0].strip()
        if popup_key:
            return popup_key, row, marker
    return None, None, None


def _aggrid(work_df: pd.DataFrame, grid_options: dict, key: str, height: int):
    ag_kwargs = dict(gridOptions=grid_options, key=key, allow_unsafe_jscode=True, data_return_mode=DataReturnMode.AS_INPUT, fit_columns_on_grid_load=False, theme='streamlit', height=height, reload_data=False, custom_css=build_common_grid_css_dict())
    update_mode = _grid_update_mode()
    try:
        return AgGrid(work_df, update_on=update_mode, **ag_kwargs)
    except TypeError:
        return AgGrid(work_df, update_mode=update_mode, **ag_kwargs)


def render_standard_grid(grid_df, date_cols, panel_id, result_metric, target_qty, show_stats, view_priority='알람명'):
    if grid_df.empty:
        st.info('조회 조건에 해당하는 데이터가 없습니다.')
        return None, None, None
    if not AGGRID_AVAILABLE:
        st.dataframe(grid_df.drop(columns=[c for c in grid_df.columns if c.startswith('pk_')], errors='ignore'), use_container_width=True, hide_index=True)
        return None, None, None
    work_df = grid_df.copy()
    work_df['__popup_click__'] = ''
    gb = GridOptionsBuilder.from_dataframe(work_df)
    gb.configure_default_column(editable=False, sortable=False, filter=False, resizable=True)
    gb.configure_selection(selection_mode='single', use_checkbox=False, rowMultiSelectWithClick=False)
    grid_options = gb.build()
    grid_options['headerHeight'] = 42
    grid_options['rowHeight'] = 40
    grid_options['animateRows'] = False
    grid_options['suppressRowTransform'] = True
    grid_options['ensureDomOrder'] = True
    grid_options['suppressMovableColumns'] = True
    click_js = JsCode("""
    function(params) {
        const colId = (params && params.column && params.column.colId) ? String(params.column.colId) : '';
        if (!colId.startsWith('d_')) { return; }
        const popupField = 'pk_' + colId.substring(2);
        const data = (params && params.node) ? params.node.data : null;
        if (!data) { return; }
        const popupKey = data[popupField];
        if (!popupKey) { return; }
        params.api.forEachNode(function(node) {
            if (node && node.data && node.data.__popup_click__) {
                node.setDataValue('__popup_click__', '');
            }
        });
        params.node.setDataValue('__popup_click__', String(popupKey) + '||' + String(Date.now()));
        params.api.refreshCells({ force: true });
    }
    """)
    grid_options['onCellClicked'] = click_js
    grid_options['onCellDoubleClicked'] = click_js
    vf_int = value_formatter_int(); vf_rate = value_formatter_rate(); cs_default = default_cell_style(); cs_mtba = mtba_cell_style(); cs_qty = qty_cell_style(target_qty)
    if view_priority == '설비 호기':
        fixed_base = [('공정명', 120, False, cs_default, None), ('호기', 80, False, cs_default, None), ('구분', 90, False, cs_default, None), ('알람명', 220, False, cs_default, None), ('MTBA', 70, False, cs_mtba, vf_int), ('알람수', 78, False, cs_default, vf_int), ('생산수량', 92, False, cs_qty, vf_int), ('MTBA Avg', 90, not show_stats, cs_default, vf_int), ('MTBA Min', 90, not show_stats, cs_default, vf_int), ('MTBA Max', 90, not show_stats, cs_default, vf_int), ('MTBA Std', 110, not show_stats, cs_default, vf_int)]
    else:
        fixed_base = [('공정명', 120, False, cs_default, None), ('구분', 90, False, cs_default, None), ('알람명', 220, False, cs_default, None), ('호기', 80, False, cs_default, None), ('MTBA', 70, False, cs_mtba, vf_int), ('알람수', 78, False, cs_default, vf_int), ('생산수량', 92, False, cs_qty, vf_int), ('MTBA Avg', 90, not show_stats, cs_default, vf_int), ('MTBA Min', 90, not show_stats, cs_default, vf_int), ('MTBA Max', 90, not show_stats, cs_default, vf_int), ('MTBA Std', 110, not show_stats, cs_default, vf_int)]
    col_defs = []
    for col, width, hide, style, vf in fixed_base:
        d = {'headerName': col, 'field': col, 'minWidth': width, 'pinned': 'left', 'hide': hide, 'cellStyle': style}
        if vf is not None:
            d['valueFormatter'] = vf
        col_defs.append(d)
    pointer_style = JsCode(f"function(params){{ return {{borderRight:'1px solid {BORDER}', cursor:'pointer'}}; }}")
    day_vf = vf_rate if result_metric == '알람율' else vf_int
    day_style = cs_mtba if result_metric == 'MTBA' else (cs_qty if result_metric == '생산수량' else pointer_style)
    for dt in date_cols:
        label = pd.to_datetime(dt).strftime('%Y-%m-%d')
        col_defs.append({'headerName': label, 'field': f'd_{label}', 'minWidth': 112, 'valueFormatter': day_vf, 'cellStyle': day_style})
        col_defs.append({'field': f'pk_{label}', 'hide': True})
    col_defs.append({'field': '__popup_click__', 'hide': True, 'editable': True})
    grid_options['columnDefs'] = col_defs
    grid_key = f"detail_grid_{panel_id}_{int(st.session_state.detail_grid_nonce.get(str(panel_id), 0))}"
    resp = _aggrid(work_df, grid_options, key=grid_key, height=min(max(440, 120 + len(work_df) * 40), 1200))
    popup_key, selected_row, click_marker = _resolve_clicked_popup_key(resp, work_df)
    if selected_row:
        st.session_state.detail_selected_row[str(panel_id)] = selected_row
    st.caption('날짜 셀 클릭 시 해당 날짜/알람 상세 팝업이 열립니다.')
    return popup_key, selected_row, click_marker


def render_fol_grid(grid_df, process_cols, result_metric, panel_id, target_qty):
    if grid_df.empty:
        st.info('FOL In-line 조건에 해당하는 데이터가 없습니다.')
        return None, None, None
    if not AGGRID_AVAILABLE:
        st.dataframe(grid_df.drop(columns=[c for c in grid_df.columns if c.startswith('pk_')], errors='ignore'), use_container_width=True, hide_index=True)
        return None, None, None
    work_df = grid_df.copy()
    work_df['__popup_click__'] = ''
    gb = GridOptionsBuilder.from_dataframe(work_df)
    gb.configure_default_column(editable=False, sortable=False, filter=False, resizable=True)
    gb.configure_selection(selection_mode='single', use_checkbox=False, rowMultiSelectWithClick=False)
    grid_options = gb.build()
    grid_options['headerHeight'] = 42
    grid_options['rowHeight'] = 42
    grid_options['animateRows'] = False
    grid_options['suppressRowTransform'] = True
    grid_options['ensureDomOrder'] = True
    grid_options['suppressMovableColumns'] = True
    click_js = JsCode("""
    function(params) {
        const colId = (params && params.column && params.column.colId) ? String(params.column.colId) : '';
        if (!colId.startsWith('p_')) { return; }
        const popupField = 'pk_' + colId.substring(2);
        const data = (params && params.node) ? params.node.data : null;
        if (!data) { return; }
        const popupKey = data[popupField];
        if (!popupKey) { return; }
        params.api.forEachNode(function(node) {
            if (node && node.data && node.data.__popup_click__) {
                node.setDataValue('__popup_click__', '');
            }
        });
        params.node.setDataValue('__popup_click__', String(popupKey) + '||' + String(Date.now()));
        params.api.refreshCells({ force: true });
    }
    """)
    grid_options['onCellClicked'] = click_js
    grid_options['onCellDoubleClicked'] = click_js
    vf_int = value_formatter_int(); vf_rate = value_formatter_rate(); cs_default = default_cell_style(); cs_mtba = mtba_cell_style(); cs_qty = qty_cell_style(target_qty)
    fixed_cols = [('모델명',88,cs_default,None), ('설비세그먼트명',190,cs_default,None), (result_metric,88,cs_mtba if result_metric=='MTBA' else cs_qty if result_metric=='생산수량' else cs_default, vf_rate if result_metric=='알람율' else vf_int)]
    if result_metric != '생산수량':
        fixed_cols.append(('생산수량',92,cs_qty,vf_int))
    col_defs = []
    for col, width, style, vf in fixed_cols:
        d = {'headerName': col, 'field': col, 'minWidth': width, 'pinned': 'left', 'cellStyle': style}
        if vf is not None:
            d['valueFormatter'] = vf
        col_defs.append(d)
    pointer_style = JsCode(f"function(params){{ return {{borderRight:'1px solid {BORDER}', cursor:'pointer'}}; }}")
    proc_vf = vf_rate if result_metric == '알람율' else vf_int
    for proc in process_cols:
        style = cs_mtba if result_metric == 'MTBA' else cs_qty if result_metric == '생산수량' else pointer_style
        col_defs.append({'headerName': proc, 'field': f'p_{proc}', 'minWidth': 128, 'valueFormatter': proc_vf, 'cellStyle': style})
        col_defs.append({'field': f'pk_{proc}', 'hide': True})
    col_defs.append({'field': '__popup_click__', 'hide': True, 'editable': True})
    grid_options['columnDefs'] = col_defs
    grid_key = f"fol_grid_{panel_id}_{int(st.session_state.detail_grid_nonce.get(str(panel_id), 0))}"
    resp = _aggrid(work_df, grid_options, key=grid_key, height=min(max(340, 110 + len(work_df) * 42), 900))
    popup_key, selected_row, click_marker = _resolve_clicked_popup_key(resp, work_df)
    if selected_row:
        st.session_state.detail_selected_row[str(panel_id)] = selected_row
    st.caption('공정 셀 클릭 시 해당 공정/알람 상세 팝업이 열립니다.')
    return popup_key, selected_row, click_marker

# ---------------------------------------------------------
# Popup
# ---------------------------------------------------------
def render_popup_alarm_table(popup_rows):
    if not popup_rows:
        st.info('상세 알람 데이터가 없습니다.')
        return
    rows_html = []
    for r in popup_rows:
        rows_html.append(
            f"<tr><td style='padding:8px 10px; text-align:center; border-bottom:1px solid #E5E7EB;'>{r.get('rank','')}</td>"
            f"<td style='padding:8px 10px; border-bottom:1px solid #E5E7EB;'>{escape(str(r.get('alarm_name','')))}</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #E5E7EB;'>{fmt_int(r.get('alarm_count',0))}</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #E5E7EB;'>{fmt_rate(r.get('alarm_rate_pct',0.0))}%</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #E5E7EB;'>{fmt_rate(r.get('share_pct',0.0))}%</td></tr>"
        )
    html = f"""
    <table style='width:100%; border-collapse:collapse; font-size:13px;'>
        <tr style='background:{ROSE};'>
            <th style='padding:8px 10px; border-bottom:1px solid #CBD0D6;'>구분</th>
            <th style='padding:8px 10px; border-bottom:1px solid #CBD0D6;'>알람명</th>
            <th style='padding:8px 10px; border-bottom:1px solid #CBD0D6;'>알람수</th>
            <th style='padding:8px 10px; border-bottom:1px solid #CBD0D6;'>알람율</th>
            <th style='padding:8px 10px; border-bottom:1px solid #CBD0D6;'>점유율</th>
        </tr>
        {''.join(rows_html)}
    </table>
    """
    components.html(html, height=max(180, min(64 + len(popup_rows) * 42, 320)), scrolling=False)


@st.dialog('상세 정보')
def detail_cell_dialog(payload, panel_id):
    title = payload.get('title') or '-'
    runtime_min = round_int(payload.get('runtime_min', 0))
    output_qty = round_int(payload.get('output_qty', 0))
    total_alarm_count = round_int(payload.get('total_alarm_count', 0))
    popup_rows = payload.get('rows', [])
    segment_name = str(payload.get('segment_name') or '').strip()
    process_name = str(payload.get('process_name') or '').strip()
    base_date = to_py_date(payload.get('base_date'), None)
    meta_parts = []
    if segment_name:
        meta_parts.append(f'세그먼트명 : {segment_name}')
    if process_name:
        meta_parts.append(f'공정명 : {process_name}')
    if base_date:
        meta_parts.append(f'선택일자 : {base_date.strftime("%Y-%m-%d")}')
    meta_line = ' / '.join(meta_parts) if meta_parts else '-'
    st.markdown(f"""
    <div class='popup-meta'>
        <div class='popup-title'>{escape(str(title))}</div>
        <div class='popup-sub'>{escape(meta_line)}</div>
        <div class='popup-sub'>가동 시간 : {fmt_int(runtime_min)}분 / 생산 수량 : {fmt_int(output_qty)} / 총 알람수 : {fmt_int(total_alarm_count)}</div>
    </div>
    """, unsafe_allow_html=True)
    render_popup_alarm_table(popup_rows)
    add_comment_section_to_popup(payload, panel_id)
    if st.button('팝업 닫기', key=f'detail_close_popup_{panel_id}', use_container_width=True):
        suppress_popup_once(panel_id, payload.get('popup_key'))
        clear_panel_popup(panel_id)
        st.rerun()

# ---------------------------------------------------------
# Query card and panel rendering
# ---------------------------------------------------------
def render_query_card_open(panel_id=None, model_name=None, source_view=None, min_date=None, max_date=None):
    if panel_id is None:
        return
    mode = st.session_state.get(f'mode_{panel_id}', 'standard')
    st.markdown("<div class='filter-wrap'>", unsafe_allow_html=True)
    if mode == 'fol':
        target_date = st.date_input('기준일', value=max_date, min_value=min_date, max_value=max_date, key=f'fol_date_{panel_id}')
        base_df = load_fol_inline_base(source_view, model_name, target_date)
        segment_options = build_fol_inline_segment_options(base_df)
        selected_segments = st.multiselect('설비세그먼트', segment_options, default=segment_options[:1] if segment_options else [], key=f'fol_segment_{panel_id}')
        process_options = sorted(base_df['process_name'].dropna().astype(str).unique().tolist()) if not base_df.empty else []
        if f'fol_prod_process_{panel_id}' not in st.session_state or st.session_state.get(f'fol_prod_process_{panel_id}') not in process_options:
            st.session_state[f'fol_prod_process_{panel_id}'] = process_options[0] if process_options else ''
        prod_process = st.selectbox('생산수량 기준 공정', process_options if process_options else [''], key=f'fol_prod_process_{panel_id}')
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            result_metric = st.selectbox('Data 결과값', ['MTBA', '생산수량'], key=f'fol_result_metric_{panel_id}')
        with c2:
            mtba_limit = int_text_input('MTBA Limit', f'fol_mtba_limit_txt_{panel_id}', 120)
        with c3:
            target_qty = int_text_input('Target Qty', f'fol_target_qty_txt_{panel_id}', 0)
        with c4:
            only_below = st.checkbox('MTBA Limit 이하만', value=False, key=f'fol_only_below_{panel_id}')
        if st.button('데이터 조회', key=f'run_fol_{panel_id}', type='primary', use_container_width=True):
            q = {'mode': 'fol_inline', 'target_date': to_py_date(target_date, max_date), 'selected_segments': selected_segments, 'prod_process': prod_process if prod_process else None, 'result_metric': result_metric, 'mtba_limit': float(mtba_limit), 'only_below': bool(only_below), 'target_qty': float(target_qty)}
            save_panel_query(panel_id, q)
            st.rerun()
    else:
        default_range = st.session_state.get(f'period_{panel_id}', get_default_this_week_range(min_date, max_date))
        period = st.date_input('조회 기간', value=default_range, min_value=min_date, max_value=max_date, key=f'period_{panel_id}')
        if isinstance(period, tuple) and len(period) == 2:
            start_d, end_d = period
        elif isinstance(period, list) and len(period) == 2:
            start_d, end_d = period[0], period[1]
        else:
            start_d = end_d = period if period else max_date
        start_d = to_py_date(start_d, min_date)
        end_d = to_py_date(end_d, max_date)
        if start_d and end_d and start_d > end_d:
            start_d, end_d = end_d, start_d
        process_options = get_processes_for_view(source_view, model_name, start_d, end_d)
        if not process_options:
            process_options = get_processes_all_for_view(source_view, model_name)
        proc_key = f'process_{panel_id}'
        if process_options:
            current = st.session_state.get(proc_key)
            if current not in process_options:
                st.session_state[proc_key] = process_options[0]
        c1, c2, c3 = st.columns([2.2, 1.2, 1.2])
        with c1:
            process_name = st.selectbox('공정', process_options if process_options else [''], key=proc_key)
        with c2:
            result_metric = st.selectbox('Data 결과값', ['MTBA', '알람수', '알람율', '생산수량'], key=f'result_metric_{panel_id}')
        with c3:
            view_priority = st.selectbox('Data view 우선순위', ['알람명', '설비 호기'], key=f'view_priority_{panel_id}')
        c4, c5, c6, c7 = st.columns([1.0, 1.0, 1.0, 1.0])
        with c4:
            alarm_worst = int_text_input('Worst 알람 수', f'alarm_worst_txt_{panel_id}', 5)
        with c5:
            mtba_worst = int_text_input('Worst 호기 수', f'mtba_worst_txt_{panel_id}', 0)
        with c6:
            mtba_limit = int_text_input('MTBA Limit', f'mtba_limit_txt_{panel_id}', 120)
        with c7:
            target_qty = int_text_input('Target Qty', f'target_qty_txt_{panel_id}', 0)

        # 바로 아래 줄에 나란히 배치
        c8, c9 = st.columns([1.2, 1.2])
        with c8:
            only_below = st.checkbox('MTBA Limit 이하만', value=False, key=f'only_below_{panel_id}')
        with c9:
            show_stats = st.checkbox('MTBA 통계 컬럼 표시', value=False, key=f'show_stats_{panel_id}')
        render_heatmap_legend()
        if st.button('데이터 조회', key=f'run_std_{panel_id}', type='primary', use_container_width=True):
            q = {'mode': 'standard', 'model_name': model_name, 'process_name': process_name, 'start_date': start_d, 'end_date': end_d, 'result_metric': result_metric, 'view_priority': view_priority, 'alarm_worst': int(alarm_worst), 'mtba_worst': int(mtba_worst), 'mtba_limit': float(mtba_limit), 'only_below': bool(only_below), 'target_qty': float(target_qty), 'show_stats': bool(show_stats)}
            save_panel_query(panel_id, q)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def handle_mode_switch(panel_id: int, min_date, max_date):
    mode_key = f'mode_{panel_id}'
    checkbox_key = f'fol_checkbox_{panel_id}'
    if mode_key not in st.session_state:
        q = next((p.get('query') for p in st.session_state.detail_panels if int(p['id']) == int(panel_id)), None)
        st.session_state[mode_key] = 'fol' if (isinstance(q, dict) and q.get('mode') == 'fol_inline') else 'standard'
    if checkbox_key not in st.session_state:
        st.session_state[checkbox_key] = (st.session_state[mode_key] == 'fol')
    desired = 'fol' if st.session_state[checkbox_key] else 'standard'
    if desired != st.session_state[mode_key]:
        st.session_state[mode_key] = desired
        clear_panel_query(panel_id)
        if desired == 'standard':
            for k in [f'fol_date_{panel_id}', f'fol_segment_{panel_id}', f'fol_prod_process_{panel_id}', f'fol_result_metric_{panel_id}', f'fol_mtba_limit_txt_{panel_id}', f'fol_target_qty_txt_{panel_id}', f'fol_only_below_{panel_id}']:
                st.session_state.pop(k, None)
            if f'period_{panel_id}' not in st.session_state:
                st.session_state[f'period_{panel_id}'] = get_default_this_week_range(min_date, max_date)
        else:
            if f'fol_date_{panel_id}' not in st.session_state:
                st.session_state[f'fol_date_{panel_id}'] = max_date
        st.rerun()


def render_standard_panel(panel_id, panel, model_name, source_view):
    query = panel.get('query')
    if not query:
        return

    q = dict(query)
    q['model_name'] = model_name

    bundle = build_standard_bundle(q, source_view)
    grid_df = build_grid_dataframe(
        bundle['rows'],
        bundle['date_cols'],
        q.get('view_priority', '알람명')
    ) if bundle.get('rows') else pd.DataFrame()

    popup_key, selected_row, click_marker = render_standard_grid(
        grid_df,
        bundle['date_cols'],
        panel_id,
        q.get('result_metric', 'MTBA'),
        q.get('target_qty', 0),
        q.get('show_stats', False),
        q.get('view_priority', '알람명')
    )

    panel_key = str(panel_id)
    suppressed = get_suppressed_popup(panel_id)
    last_marker = st.session_state.detail_last_grid_click.get(panel_key)

    if popup_key and popup_key == suppressed:
        st.session_state.detail_popup_suppressed.pop(panel_key, None)
    elif popup_key and click_marker and click_marker != last_marker and popup_key in bundle['popup_map']:
        st.session_state.detail_last_grid_click[panel_key] = click_marker
        request_panel_popup(panel_id, popup_key)
        # ⚠️  DO NOT add st.rerun() here, and DO NOT insert any widget / state
        # 변경 / early return 사이에 있는 request_panel_popup() ↔ consume_panel_popup_request()
        # 사이에 끼워 넣지 말 것.
        # 이 두 호출은 반드시 same rerun frame 에서 연속 실행되어야 popup 이 즉시 열림.
        # st.rerun() 추가 시 build_standard_bundle (5-30s) 재호출 → 팝업 5-30s 지연.

    open_key = consume_panel_popup_request(panel_id)
    if open_key and open_key in bundle['popup_map']:
        detail_cell_dialog({**bundle['popup_map'][open_key], 'popup_key': open_key}, panel_id)

def render_fol_panel(panel_id, panel, model_name, source_view):
    query = panel.get('query')
    if not query:
        return

    q = dict(query)
    target_date = to_py_date(q.get('target_date'), None)
    if target_date is None:
        st.info('기준일을 다시 선택해 주세요.')
        return

    base_df = load_fol_inline_base(source_view, model_name, target_date)

    bundle = build_fol_inline_bundle(
        base_df,
        model_name,
        target_date,
        q.get('selected_segments') or [],
        q.get('prod_process'),
        q.get('result_metric', 'MTBA'),
        safe_float(q.get('mtba_limit', 120.0), 120.0),
        bool(q.get('only_below', False))
    )

    popup_key, selected_row, click_marker = render_fol_grid(
        bundle['grid_df'],
        bundle['process_cols'],
        q.get('result_metric', 'MTBA'),
        panel_id,
        q.get('target_qty', 0)
    )

    panel_key = str(panel_id)
    suppressed = get_suppressed_popup(panel_id)
    last_marker = st.session_state.detail_last_grid_click.get(panel_key)

    if popup_key and popup_key == suppressed:
        st.session_state.detail_popup_suppressed.pop(panel_key, None)
    elif popup_key and click_marker and click_marker != last_marker and popup_key in bundle.get('popup_map', {}):
        st.session_state.detail_last_grid_click[panel_key] = click_marker
        request_panel_popup(panel_id, popup_key)
        # ⚠️  Standard panel 과 동일 규칙 — request_panel_popup ↔ consume_panel_popup_request
        # 사이에 st.rerun / 위젯 변경 / early return 추가 금지. same-frame 보장 깨지면
        # 팝업이 닫혀 보이거나, build_fol_bundle (수 초) 재호출이 발생함.

    open_key = consume_panel_popup_request(panel_id)
    if open_key and open_key in bundle.get('popup_map', {}):
        detail_cell_dialog({**bundle['popup_map'][open_key], 'popup_key': open_key}, panel_id)

def render_panel(panel, source_view, min_date, max_date, model_options):
    panel_id = int(panel['id'])
    mode_key = f'mode_{panel_id}'
    checkbox_key = f'fol_checkbox_{panel_id}'
    title_key = f'panel_title_{panel_id}'
    edit_key = f'panel_title_edit_{panel_id}'
    editor_key = f'panel_title_editor_{panel_id}'

    if title_key not in st.session_state or not str(st.session_state.get(title_key)).strip():
        st.session_state[title_key] = f'조회 패널 #{panel_id}'

    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    # -------------------------
    # 박스 위: 제목 표시 (이미지 스타일)
    # -------------------------
    title_row = st.columns([6, 1])

    with title_row[0]:
        st.markdown(
            f"<div class='query-panel-title'>{st.session_state[title_key]}</div>",
            unsafe_allow_html=True
        )

    with title_row[1]:
        if st.button('이름 변경', key=f'edit_title_btn_{panel_id}', use_container_width=True):
            st.session_state[edit_key] = not st.session_state[edit_key]
            if st.session_state[edit_key]:
                st.session_state[editor_key] = st.session_state[title_key]
            st.rerun()

    # -------------------------
    # 이름 변경 UI (버튼 눌렀을 때만 열림)
    # -------------------------
    if st.session_state.get(edit_key, False):
        st.markdown("<div class='panel-edit-wrap'>", unsafe_allow_html=True)

        edit_cols = st.columns([6, 1, 1])

        with edit_cols[0]:
            st.text_input(
                '패널 이름 변경',
                key=editor_key,
                label_visibility='collapsed',
                placeholder=f'조회 패널 #{panel_id}'
            )

        with edit_cols[1]:
            if st.button('적용', key=f'apply_title_{panel_id}', use_container_width=True):
                new_title = str(st.session_state.get(editor_key, '')).strip()
                st.session_state[title_key] = new_title if new_title else f'조회 패널 #{panel_id}'
                st.session_state[edit_key] = False
                st.rerun()

        with edit_cols[2]:
            if st.button('취소', key=f'cancel_title_{panel_id}', use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # 조회조건 전체 박스
    # -------------------------
    with st.container(border=True):

        # 1행: 모델선택 / 조회모드 / 패널추가 / 패널삭제
        row1 = st.columns([2.2, 1.3, 1.0, 1.1])

        with row1[0]:
            st.markdown(
                "<div class='helper' style='margin-bottom:4px;'>상세조회 모델 선택</div>",
                unsafe_allow_html=True
            )

            model_key = f'model_{panel_id}'
            if model_key not in st.session_state or st.session_state.get(model_key) not in model_options:
                st.session_state[model_key] = model_options[0]

            model_name = st.selectbox(
                f'모델 선택 #{panel_id}',
                model_options,
                key=model_key,
                label_visibility='collapsed'
            )

        with row1[1]:
            st.markdown(
                "<div class='helper' style='margin-bottom:4px;'>조회 모드</div>",
                unsafe_allow_html=True
            )
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            st.checkbox(
                f'FOL In-line #{panel_id}',
                key=checkbox_key
            )

        with row1[2]:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button('패널 추가', key=f'add_panel_{panel_id}', use_container_width=True):
                insert_panel_after(panel_id)
                st.rerun()

        with row1[3]:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button(
                '해당 패널 삭제',
                key=f'remove_panel_{panel_id}',
                use_container_width=True,
                disabled=(len(st.session_state.detail_panels) <= 1)
            ):
                remove_panel(panel_id)
                st.rerun()

        handle_mode_switch(panel_id, min_date, max_date)

        # 2행 이하 조회조건
        render_query_card_open(panel_id, model_name, source_view, min_date, max_date)

    # -------------------------
    # 결과 영역
    # render_query_card_open()는 조회조건만 그리고,
    # 결과는 여기서 따로 렌더링
    # -------------------------
    if st.session_state.get(mode_key, 'standard') == 'fol':
        render_fol_panel(panel_id, panel, model_name, source_view)
    else:
        render_standard_panel(panel_id, panel, model_name, source_view)

# ---------------------------------------------------------
# Page entry
# ---------------------------------------------------------
ensure_state()
ensure_alarm_comment_history_table()

# preview sec-detail 와 정렬 — vit-top-strip 6px wine + flat title.
from ui.vitals.components import render_top_strip
render_top_strip()
st.markdown("""
<div class='page-hero'>
    <div class='page-hero-title'>MTBA Detail View</div>
    <div class='page-hero-sub'>
    </div>
</div>
""", unsafe_allow_html=True)

# c1, c2 = st.columns([1.2, 1.2])
# with c1:
#     if st.button('페이지 상태 초기화', use_container_width=True):
#         reset_detail_page_state()
#         st.rerun()
# with c2:
#     if st.button('패널 1개 추가', use_container_width=True):
#         insert_panel_after(int(st.session_state.detail_panels[-1]['id']))
#         st.rerun()

source_view = resolve_source_view()
if source_view is None:
    st.error('조회에 사용할 상세 View/MV가 없습니다.')
    st.stop()
min_date, max_date = get_date_range_for_view(source_view)
model_options = get_models_for_view(source_view)
if min_date is None or max_date is None or not model_options:
    st.error('조회 가능한 기본 데이터가 없습니다.')
    st.stop()

for panel in st.session_state.detail_panels:
    render_panel(panel, source_view, min_date, max_date, model_options)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
