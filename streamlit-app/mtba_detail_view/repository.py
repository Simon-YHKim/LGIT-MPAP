# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine
from .config import ALLOWED_MODELS, COMMENT_TABLE, DIM_EQUIPMENT, FALLBACK_MV, MASTER_MV
from .helpers import parse_relation_name, to_py_date

engine = get_engine()


def get_engine_instance():
    return engine


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
    sql = text(
        'SELECT column_name '
        'FROM information_schema.columns '
        'WHERE table_schema=:schema_name AND table_name=:rel_name '
        'ORDER BY ordinal_position'
    )
    df = pd.read_sql(sql, engine, params={'schema_name': schema_name, 'rel_name': rel_name})
    return set(df['column_name'].dropna().astype(str).tolist()) if not df.empty else set()


@st.cache_data(ttl=300, show_spinner=False)
def get_date_range_for_view(source_view):
    df = pd.read_sql(text(f'SELECT MIN(base_date) AS min_d, MAX(base_date) AS max_d FROM {source_view}'), engine)
    if df.empty:
        return None, None
    return to_py_date(df.loc[0, 'min_d']), to_py_date(df.loc[0, 'max_d'])


@st.cache_data(ttl=300, show_spinner=False)
def get_models_for_view(source_view):
    df = pd.read_sql(
        text(f'SELECT DISTINCT model_name FROM {source_view} WHERE model_name IS NOT NULL ORDER BY model_name'),
        engine,
    )
    models = df['model_name'].dropna().astype(str).tolist() if not df.empty else []
    return [m for m in models if m in ALLOWED_MODELS]


@st.cache_data(ttl=300, show_spinner=False)
def get_processes_for_view(source_view, model_name, start_d, end_d):
    sql = text(
        f'SELECT DISTINCT process_name FROM {source_view} '
        'WHERE model_name=:m AND base_date BETWEEN :s AND :e AND process_name IS NOT NULL '
        'ORDER BY process_name'
    )
    df = pd.read_sql(sql, engine, params={'m': model_name, 's': start_d, 'e': end_d})
    return df['process_name'].dropna().astype(str).tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def get_processes_all_for_view(source_view, model_name):
    sql = text(
        f'SELECT DISTINCT process_name FROM {source_view} '
        'WHERE model_name=:m AND process_name IS NOT NULL '
        'ORDER BY process_name'
    )
    df = pd.read_sql(sql, engine, params={'m': model_name})
    return df['process_name'].dropna().astype(str).tolist() if not df.empty else []


@st.cache_data(ttl=300, show_spinner=False)
def load_detail_base(source_view, model_name, process_name, start_d, end_d):
    cols = get_relation_columns(source_view)
    alarm_code_expr = 'alarm_code' if 'alarm_code' in cols else 'NULL::text AS alarm_code'
    runtime_col = next((c for c in ['runtime_minutes', 'runtime', 'daily_runtime_minutes', 'daily_runtime'] if c in cols), None)
    runtime_expr = f'{runtime_col} AS runtime_minutes' if runtime_col else 'NULL::numeric AS runtime_minutes'

    sql = text(
        f"SELECT base_date, process_name, model_name, equipment_id, equipment_name, equipment_no, {alarm_code_expr}, "
        f"alarm_name, alarm_count, output_qty, daily_mtba, {runtime_expr} "
        f"FROM {source_view} "
        "WHERE model_name=:m AND process_name=:p AND base_date BETWEEN :s AND :e AND alarm_name IS NOT NULL "
        "ORDER BY base_date DESC, equipment_no, alarm_name"
    )
    df = pd.read_sql(sql, engine, params={'m': model_name, 'p': process_name, 's': start_d, 'e': end_d})
    if df.empty:
        return df

    df['base_date'] = pd.to_datetime(df['base_date'], errors='coerce').dt.date
    for col in ['alarm_count', 'output_qty', 'daily_mtba', 'runtime_minutes']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    eq_mtba = (
        df.groupby(['equipment_id', 'equipment_no', 'equipment_name'], dropna=False)['daily_mtba']
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={'daily_mtba': 'mtba'})
    )
    return df.merge(eq_mtba[['equipment_id', 'mtba']], on='equipment_id', how='left')


@st.cache_data(ttl=300, show_spinner=False)
def load_fol_inline_base(source_view, model_name, target_date):
    cols = get_relation_columns(source_view)
    alarm_code_expr = 'v.alarm_code' if 'alarm_code' in cols else 'NULL::text AS alarm_code'
    runtime_col = next((c for c in ['runtime_minutes', 'runtime', 'daily_runtime_minutes', 'daily_runtime'] if c in cols), None)
    runtime_expr = f'v.{runtime_col} AS runtime_minutes' if runtime_col else 'NULL::numeric AS runtime_minutes'

    sql = text(
        f"SELECT v.base_date, v.process_name, v.model_name, v.equipment_id, v.equipment_name, v.equipment_no, "
        f"de.segment_name AS equipment_segment_name, {alarm_code_expr}, v.alarm_name, v.alarm_count, "
        f"v.output_qty, v.daily_mtba, {runtime_expr} "
        f"FROM {source_view} v "
        f"LEFT JOIN {DIM_EQUIPMENT} de ON v.equipment_id = de.equipment_id "
        "WHERE v.model_name=:m AND v.base_date=:d "
        "ORDER BY v.process_name, equipment_segment_name, v.equipment_no, v.alarm_name"
    )
    df = pd.read_sql(sql, engine, params={'m': model_name, 'd': target_date})
    if df.empty:
        return df

    df['base_date'] = pd.to_datetime(df['base_date'], errors='coerce').dt.date
    df['equipment_segment_name'] = df['equipment_segment_name'].fillna('').astype(str).str.strip()
    for col in ['alarm_count', 'output_qty', 'daily_mtba', 'runtime_minutes']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def ensure_comment_history_table() -> None:
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
    CREATE INDEX IF NOT EXISTS idx_alarm_comment_hist_std
        ON {COMMENT_TABLE} (popup_scope, equipment_id, base_date, alarm_name, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_alarm_comment_hist_fol
        ON {COMMENT_TABLE} (popup_scope, segment_name, process_name, base_date, alarm_name, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_alarm_comment_hist_code
        ON {COMMENT_TABLE} (alarm_code, created_at DESC);
    """
    with engine.begin() as conn:
        for stmt in [s.strip() for s in ddl.split(';') if s.strip()]:
            conn.execute(text(stmt))
