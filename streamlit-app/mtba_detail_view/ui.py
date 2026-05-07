# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st

from .builders import build_fol_inline_bundle, build_fol_inline_segment_options, build_grid_dataframe, build_standard_bundle
from .config import PAGE_STYLE
from .grid import render_fol_grid, render_standard_grid
from .helpers import get_default_this_week_range, int_text_input, to_py_date
from .popup import detail_cell_dialog
from .repository import (
    ensure_comment_history_table,
    get_date_range_for_view,
    get_models_for_view,
    get_processes_all_for_view,
    get_processes_for_view,
    load_detail_base,
    load_fol_inline_base,
    resolve_source_view,
)
from .state import (
    clear_panel_popup,
    clear_panel_query,
    ensure_state,
    get_last_grid_click,
    get_panels,
    get_suppressed_popup,
    insert_panel_after,
    pop_suppressed_popup,
    remove_panel,
    request_panel_popup,
    reset_page_state,
    save_panel_query,
    consume_panel_popup_request,
    set_last_grid_click,
)


def render_heatmap_legend():
    st.markdown(
        """
        <div class='legend-wrap'>
            <div class='legend-chip red'>0 ~ 60 미만</div>
            <div class='legend-chip yellow'>60 ~ 120 미만</div>
            <div class='legend-chip green'>120 이상</div>
            <div class='legend-chip prod'>Target 미만 생산수량</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _set_default_mode(panel_id: int):
    mode_key = f'mode_{panel_id}'
    checkbox_key = f'fol_checkbox_{panel_id}'
    if mode_key not in st.session_state:
        panel_query = next((p.get('query') for p in get_panels() if int(p.get('id', -1)) == int(panel_id)), None)
        st.session_state[mode_key] = 'fol' if isinstance(panel_query, dict) and panel_query.get('mode') == 'fol_inline' else 'standard'
    if checkbox_key not in st.session_state:
        st.session_state[checkbox_key] = st.session_state[mode_key] == 'fol'


def handle_mode_switch(panel_id: int, min_date, max_date):
    mode_key = f'mode_{panel_id}'
    checkbox_key = f'fol_checkbox_{panel_id}'
    _set_default_mode(panel_id)
    desired = 'fol' if st.session_state[checkbox_key] else 'standard'
    if desired == st.session_state[mode_key]:
        return

    st.session_state[mode_key] = desired
    clear_panel_query(panel_id)
    clear_panel_popup(panel_id)

    if desired == 'standard':
        for key in [
            f'fol_date_{panel_id}',
            f'fol_segment_{panel_id}',
            f'fol_prod_process_{panel_id}',
            f'fol_result_metric_{panel_id}',
            f'fol_mtba_limit_txt_{panel_id}',
            f'fol_target_qty_txt_{panel_id}',
            f'fol_only_below_{panel_id}',
        ]:
            st.session_state.pop(key, None)
        if f'period_{panel_id}' not in st.session_state:
            st.session_state[f'period_{panel_id}'] = get_default_this_week_range(min_date, max_date)
    else:
        if f'fol_date_{panel_id}' not in st.session_state:
            st.session_state[f'fol_date_{panel_id}'] = max_date

    st.rerun()


def render_query_card(panel_id: int, model_name: str, source_view: str, min_date, max_date):
    mode = st.session_state.get(f'mode_{panel_id}', 'standard')
    with st.container(border=True):
        if mode == 'fol':
            target_date = st.date_input('기준일', value=max_date, min_value=min_date, max_value=max_date, key=f'fol_date_{panel_id}')
            base_df = load_fol_inline_base(source_view, model_name, target_date)
            segment_options = build_fol_inline_segment_options(base_df)
            selected_segments = st.multiselect(
                '설비세그먼트',
                segment_options,
                default=segment_options[:1] if segment_options else [],
                key=f'fol_segment_{panel_id}',
            )
            process_options = sorted(base_df['process_name'].dropna().astype(str).unique().tolist()) if not base_df.empty else []
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
                query = {
                    'mode': 'fol_inline',
                    'target_date': to_py_date(target_date, max_date),
                    'selected_segments': selected_segments,
                    'prod_process': prod_process if prod_process else None,
                    'result_metric': result_metric,
                    'mtba_limit': float(mtba_limit),
                    'only_below': bool(only_below),
                    'target_qty': float(target_qty),
                }
                save_panel_query(panel_id, query)
                clear_panel_popup(panel_id)
                st.rerun()
            return

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

        c1, c2, c3 = st.columns([2.2, 1.2, 1.2])
        with c1:
            process_name = st.selectbox('공정', process_options if process_options else [''], key=f'process_{panel_id}')
        with c2:
            result_metric = st.selectbox('Data 결과값', ['MTBA', '알람수', '알람율', '생산수량'], key=f'result_metric_{panel_id}')
        with c3:
            view_priority = st.selectbox('Data view 우선순위', ['알람명', '설비 호기'], key=f'view_priority_{panel_id}')

        c4, c5, c6, c7, c8 = st.columns([1.0, 1.0, 1.0, 1.0, 1.2])
        with c4:
            alarm_worst = int_text_input('Worst 알람 수', f'alarm_worst_txt_{panel_id}', 5)
        with c5:
            mtba_worst = int_text_input('Worst 호기 수', f'mtba_worst_txt_{panel_id}', 0)
        with c6:
            mtba_limit = int_text_input('MTBA Limit', f'mtba_limit_txt_{panel_id}', 120)
        with c7:
            target_qty = int_text_input('Target Qty', f'target_qty_txt_{panel_id}', 0)
        with c8:
            only_below = st.checkbox('MTBA Limit 이하만', value=False, key=f'only_below_{panel_id}')

        show_stats = st.checkbox('MTBA 통계 컬럼 표시', value=False, key=f'show_stats_{panel_id}')
        render_heatmap_legend()

        if st.button('데이터 조회', key=f'run_std_{panel_id}', type='primary', use_container_width=True):
            query = {
                'mode': 'standard',
                'model_name': model_name,
                'process_name': process_name,
                'start_date': start_d,
                'end_date': end_d,
                'result_metric': result_metric,
                'view_priority': view_priority,
                'alarm_worst': int(alarm_worst),
                'mtba_worst': int(mtba_worst),
                'mtba_limit': float(mtba_limit),
                'only_below': bool(only_below),
                'target_qty': float(target_qty),
                'show_stats': bool(show_stats),
            }
            save_panel_query(panel_id, query)
            clear_panel_popup(panel_id)
            st.rerun()


def render_standard_panel(panel_id: int, panel: dict, model_name: str, source_view: str, min_date, max_date):
    render_query_card(panel_id, model_name, source_view, min_date, max_date)
    query = panel.get('query')
    if not query:
        return

    base_df = load_detail_base(source_view, model_name, query['process_name'], query['start_date'], query['end_date'])
    bundle = build_standard_bundle(base_df, {**query, 'model_name': model_name})
    grid_df = build_grid_dataframe(bundle['rows'], bundle['date_cols'], query.get('view_priority', '알람명')) if bundle.get('rows') else pd.DataFrame()
    popup_key, selected_row, click_marker = render_standard_grid(
        grid_df,
        bundle['date_cols'],
        panel_id,
        query.get('result_metric', 'MTBA'),
        query.get('target_qty', 0),
        query.get('show_stats', False),
        query.get('view_priority', '알람명'),
    )
    if selected_row:
        st.session_state.detail_selected_row[str(panel_id)] = selected_row

    suppressed = get_suppressed_popup(panel_id)
    last_click = get_last_grid_click(panel_id)
    if popup_key and popup_key == suppressed:
        pop_suppressed_popup(panel_id)
    elif popup_key and click_marker and click_marker != last_click and popup_key in bundle['popup_map']:
        set_last_grid_click(panel_id, click_marker)
        request_panel_popup(panel_id, popup_key)
        st.rerun()

    open_key = consume_panel_popup_request(panel_id)
    if open_key and open_key in bundle['popup_map']:
        detail_cell_dialog({**bundle['popup_map'][open_key], 'popup_key': open_key}, panel_id)


def render_fol_panel(panel_id: int, panel: dict, model_name: str, source_view: str, min_date, max_date):
    render_query_card(panel_id, model_name, source_view, min_date, max_date)
    query = panel.get('query')
    if not query:
        return

    target_date = to_py_date(query.get('target_date'), None)
    if target_date is None:
        st.info('기준일을 다시 선택해 주세요.')
        return

    base_df = load_fol_inline_base(source_view, model_name, target_date)
    bundle = build_fol_inline_bundle(
        base_df,
        model_name,
        target_date,
        query.get('selected_segments') or [],
        query.get('prod_process'),
        query.get('result_metric', 'MTBA'),
        float(query.get('mtba_limit', 120.0)),
        bool(query.get('only_below', False)),
    )
    popup_key, selected_row, click_marker = render_fol_grid(
        bundle['grid_df'],
        bundle['process_cols'],
        query.get('result_metric', 'MTBA'),
        panel_id,
        query.get('target_qty', 0),
    )
    if selected_row:
        st.session_state.detail_selected_row[str(panel_id)] = selected_row

    suppressed = get_suppressed_popup(panel_id)
    last_click = get_last_grid_click(panel_id)
    if popup_key and popup_key == suppressed:
        pop_suppressed_popup(panel_id)
    elif popup_key and click_marker and click_marker != last_click and popup_key in bundle['popup_map']:
        set_last_grid_click(panel_id, click_marker)
        request_panel_popup(panel_id, popup_key)
        st.rerun()

    open_key = consume_panel_popup_request(panel_id)
    if open_key and open_key in bundle['popup_map']:
        detail_cell_dialog({**bundle['popup_map'][open_key], 'popup_key': open_key}, panel_id)


def render_panel(panel: dict, source_view: str, min_date, max_date, model_options: list[str]):
    panel_id = int(panel['id'])
    _set_default_mode(panel_id)

    st.markdown(
        f"""
        <div class='soft-card'>
            <div class='panel-title'>MTBA 상세 조회 #{panel_id}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top = st.columns([2.3, 3.7, 0.75, 0.75])
    with top[0]:
        model_col, fol_col = st.columns([1.8, 1.0])
        with model_col:
            model_name = st.selectbox(f'모델 선택 #{panel_id}', model_options, key=f'model_{panel_id}')
        with fol_col:
            st.checkbox(f'FOL In-line #{panel_id}', key=f'fol_checkbox_{panel_id}')
    with top[2]:
        if st.button('패널+', key=f'add_panel_{panel_id}', use_container_width=True):
            insert_panel_after(panel_id)
            st.rerun()
    with top[3]:
        disabled = len(get_panels()) <= 1
        if st.button('삭제', key=f'remove_panel_{panel_id}', use_container_width=True, disabled=disabled):
            remove_panel(panel_id)
            st.rerun()

    handle_mode_switch(panel_id, min_date, max_date)
    if st.session_state.get(f'mode_{panel_id}', 'standard') == 'fol':
        render_fol_panel(panel_id, panel, model_name, source_view, min_date, max_date)
    else:
        render_standard_panel(panel_id, panel, model_name, source_view, min_date, max_date)


def main():
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    ensure_state()
    ensure_comment_history_table()

    st.markdown(
        """
        <div class='soft-card'>
            <div class='section-title'>MTBA Detail View</div>
            <div class='helper-text'>
                초기 로딩 시 자동 rerun이 발생하던 문제를 수정한 핫픽스 버전입니다.<br>
                popup은 실제 클릭 marker가 있을 때만 열리며, 동일 marker의 중복 rerun도 차단합니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.2, 1.2])
    with c1:
        if st.button('페이지 상태 초기화', use_container_width=True):
            reset_page_state()
            st.rerun()
    with c2:
        if st.button('패널 1개 추가', use_container_width=True):
            last_panel_id = int(get_panels()[-1]['id'])
            insert_panel_after(last_panel_id)
            st.rerun()

    source_view = resolve_source_view()
    if source_view is None:
        st.error('조회에 사용할 상세 View/MV가 없습니다.')
        st.stop()

    min_date, max_date = get_date_range_for_view(source_view)
    model_options = get_models_for_view(source_view)
    if min_date is None or max_date is None or not model_options:
        st.error('조회 가능한 기본 데이터가 없습니다.')
        st.stop()

    for panel in get_panels():
        render_panel(panel, source_view, min_date, max_date, model_options)
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
