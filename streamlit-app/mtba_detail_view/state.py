# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st

from .helpers import make_query_signature

PANEL_DEFAULT = {"id": 1, "query": None, "sig": None}


def ensure_state() -> None:
    panels = st.session_state.get('detail_panels')
    valid = isinstance(panels, list) and len(panels) > 0 and all(isinstance(p, dict) and 'id' in p for p in panels)
    if not valid:
        st.session_state.detail_panels = [PANEL_DEFAULT.copy()]

    defaults = {
        'detail_next_panel_id': max((int(p.get('id', 0)) for p in st.session_state.detail_panels), default=1) + 1,
        'detail_popup_request': {},
        'detail_popup_suppressed': {},
        'detail_selected_row': {},
        'detail_last_grid_click': {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_page_state() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith('detail_') or key.startswith('mode_') or key.startswith('fol_checkbox_'):
            st.session_state.pop(key, None)
    st.session_state.detail_panels = [PANEL_DEFAULT.copy()]
    st.session_state.detail_next_panel_id = 2
    st.session_state.detail_popup_request = {}
    st.session_state.detail_popup_suppressed = {}
    st.session_state.detail_selected_row = {}
    st.session_state.detail_last_grid_click = {}


def get_panels() -> list[dict]:
    ensure_state()
    return st.session_state.detail_panels


def insert_panel_after(after_panel_id: int) -> None:
    ensure_state()
    panels = st.session_state.detail_panels
    new_id = int(st.session_state.get('detail_next_panel_id', 1))
    st.session_state.detail_next_panel_id = new_id + 1
    new_panel = {'id': new_id, 'query': None, 'sig': None}

    insert_idx = len(panels)
    for i, panel in enumerate(panels):
        if int(panel.get('id', -1)) == int(after_panel_id):
            insert_idx = i + 1
            break
    panels.insert(insert_idx, new_panel)


def remove_panel(panel_id: int) -> None:
    ensure_state()
    panels = st.session_state.detail_panels
    if len(panels) <= 1:
        return
    st.session_state.detail_panels = [p for p in panels if int(p.get('id', -1)) != int(panel_id)]
    clear_panel_state(panel_id)


def save_panel_query(panel_id: int, query: dict) -> None:
    sig = make_query_signature(query)
    for panel in st.session_state.detail_panels:
        if int(panel.get('id', -1)) == int(panel_id):
            panel['query'] = query
            panel['sig'] = sig
            break


def clear_panel_query(panel_id: int) -> None:
    for panel in st.session_state.detail_panels:
        if int(panel.get('id', -1)) == int(panel_id):
            panel['query'] = None
            panel['sig'] = None
            break
    clear_panel_popup(panel_id)


def request_panel_popup(panel_id: int, popup_key: str) -> None:
    if not popup_key:
        return
    st.session_state.detail_popup_request[str(panel_id)] = popup_key


def consume_panel_popup_request(panel_id: int):
    return st.session_state.detail_popup_request.pop(str(panel_id), None)


def suppress_popup_once(panel_id: int, popup_key: str) -> None:
    st.session_state.detail_popup_suppressed[str(panel_id)] = popup_key


def pop_suppressed_popup(panel_id: int):
    return st.session_state.detail_popup_suppressed.pop(str(panel_id), None)


def get_suppressed_popup(panel_id: int):
    return st.session_state.detail_popup_suppressed.get(str(panel_id))


def clear_panel_popup(panel_id: int) -> None:
    st.session_state.detail_popup_request.pop(str(panel_id), None)
    st.session_state.detail_popup_suppressed.pop(str(panel_id), None)
    st.session_state.detail_selected_row.pop(str(panel_id), None)
    st.session_state.detail_last_grid_click.pop(str(panel_id), None)
    for key in list(st.session_state.keys()):
        if key.startswith(f'comment_alarm_select_{panel_id}') or key.startswith(f'comment_text_{panel_id}'):
            st.session_state.pop(key, None)


def clear_panel_state(panel_id: int) -> None:
    clear_panel_query(panel_id)
    for suffix in [
        f'mode_{panel_id}',
        f'fol_checkbox_{panel_id}',
        f'model_{panel_id}',
        f'period_{panel_id}',
        f'process_{panel_id}',
        f'result_metric_{panel_id}',
        f'view_priority_{panel_id}',
        f'alarm_worst_txt_{panel_id}',
        f'mtba_worst_txt_{panel_id}',
        f'mtba_limit_txt_{panel_id}',
        f'target_qty_txt_{panel_id}',
        f'only_below_{panel_id}',
        f'show_stats_{panel_id}',
        f'fol_date_{panel_id}',
        f'fol_segment_{panel_id}',
        f'fol_prod_process_{panel_id}',
        f'fol_result_metric_{panel_id}',
        f'fol_mtba_limit_txt_{panel_id}',
        f'fol_target_qty_txt_{panel_id}',
        f'fol_only_below_{panel_id}',
    ]:
        st.session_state.pop(suffix, None)


def get_last_grid_click(panel_id: int):
    return st.session_state.detail_last_grid_click.get(str(panel_id))


def set_last_grid_click(panel_id: int, marker: str | None) -> None:
    if marker is None:
        st.session_state.detail_last_grid_click.pop(str(panel_id), None)
    else:
        st.session_state.detail_last_grid_click[str(panel_id)] = marker
