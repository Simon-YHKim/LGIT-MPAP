
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, timedelta
import io

import pandas as pd
import streamlit as st
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


from db import get_engine
from utils import (
    get_all_processes,
    get_team_process_ids,
    save_team_process_ids,
    ensure_team_process_filter_table,
)

st.set_page_config(page_title='Alarm Action List', layout='wide')

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

from ui.analytics import inject_tracker
inject_tracker(page_name="5_Alarm_Action_List", page_path="pages/5_Alarm_Action_List.py")

engine = get_engine()
ensure_team_process_filter_table(engine)

COMMENT_TABLE = 'mtba.alarm_comment_history'
TEAM_OPTIONS = ['전체', 'FOL팀', 'MOL팀', 'EOL팀']

# Vitals 팔레트 정렬
PRIMARY   = '#A50034'  # Vitals primary
PRIMARY_2 = '#7E0027'  # Vitals primary-dark
BG        = '#F7F8FA'  # Vitals page-bg
ROSE      = '#F8E5EC'  # Vitals primary-tint
BORDER    = '#E5E7EB'  # Vitals border
TEXT      = '#1F2430'  # Vitals ink-body
SUB       = '#6B7280'  # Vitals ink-muted
MUTED     = '#9CA3AF'  # Vitals ink-subtle
CARD_BG   = '#FFFFFF'  # Vitals card-bg

st.markdown(f"""
<style>
:root {{
    --primary:{PRIMARY}; --primary2:{PRIMARY_2}; --bg:{BG}; --rose:{ROSE};
    --border:{BORDER}; --text:{TEXT}; --sub:{SUB}; --muted:{MUTED}; --cardbg:{CARD_BG};
    /* Vitals 표준 토큰 alias — page 별 별칭과 양립 */
    --page-bg:{BG}; --card-bg:{CARD_BG}; --soft:#F1F3F5;
    --ink-body:{TEXT}; --ink-muted:{SUB};
    /* status 시맨틱 — 알람 액션 리스트의 처리상태 라벨에 사용 */
    --status-good:#1F8B4C; --status-warn:#B57F1B; --status-bad:#B23A48;
    --status-good-tint:#E6F4EA; --status-warn-tint:#FAF1DD; --status-bad-tint:#FDECEF;
}}
.action-status-good {{ color:var(--status-good); font-weight:700; }}
.action-status-warn {{ color:var(--status-warn); font-weight:700; }}
.action-status-bad  {{ color:var(--status-bad);  font-weight:700; }}
.stApp {{ background: linear-gradient(180deg,#fffdfd 0%, var(--bg) 100%); color: var(--text); }}
.block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}

.main-title {{
    background: linear-gradient(135deg, {PRIMARY_2} 0%, {PRIMARY} 100%);
    color: #fff;
    border-radius: 0;
    padding: 40px 28px 24px 28px;
    box-shadow: 0 10px 24px rgba(109,16,40,.18);
    margin: 0 0 14px 0;
    overflow: visible;
}}

.main-title h1 {{
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
}}

.main-title p {{
    margin: 8px 0 0 0;
    font-size: 13px;
    color: rgba(255,255,255,.92);
}}
.soft-card {{ border:1px solid var(--border); border-radius: 0; padding:12px 14px; background:rgba(255,255,255,.96); box-shadow:0 8px 18px rgba(109,16,40,.05); margin-bottom:10px; }}
.section-title {{ font-size:13px; font-weight:800; color:var(--primary); margin:0 0 8px 0; }}
.small-muted {{ color:var(--sub); font-size:12px; }}
.info-chip {{ display:inline-block; padding:6px 12px; border-radius:999px; background:var(--rose); color:var(--primary); font-size:12px; font-weight:800; margin-right:6px; margin-bottom:6px; border:1px solid var(--border); }}
.team-badge {{ display:inline-block; padding:4px 10px; border-radius:999px; background:#fff; color:var(--primary); border:1px solid var(--border); font-size:12px; font-weight:800; margin-left:8px; }}
.timeline-day {{ border:1px solid var(--border); border-radius: 0; padding:14px 16px; background:rgba(255,255,255,.96); box-shadow:0 8px 18px rgba(109,16,40,.05); margin-bottom:12px; }}
.timeline-day-header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }}
.timeline-date {{ font-size:20px; font-weight:900; color:var(--primary); }}
.timeline-stats {{ color:var(--sub); font-size:12px; }}
.comment-card {{ border:1px solid var(--border); border-radius:0; padding:12px 14px; background:var(--cardbg); margin-bottom:10px; box-shadow:0 4px 10px rgba(109,16,40,.04); }}
.comment-title {{ font-size:14px; font-weight:800; color:var(--primary); margin-bottom:6px; }}
.comment-meta {{ color:var(--sub); font-size:12px; margin-bottom:8px; }}
.comment-body {{ color:var(--text); font-size:13px; white-space:pre-wrap; line-height:1.5; background:#fff; border:1px solid #EFE4E8; border-radius:0; padding:10px 12px; }}
.proc-card-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:4px; }}
.proc-card-title {{ font-size:16px; font-weight:900; color:var(--primary); }}
.proc-card-sub {{ color:var(--sub); font-size:12px; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stDateInput > div > div, .stTextArea textarea {{ border-radius:0!important; border:1px solid var(--border) !important; box-shadow:none !important; background:#fff !important; }}
.stButton > button {{ border-radius:0!important; border:1px solid var(--border) !important; min-height:2.5rem; }}
button[kind="primary"] {{ background:linear-gradient(135deg,var(--primary) 0%, var(--primary2) 100%) !important; color:#fff !important; box-shadow:0 8px 16px rgba(109,16,40,.15) !important; }}
</style>
""", unsafe_allow_html=True)


