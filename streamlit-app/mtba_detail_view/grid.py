# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st

from .config import BORDER, PASTEL_GREEN, PASTEL_RED, PASTEL_RED_STRONG, PASTEL_YELLOW, PRIMARY, ROSE, TEXT

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False
    AgGrid = GridOptionsBuilder = GridUpdateMode = DataReturnMode = JsCode = None


def value_formatter_1dp():
    return JsCode("function(params){ const v=Number(params.value); return isNaN(v)?(params.value ?? ''):v.toFixed(1); }") if AGGRID_AVAILABLE else None


def mtba_cell_style():
    return JsCode(
        f"function(params){{ const v=Number(params.value); if(isNaN(v)) return {{borderRight:'1px solid {BORDER}'}}; if(v<60) return {{backgroundColor:'{PASTEL_RED}',borderRight:'1px solid {BORDER}'}}; if(v<120) return {{backgroundColor:'{PASTEL_YELLOW}',borderRight:'1px solid {BORDER}'}}; return {{backgroundColor:'{PASTEL_GREEN}',borderRight:'1px solid {BORDER}'}}; }}"
    ) if AGGRID_AVAILABLE else None


def qty_cell_style(target_qty: float):
    return JsCode(
        f"function(params){{ const v=Number(params.value); if(isNaN(v)) return {{borderRight:'1px solid {BORDER}'}}; if(v<{float(target_qty):.6f}) return {{backgroundColor:'{PASTEL_RED_STRONG}',borderRight:'1px solid {BORDER}'}}; return {{borderRight:'1px solid {BORDER}'}}; }}"
    ) if AGGRID_AVAILABLE else None


def default_cell_style():
    return JsCode(f"function(params){{ return {{borderRight:'1px solid {BORDER}'}}; }}") if AGGRID_AVAILABLE else None


def pointer_style():
    return JsCode(f"function(params){{ return {{borderRight:'1px solid {BORDER}', cursor:'pointer'}}; }}") if AGGRID_AVAILABLE else None


def build_common_grid_css_dict():
    return {
        '.ag-root-wrapper': {'border': f'1px solid {BORDER} !important', 'border-radius': '20px !important', 'overflow': 'hidden !important'},
        '.ag-header': {'background': f'linear-gradient(180deg, {ROSE}, #FFFDFE) !important'},
        '.ag-header-cell': {'font-weight': '800 !important', 'color': f'{PRIMARY} !important', 'justify-content': 'center !important', 'text-align': 'center !important', 'border-right': f'1px solid {BORDER} !important'},
        '.ag-cell': {'font-size': '12px !important', 'display': 'flex !important', 'align-items': 'center !important', 'justify-content': 'center !important', 'color': f'{TEXT} !important', 'border-right': f'1px solid {BORDER} !important'},
        '.ag-row': {'border-bottom': '1px solid #F0E5EA !important'},
        '.ag-row-hover': {'background-color': '#FCF7F9 !important'},
        '.ag-row-selected': {'background-color': '#F9EDF1 !important'},
    }


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
    """
    자동 focus/focused cell 은 무시하고,
    click_js가 넣은 __popup_click__ marker가 있을 때만 popup을 연다.
    이게 초기 진입 시 무한 rerun의 핵심 원인 방지 포인트다.
    """
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
    ag_kwargs = dict(
        gridOptions=grid_options,
        key=key,
        allow_unsafe_jscode=True,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=False,
        theme='streamlit',
        height=height,
        reload_data=False,
        custom_css=build_common_grid_css_dict(),
    )
    update_mode = _grid_update_mode()
    try:
        return AgGrid(work_df, update_on=update_mode, **ag_kwargs)
    except TypeError:
        return AgGrid(work_df, update_mode=update_mode, **ag_kwargs)


