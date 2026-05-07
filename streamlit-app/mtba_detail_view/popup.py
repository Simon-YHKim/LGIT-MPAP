# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from .comments import render_comment_section
from .helpers import fmt1, html_escape, to_py_date
from .state import clear_panel_popup, suppress_popup_once


def render_popup_alarm_table(popup_rows: list[dict]):
    if not popup_rows:
        st.info('상세 알람 데이터가 없습니다.')
        return

    rows_html = []
    for row in popup_rows:
        rows_html.append(
            '<tr>'
            f"<td style='padding:8px 10px; text-align:center; border-bottom:1px solid #eee;'>{row.get('rank', '')}</td>"
            f"<td style='padding:8px 10px; border-bottom:1px solid #eee;'>{html_escape(row.get('alarm_name', ''))}</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #eee;'>{fmt1(row.get('alarm_count', 0))}</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #eee;'>{fmt1(row.get('alarm_rate_pct', 0.0))}%</td>"
            f"<td style='padding:8px 10px; text-align:right; border-bottom:1px solid #eee;'>{fmt1(row.get('share_pct', 0.0))}%</td>"
            '</tr>'
        )
    html = f"""
    <table style='width:100%; border-collapse:collapse; font-size:13px;'>
        <thead>
            <tr style='background:#f7e7ec;'>
                <th style='padding:8px 10px; border-bottom:1px solid #ddd;'>구분</th>
                <th style='padding:8px 10px; border-bottom:1px solid #ddd;'>알람명</th>
                <th style='padding:8px 10px; border-bottom:1px solid #ddd;'>알람수</th>
                <th style='padding:8px 10px; border-bottom:1px solid #ddd;'>알람율</th>
                <th style='padding:8px 10px; border-bottom:1px solid #ddd;'>점유율</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
    """
    components.html(html, height=max(180, min(64 + len(popup_rows) * 42, 320)), scrolling=False)


@st.dialog('상세 정보')
def detail_cell_dialog(payload: dict, panel_id: int):
    title = payload.get('title') or '-'
    runtime_min = payload.get('runtime_min', 0.0)
    output_qty = payload.get('output_qty', 0.0)
    total_alarm_count = payload.get('total_alarm_count', 0.0)
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

    st.markdown(
        f"""
        <div class='popup-meta'>
            <div class='popup-title'>{html_escape(title)}</div>
            <div class='popup-sub'>{html_escape(meta_line)}</div>
            <div class='popup-sub'>가동 시간 : {runtime_min:.1f}분 / 생산 수량 : {output_qty:.1f} / 총 알람수 : {total_alarm_count:.1f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_popup_alarm_table(popup_rows)
    render_comment_section(payload, panel_id)

    if st.button('팝업 닫기', key=f'detail_close_popup_{panel_id}', use_container_width=True):
        popup_key = payload.get('popup_key')
        if popup_key:
            suppress_popup_once(panel_id, str(popup_key))
        clear_panel_popup(panel_id)
        st.rerun()