def ensure_comment_table(engine):
    ddl = """
    CREATE SCHEMA IF NOT EXISTS mtba;
    CREATE TABLE IF NOT EXISTS mtba.alarm_comment_history (
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


def get_comment_date_range(engine):
    df = pd.read_sql(text(f"SELECT MIN(created_at::date) AS min_d, MAX(created_at::date) AS max_d FROM {COMMENT_TABLE}"), engine)
    if df.empty or pd.isna(df.loc[0, 'min_d']) or pd.isna(df.loc[0, 'max_d']):
        today = date.today()
        return today, today
    return pd.to_datetime(df.loc[0, 'min_d']).date(), pd.to_datetime(df.loc[0, 'max_d']).date()


def get_author_options(engine, start_date, end_date):
    sql = text(f"SELECT DISTINCT COALESCE(created_by, '-') AS created_by FROM {COMMENT_TABLE} WHERE created_at::date BETWEEN :s AND :e ORDER BY 1")
    df = pd.read_sql(sql, engine, params={'s': start_date, 'e': end_date})
    return df['created_by'].dropna().astype(str).tolist() if not df.empty else []


def get_alarm_code_options(engine, start_date, end_date):
    sql = text(f"SELECT DISTINCT COALESCE(alarm_code, '-') AS alarm_code FROM {COMMENT_TABLE} WHERE created_at::date BETWEEN :s AND :e ORDER BY 1")
    df = pd.read_sql(sql, engine, params={'s': start_date, 'e': end_date})
    return df['alarm_code'].dropna().astype(str).tolist() if not df.empty else []


def build_process_editor_df(engine, team_name: str) -> pd.DataFrame:
    all_process_df = get_all_processes(engine).copy()
    if all_process_df.empty:
        return pd.DataFrame(columns=['선택', '공정약어', '공정명', 'process_id'])
    all_process_df['process_id'] = all_process_df['process_id'].astype(int)
    all_process_df = all_process_df.sort_values(['process_name']).reset_index(drop=True)
    saved_ids = [] if team_name == '전체' else [int(x) for x in get_team_process_ids(engine, team_name)]
    return pd.DataFrame({
        '선택': all_process_df['process_id'].isin(saved_ids),
        '공정약어': all_process_df['process_short_name'].astype(str),
        '공정명': all_process_df['process_name'].astype(str),
        'process_id': all_process_df['process_id'].astype(int),
    })


def get_selected_process_ids_from_editor(editor_df: pd.DataFrame) -> list[int]:
    if editor_df is None or editor_df.empty or '선택' not in editor_df.columns:
        return []
    out = editor_df.loc[editor_df['선택'] == True, 'process_id'].tolist() if 'process_id' in editor_df.columns else []
    return [int(x) for x in out]


def get_team_badge_counts(engine) -> dict[str, int]:
    return {team: len([int(x) for x in get_team_process_ids(engine, team)]) for team in TEAM_OPTIONS if team != '전체'}


def load_action_list(engine, start_date, end_date, team_name, selected_process_ids, keyword='', authors=None, alarm_codes=None):
    all_process_df = get_all_processes(engine).copy()
    if not all_process_df.empty:
        all_process_df['process_id'] = all_process_df['process_id'].astype(int)
    selected_process_names = []
    if team_name != '전체' and selected_process_ids and not all_process_df.empty:
        selected_process_names = all_process_df.loc[all_process_df['process_id'].isin(selected_process_ids), 'process_name'].dropna().astype(str).tolist()

    where = ["created_at::date BETWEEN :start_date AND :end_date"]
    params = {'start_date': start_date, 'end_date': end_date}

    if team_name != '전체' and selected_process_names:
        where.append("process_name = ANY(:process_names)")
        params['process_names'] = selected_process_names
    elif team_name != '전체' and not selected_process_ids:
        where.append("1=0")

    kw = (keyword or '').strip()
    if kw:
        where.append("(COALESCE(alarm_name,'') ILIKE :kw OR COALESCE(alarm_code,'') ILIKE :kw OR COALESCE(comment_text,'') ILIKE :kw OR COALESCE(equipment_name,'') ILIKE :kw OR COALESCE(equipment_no,'') ILIKE :kw)")
        params['kw'] = f"%{kw}%"

    authors = [str(x) for x in (authors or []) if str(x).strip()]
    if authors:
        where.append("COALESCE(created_by, '-') = ANY(:authors)")
        params['authors'] = authors

    alarm_codes = [str(x) for x in (alarm_codes or []) if str(x).strip()]
    if alarm_codes:
        where.append("COALESCE(alarm_code, '-') = ANY(:alarm_codes)")
        params['alarm_codes'] = alarm_codes

    sql = text(f"""
        SELECT
            id,
            created_at,
            created_at::date AS written_date,
            COALESCE(created_by, '-') AS written_by,
            COALESCE(model_name, '-') AS model_name,
            COALESCE(process_name, '-') AS process_name,
            COALESCE(equipment_name, '-') AS equipment_name,
            COALESCE(equipment_no, '-') AS equipment_no,
            COALESCE(alarm_code, '-') AS alarm_code,
            COALESCE(alarm_name, '-') AS alarm_name,
            COALESCE(comment_text, '') AS comment_text,
            COALESCE(popup_scope, '-') AS popup_scope,
            COALESCE(segment_name, '-') AS segment_name,
            base_date AS base_date
        FROM {COMMENT_TABLE}
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC, id DESC
    """)
    return pd.read_sql(sql, engine, params=params)


def update_comment(engine, row_id: int, new_text: str, new_author: str):
    sql = text(f"UPDATE {COMMENT_TABLE} SET comment_text=:comment_text, created_by=:created_by WHERE id=:id")
    with engine.begin() as conn:
        conn.execute(sql, {'id': int(row_id), 'comment_text': new_text.strip(), 'created_by': (new_author or '').strip() or None})


def delete_comment(engine, row_id: int):
    sql = text(f"DELETE FROM {COMMENT_TABLE} WHERE id=:id")
    with engine.begin() as conn:
        conn.execute(sql, {'id': int(row_id)})


def rename_display(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={
        'created_at': '작성일시',
        'written_date': '작성일',
        'written_by': '작성자',
        'model_name': '모델',
        'process_name': '공정',
        'equipment_name': '설비명',
        'equipment_no': '호기',
        'alarm_code': '알람코드',
        'alarm_name': '알람명',
        'comment_text': 'Comment',
        'popup_scope': 'Scope',
        'segment_name': '세그먼트',
        'base_date': '기준일',
    }).copy()
    if '작성일시' in out.columns:
        out['작성일시'] = pd.to_datetime(out['작성일시'], errors='coerce')
    if '작성일' in out.columns:
        out['작성일'] = pd.to_datetime(out['작성일'], errors='coerce').dt.date
    return out


def render_timeline_cards(display_df: pd.DataFrame):
    st.markdown('### 날짜별 타임라인 카드 보기')
    days = sorted(display_df['작성일'].dropna().unique().tolist(), reverse=True)
    for day in days:
        day_df = display_df[display_df['작성일'] == day].copy().sort_values('작성일시', ascending=False)
        comment_cnt = len(day_df)
        proc_cnt = day_df['공정'].nunique() if '공정' in day_df.columns else 0
        alarm_cnt = day_df['알람명'].nunique() if '알람명' in day_df.columns else 0
        st.markdown(f"<div class='timeline-day'><div class='timeline-day-header'><div class='timeline-date'>{day}</div><div class='timeline-stats'>Comment {comment_cnt}건 · 공정 {proc_cnt}개 · 알람 {alarm_cnt}개</div></div>", unsafe_allow_html=True)

        for row in day_df.to_dict('records'):
            rid = int(row['id'])
            title = f"[{row.get('알람코드','-')}] {row.get('알람명','-')}"
            dt_text = pd.to_datetime(row.get('작성일시')).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row.get('작성일시')) else '-'
            meta = f"작성일시: {dt_text} | 작성자: {row.get('작성자','-')} | 모델: {row.get('모델','-')} | 공정: {row.get('공정','-')} | 설비: {row.get('설비명','-')} | 호기: {row.get('호기','-')} | Scope: {row.get('Scope','-')} | 세그먼트: {row.get('세그먼트','-')}"
            body = str(row.get('Comment','')).replace('<','&lt;').replace('>','&gt;')
            st.markdown(f"<div class='comment-card'><div class='comment-title'>{title}</div><div class='comment-meta'>{meta}</div><div class='comment-body'>{body}</div></div>", unsafe_allow_html=True)

            act1, act2, act3 = st.columns([0.9, 0.9, 4.2])
            with act1:
                if st.button('수정', key=f'edit_btn_{rid}', use_container_width=True):
                    st.session_state['editing_comment_id'] = rid
                    st.session_state[f'editing_comment_text_{rid}'] = str(row.get('Comment', ''))
                    st.session_state[f'editing_comment_author_{rid}'] = str(row.get('작성자', '-'))
                    st.rerun()
            with act2:
                if st.button('삭제', key=f'del_btn_{rid}', use_container_width=True):
                    st.session_state['delete_comment_id'] = rid
                    st.rerun()

            if st.session_state.get('editing_comment_id') == rid:
                st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
                new_author = st.text_input('작성자', key=f'editing_comment_author_{rid}')
                new_text = st.text_area('Comment 수정', key=f'editing_comment_text_{rid}', height=140)
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button('수정 저장', key=f'save_edit_{rid}', type='primary', use_container_width=True):
                        update_comment(engine, rid, new_text, new_author)
                        st.success('Comment가 수정되었습니다.')
                        st.session_state.pop('editing_comment_id', None)
                        st.rerun()
                with c2:
                    if st.button('수정 취소', key=f'cancel_edit_{rid}', use_container_width=True):
                        st.session_state.pop('editing_comment_id', None)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get('delete_comment_id') == rid:
                st.warning('정말 이 Comment를 삭제하시겠습니까?')
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button('삭제 확인', key=f'confirm_del_{rid}', type='primary', use_container_width=True):
                        delete_comment(engine, rid)
                        st.success('Comment가 삭제되었습니다.')
                        st.session_state.pop('delete_comment_id', None)
                        st.rerun()
                with c2:
                    if st.button('삭제 취소', key=f'cancel_del_{rid}', use_container_width=True):
                        st.session_state.pop('delete_comment_id', None)
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


ensure_comment_table(engine)
all_min_date, all_max_date = get_comment_date_range(engine)
if 'aal_team' not in st.session_state:
    st.session_state.aal_team = '전체'
if 'aal_period' not in st.session_state:
    default_start = max(all_min_date, all_max_date - timedelta(days=6))
    st.session_state.aal_period = (default_start, all_max_date)

# preview sec-alarm 와 동일 — vit-top-strip 6px wine + flat 페이지 타이틀.
from ui.vitals.components import render_top_strip, render_sub_head
render_top_strip()
st.markdown(
    '<div class="board-top-title vit-page-head" '
    'style="font-family:\'LG EI Headline\',\'LG EI Text\',sans-serif;'
    'font-size:28px;font-weight:700;color:var(--ink-body,#1F2430);'
    'letter-spacing:-0.02em;margin:0 0 6px;'
    'border-bottom:1px solid var(--border,#E5E7EB);padding-bottom:8px;">'
    'Alarm Action List · 알람 액션 이력</div>',
    unsafe_allow_html=True,
)

st.markdown("""
<div class='soft-card'>
  <div class='section-title'>사용 방법</div>
  <div class='small-muted'>선택한 팀에 따라 공정 선택 카드 제목과 저장 버튼 문구가 동적으로 바뀌며, 팀별 저장 공정 수 배지가 함께 표시됩니다.</div>
