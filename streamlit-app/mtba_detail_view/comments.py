# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from .config import COMMENT_TABLE
from .repository import get_engine_instance
from .state import request_panel_popup

engine = get_engine_instance()


def insert_alarm_comment(payload: dict) -> None:
    sql = text(f"""
        INSERT INTO {COMMENT_TABLE}
        (
            popup_scope, equipment_id, segment_name, base_date,
            alarm_code, alarm_name, model_name, process_name,
            equipment_name, equipment_no, comment_text, created_by
        )
        VALUES
        (
            :popup_scope, :equipment_id, :segment_name, :base_date,
            :alarm_code, :alarm_name, :model_name, :process_name,
            :equipment_name, :equipment_no, :comment_text, :created_by
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql, payload)


def load_alarm_comment_history(popup_payload: dict, alarm_name: str, alarm_code: str | None = None, limit: int = 100):
    popup_scope = str(popup_payload.get('popup_scope', 'standard'))
    params = {
        'popup_scope': popup_scope,
        'base_date': popup_payload.get('base_date'),
        'alarm_name': alarm_name,
        'alarm_code': alarm_code,
        'limit': int(limit),
    }
    where_sql = [
        'popup_scope = :popup_scope',
        'base_date = :base_date',
        'alarm_name = :alarm_name',
    ]
    if popup_scope == 'fol':
        where_sql += [
            "COALESCE(segment_name,'') = COALESCE(:segment_name,'')",
            "COALESCE(process_name,'') = COALESCE(:process_name,'')",
        ]
        params['segment_name'] = popup_payload.get('segment_name')
        params['process_name'] = popup_payload.get('process_name')
    else:
        where_sql += ["COALESCE(equipment_id,-1) = COALESCE(:equipment_id,-1)"]
        params['equipment_id'] = popup_payload.get('equipment_id')

    if alarm_code:
        where_sql.append("COALESCE(alarm_code,'') = COALESCE(:alarm_code,'')")

    sql = text(f"""
        SELECT id, created_at, COALESCE(created_by,'-') AS created_by, alarm_code, alarm_name, comment_text
        FROM {COMMENT_TABLE}
        WHERE {' AND '.join(where_sql)}
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
    """)
    return pd.read_sql(sql, engine, params=params)


def render_comment_section(popup_payload: dict, panel_id: int):
    rows = popup_payload.get('rows', []) or []
    if not rows:
        st.info('Comment를 남길 알람 정보가 없습니다.')
        return

    alarm_options, option_map = [], {}
    for row in rows:
        code = str(row.get('alarm_code') or '').strip()
        name = str(row.get('alarm_name') or '').strip()
        label = f"[{code}] {name}" if code else name
        if label not in option_map:
            alarm_options.append(label)
            option_map[label] = {'alarm_code': code, 'alarm_name': name}

    st.markdown('### Comment 입력 / 이력')
    selected_label = st.selectbox('알람 선택', alarm_options, key=f'comment_alarm_select_{panel_id}')
    selected_alarm = option_map[selected_label]

    latest_df = load_alarm_comment_history(
        popup_payload,
        selected_alarm['alarm_name'],
        selected_alarm['alarm_code'],
        limit=1,
    )
    default_text = '' if latest_df.empty else str(latest_df.iloc[0]['comment_text'])
    comment_key = f"comment_text_{panel_id}_{selected_alarm['alarm_name']}"
    if comment_key not in st.session_state:
        st.session_state[comment_key] = default_text

    st.text_area(
        'Comment',
        key=comment_key,
        height=140,
        placeholder='알람 원인, 조치 내용, 재발 방지 대책 등을 입력하세요.',
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        save_clicked = st.button('Comment 저장', key=f'comment_save_{panel_id}', type='primary', use_container_width=True)
    with c2:
        st.caption('저장 시 수정이 아니라 이력으로 누적됩니다.')

    if save_clicked:
        text_value = (st.session_state.get(comment_key) or '').strip()
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
            if popup_payload.get('popup_key'):
                request_panel_popup(panel_id, popup_payload.get('popup_key'))
            st.success('Comment가 저장되었습니다.')
            st.rerun()

    st.markdown('#### Comment 이력')
    hist_df = load_alarm_comment_history(
        popup_payload,
        selected_alarm['alarm_name'],
        selected_alarm['alarm_code'],
        limit=100,
    )
    if hist_df.empty:
        st.info('저장된 Comment 이력이 없습니다.')
        return

    hist_df = hist_df.copy()
    hist_df['created_at'] = pd.to_datetime(hist_df['created_at'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    hist_df = hist_df.rename(
        columns={
            'created_at': '저장일시',
            'created_by': '작성자',
            'alarm_code': '알람코드',
            'alarm_name': '알람명',
            'comment_text': 'Comment',
        }
    )
    st.dataframe(hist_df[['저장일시', '작성자', '알람코드', '알람명', 'Comment']], use_container_width=True, hide_index=True)