def render_standard_grid(grid_df: pd.DataFrame, date_cols: list, panel_id: int, result_metric: str, target_qty: float, show_stats: bool, view_priority: str = '알람명'):
    if grid_df.empty:
        st.info('조회 조건에 해당하는 데이터가 없습니다.')
        return None, None, None
    if not AGGRID_AVAILABLE:
        st.dataframe(grid_df, use_container_width=True, hide_index=True)
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

    vf = value_formatter_1dp()
    cs_default = default_cell_style()
    cs_mtba = mtba_cell_style()
    cs_qty = qty_cell_style(target_qty)

    if view_priority == '설비 호기':
        fixed_base = [
            ('공정명', 120, False, cs_default),
            ('호기', 80, False, cs_default),
            ('구분', 90, False, cs_default),
            ('알람명', 220, False, cs_default),
            ('MTBA', 70, False, cs_mtba),
            ('알람수', 78, False, cs_default),
            ('생산수량', 92, False, cs_qty),
            ('MTBA Avg', 90, not show_stats, cs_default),
            ('MTBA Min', 90, not show_stats, cs_default),
            ('MTBA Max', 90, not show_stats, cs_default),
            ('MTBA Std', 110, not show_stats, cs_default),
        ]
    else:
        fixed_base = [
            ('공정명', 120, False, cs_default),
            ('구분', 90, False, cs_default),
            ('알람명', 220, False, cs_default),
            ('호기', 80, False, cs_default),
            ('MTBA', 70, False, cs_mtba),
            ('알람수', 78, False, cs_default),
            ('생산수량', 92, False, cs_qty),
            ('MTBA Avg', 90, not show_stats, cs_default),
            ('MTBA Min', 90, not show_stats, cs_default),
            ('MTBA Max', 90, not show_stats, cs_default),
            ('MTBA Std', 110, not show_stats, cs_default),
        ]

    col_defs = []
    for col, width, hide, style in fixed_base:
        d = {'headerName': col, 'field': col, 'minWidth': width, 'pinned': 'left', 'hide': hide, 'valueFormatter': vf, 'cellStyle': style}
        if col in ['공정명', '구분', '알람명', '호기']:
            d.pop('valueFormatter', None)
        col_defs.append(d)

    day_style = cs_mtba if result_metric == 'MTBA' else (cs_qty if result_metric == '생산수량' else pointer_style())
    for dt in date_cols:
        label = pd.to_datetime(dt).strftime('%Y-%m-%d')
        col_defs.append({'headerName': label, 'field': f'd_{label}', 'minWidth': 112, 'valueFormatter': vf, 'cellStyle': day_style})
        col_defs.append({'field': f'pk_{label}', 'hide': True})
    col_defs.append({'field': '__popup_click__', 'hide': True, 'editable': True})
    grid_options['columnDefs'] = col_defs

    resp = _aggrid(work_df, grid_options, key=f'detail_grid_{panel_id}', height=min(max(440, 120 + len(work_df) * 40), 1200))
    popup_key, selected_row, click_marker = _resolve_clicked_popup_key(resp, work_df)
    if selected_row:
        st.caption(f"날짜 셀 클릭 시 상세 팝업이 열립니다. 현재 행: 알람명={selected_row.get('알람명', '-')} / 호기={selected_row.get('호기', '-')}")
    else:
        st.caption('날짜 셀 클릭 시 해당 날짜/알람 상세 팝업이 열립니다.')
    return popup_key, selected_row, click_marker


def render_fol_grid(grid_df: pd.DataFrame, process_cols: list[str], result_metric: str, panel_id: int, target_qty: float):
    if grid_df.empty:
        st.info('FOL In-line 조건에 해당하는 데이터가 없습니다.')
        return None, None, None
    if not AGGRID_AVAILABLE:
        st.dataframe(grid_df, use_container_width=True, hide_index=True)
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

    vf = value_formatter_1dp()
    cs_default = default_cell_style()
    cs_mtba = mtba_cell_style()
    cs_qty = qty_cell_style(target_qty)
    fixed_cols = [
        ('모델명', 88, cs_default),
        ('설비세그먼트명', 190, cs_default),
        (result_metric, 88, cs_mtba if result_metric == 'MTBA' else cs_qty if result_metric == '생산수량' else cs_default),
    ]
    if result_metric != '생산수량':
        fixed_cols.append(('생산수량', 92, cs_qty))

    col_defs = []
    for col, width, style in fixed_cols:
        d = {'headerName': col, 'field': col, 'minWidth': width, 'pinned': 'left', 'valueFormatter': vf, 'cellStyle': style}
        if col in ['모델명', '설비세그먼트명']:
            d.pop('valueFormatter', None)
        col_defs.append(d)

    proc_style = cs_mtba if result_metric == 'MTBA' else cs_qty if result_metric == '생산수량' else pointer_style()
    for proc in process_cols:
        col_defs.append({'headerName': proc, 'field': f'p_{proc}', 'minWidth': 128, 'valueFormatter': vf, 'cellStyle': proc_style})
        col_defs.append({'field': f'pk_{proc}', 'hide': True})
    col_defs.append({'field': '__popup_click__', 'hide': True, 'editable': True})
    grid_options['columnDefs'] = col_defs

    resp = _aggrid(work_df, grid_options, key=f'fol_grid_{panel_id}', height=min(max(340, 110 + len(work_df) * 42), 900))
    popup_key, selected_row, click_marker = _resolve_clicked_popup_key(resp, work_df)
    if selected_row:
        st.caption(f"공정 셀 클릭 시 상세 팝업이 열립니다. 현재 행: 세그먼트={selected_row.get('설비세그먼트명', '-')} / 모델={selected_row.get('모델명', '-')}")
    else:
        st.caption('공정 셀 클릭 시 해당 공정/알람 상세 팝업이 열립니다.')
    return popup_key, selected_row, click_marker