</div>
""", unsafe_allow_html=True)

# 상단 조회 영역
team_col, period_col, keyword_col = st.columns([1.0, 1.6, 1.4])
with team_col:
    team_name = st.selectbox('팀 선택', TEAM_OPTIONS, key='aal_team')
with period_col:
    period = st.date_input('기간 선택', min_value=all_min_date, max_value=all_max_date, key='aal_period')
    if isinstance(period, (tuple, list)) and len(period) == 2:
        start_date, end_date = period[0], period[1]
    else:
        start_date, end_date = period, period
with keyword_col:
    keyword = st.text_input('검색어', value='', placeholder='알람명 / 알람코드 / Comment / 설비명 / 호기')

selected_process_ids = []
all_process_df = get_all_processes(engine).copy()
process_label_map = {}
if not all_process_df.empty:
    all_process_df['process_id'] = all_process_df['process_id'].astype(int)
    process_label_map = {
        int(row['process_id']): f"{row['process_short_name']} ({row['process_name']})"
        for _, row in all_process_df.sort_values(['process_name']).iterrows()
    }
team_badge_counts = get_team_badge_counts(engine)

if team_name != '전체':
    header_team_name = team_name.replace('팀', '').strip() or team_name
    badge_count = team_badge_counts.get(team_name, 0)
    with st.expander(f"{header_team_name} 팀 공정 선택 · 저장 {badge_count}개", expanded=True):
        st.markdown(
            f"<div class='proc-card-head'><div class='proc-card-title'>{header_team_name} 팀 공정 선택<span class='team-badge'>저장 {badge_count}개</span></div><div class='proc-card-sub'>체크된 공정만 {team_name}에 저장됩니다.</div></div>",
            unsafe_allow_html=True,
        )
        process_editor_df = build_process_editor_df(engine, team_name)
        edited_df = st.data_editor(
            process_editor_df,
            use_container_width=True,
            hide_index=True,
            num_rows='fixed',
            disabled=['공정약어', '공정명', 'process_id'],
            column_config={
                '선택': st.column_config.CheckboxColumn('선택', help='체크된 공정이 선택한 팀 공정으로 저장됩니다.'),
                '공정약어': st.column_config.TextColumn('공정약어'),
                '공정명': st.column_config.TextColumn('공정명'),
                'process_id': None,
            },
            key=f'aal_proc_editor_{team_name}',
        )
        selected_process_ids = get_selected_process_ids_from_editor(edited_df)

        btn1, btn2, btn3 = st.columns([1.2, 1.0, 2.3])
        dynamic_save_label = f"{header_team_name} 팀 공정 저장"
        with btn1:
            if st.button(dynamic_save_label, type='primary', use_container_width=True):
                save_team_process_ids(engine, team_name, selected_process_ids)
                st.success(f'[{team_name}] 팀 공정 목록이 저장되었습니다.')
                st.rerun()
        with btn2:
            if st.button('저장값 다시 불러오기', use_container_width=True):
                st.rerun()
        with btn3:
            current_saved = [int(x) for x in get_team_process_ids(engine, team_name)]
            if not current_saved:
                st.warning(f'[{team_name}] 저장된 팀 공정 목록이 없습니다. 체크 후 저장해 주세요.')
else:
    st.info("현재 '전체' 팀이 선택되어 있어 팀 공정 선택 UI를 숨깁니다.")

# 추가 필터
author_options = get_author_options(engine, start_date, end_date)
alarm_code_options = get_alarm_code_options(engine, start_date, end_date)
filter1, filter2 = st.columns([1.2, 1.2])
with filter1:
    selected_authors = st.multiselect('작성자 필터', author_options, default=[])
with filter2:
    selected_alarm_codes = st.multiselect('알람코드 필터', alarm_code_options, default=[])

# 저장된 팀 공정 목록 + 배지
render_sub_head("저장된 팀 공정 목록", "현재 팀에 저장된 공정")
chips = []
for team in [t for t in TEAM_OPTIONS if t != '전체']:
    saved_ids = [int(x) for x in get_team_process_ids(engine, team)]
    labels = [process_label_map[pid] for pid in saved_ids if pid in process_label_map]
    chips.append(f"<span class='info-chip'>{team} ({len(saved_ids)}개) : {', '.join(labels) if labels else '-'}</span>")
st.markdown(''.join(chips), unsafe_allow_html=True)

# 조회
result_df = load_action_list(engine, start_date, end_date, team_name, selected_process_ids, keyword, selected_authors, selected_alarm_codes)
metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric('총 Comment 건수', f"{len(result_df):,}")
metric2.metric('조회 시작일', str(start_date))
metric3.metric('조회 종료일', str(end_date))
metric4.metric('팀', team_name)

if result_df.empty:
    st.info('선택한 조건에 해당하는 Comment 이력이 없습니다.')
    st.stop()

display_df = rename_display(result_df)

# CSV 다운로드
csv_buf = io.StringIO()
display_df.to_csv(csv_buf, index=False, encoding='utf-8-sig')
st.download_button('CSV 다운로드', data=csv_buf.getvalue(), file_name='alarm_action_list.csv', mime='text/csv')

# 날짜별 요약
render_sub_head("날짜별 요약", "선택 기간의 알람 코멘트 추이")
summary_df = (
    display_df.assign(작성일=pd.to_datetime(display_df['작성일']).dt.date)
    .groupby('작성일', as_index=False)
    .agg(Comment건수=('id', 'count'), 공정수=('공정', lambda s: int(pd.Series(s).nunique())), 알람수=('알람명', lambda s: int(pd.Series(s).nunique())))
    .sort_values('작성일', ascending=False)
)
st.dataframe(summary_df, use_container_width=True, hide_index=True)

# 타임라인 카드형 보기
render_timeline_cards(display_df.copy())

# 전체 이력 테이블
render_sub_head("전체 이력 (최신순)", "선택 기간 · 팀의 알람 코멘트 전수")
full_df = display_df.copy()
full_df['작성일시'] = pd.to_datetime(full_df['작성일시']).dt.strftime('%Y-%m-%d %H:%M:%S')
cols = ['작성일시', '작성자', '모델', '공정', '설비명', '호기', '알람코드', '알람명', 'Comment', 'Scope', '세그먼트', '기준일']
safe_cols = [c for c in cols if c in full_df.columns]
st.dataframe(full_df[safe_cols], use_container_width=True, hide_index=True)
