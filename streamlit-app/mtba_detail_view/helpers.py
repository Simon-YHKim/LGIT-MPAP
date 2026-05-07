# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from html import escape
from typing import Any

import pandas as pd
import streamlit as st


def make_query_signature(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return default if pd.isna(v) else float(v)
    except Exception:
        return default


def fmt1(v: Any) -> str:
    return f"{safe_float(v):.1f}"


def fmt_int(v: Any) -> str:
    return f"{int(round(safe_float(v))):,}"


def to_py_date(v: Any, fallback=None):
    if v is None:
        return fallback
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    try:
        ts = pd.to_datetime(v, errors="coerce")
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


def popup_key_standard(equipment_id, base_date) -> str:
    return f"{equipment_id}|{base_date}"


def popup_key_fol(segment_name: str, process_name: str, base_date) -> str:
    return f"{segment_name}|{process_name}|{base_date}"


def html_escape(text: Any) -> str:
    return escape(str(text or ''))
