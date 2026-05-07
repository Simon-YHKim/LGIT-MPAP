from pathlib import Path
from datetime import timedelta
from html import escape
from textwrap import dedent
import time

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from PIL import Image
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

# AgGrid
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
    AGGRID_AVAILABLE = True
except Exception:
    AGGRID_AVAILABLE = False

from db import get_engine
from utils import (
    get_models,
    get_date_range,
    get_all_processes,
    get_team_process_ids,
    save_team_process_ids,
    ensure_team_process_filter_table,

    get_period_compare_by_process,
    make_mtba_process_bar_chart,
    get_process_summary,

    get_process_week_status,
    get_process_best_worst_snapshot,
    get_best_worst_alarm_top5_by_worst,

    ensure_alarm_annotation_table,
    get_alarm_annotation,
    upsert_alarm_annotation,
)

st.set_page_config(page_title="MTBA Dashboard", layout="wide")

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

engine = get_engine()
ensure_team_process_filter_table(engine)
ensure_alarm_annotation_table(engine)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Vitals 팔레트 정렬 — legacy 변수명 보존, 값만 통일 → 모든 CSS 자동 와인+모노톤
PRIMARY     = "#A50034"  # Vitals primary
PRIMARY_2   = "#7E0027"  # Vitals primary-dark
BG          = "#F7F8FA"  # Vitals page-bg (legacy 핑크-회색 → cool 회백)
CARD        = "#FFFFFF"  # Vitals card-bg
ROSE        = "#F8E5EC"  # Vitals primary-tint
MIST        = "#F1F3F5"  # Vitals soft
BORDER      = "#E5E7EB"  # Vitals border
TEXT        = "#1F2430"  # Vitals ink-body
SUB         = "#6B7280"  # Vitals ink-muted
PASTEL_RED  = "#FDECEF"  # Vitals bad-tint
PASTEL_BLUE = "#E6F4EA"  # Vitals good-tint (legacy '블루' → 그린-tint, 신호등 의미)
COMMENT_TABLE = "mtba.alarm_comment_history"

PAGE_STYLE = f"""
<style>
    .stApp {{ background: {BG}; color: {TEXT}; }}
    .block-container {{ padding-top: 1rem; padding-bottom: 2rem; }}
    .page-banner {{
    background: linear-gradient(135deg, {PRIMARY_2} 0%, {PRIMARY} 100%);
    color: #fff;
    border-radius: 12px;
    padding: 40px 28px 24px 28px;
    box-shadow: 0 10px 24px rgba(165,0,52,.18);
    margin: 0 0 14px 0;
    overflow: visible;
    font-family: var(--font-display, var(--font-body));
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.025em;
}}
    .page-subtitle {{ color: {SUB}; font-size: 13px; margin: 4px 2px 18px 4px; }}
    .soft-card {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 14px 16px; box-shadow: 0 6px 18px rgba(109,16,40,.05);
    }}
    .section-title {{ font-size: 22px; font-weight: 800; color: {PRIMARY}; margin: 2px 0 8px 0; }}
    .muted-note {{ color: {SUB}; font-size: 12px; }}
    div[data-testid="stMetric"] {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 18px; padding: 10px 12px;
    }}
    div[data-testid="stExpander"] > details {{
        background: {CARD}; border: 1px solid {BORDER}; border-radius: 18px; overflow: hidden;
    }}
    div[data-testid="stExpander"] > details > summary {{
        background: linear-gradient(180deg, {ROSE}, #FFFDFE); color: {PRIMARY}; font-weight: 800;
    }}
</style>
"""

_ensure_alarm_comment_history_table_sql = f"""
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
    for stmt in [s.strip() for s in _ensure_alarm_comment_history_table_sql.split(";") if s.strip()]:
        conn.execute(text(stmt))

# PERF #7 — PAGE_STYLE 매 rerun 재방출 회피
if not st.session_state.get("_mtba_dashboard_page_style_applied"):
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    st.session_state["_mtba_dashboard_page_style_applied"] = True
st.markdown("<div class='page-banner'>MTBA Dashboard</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='page-subtitle'>선택한 기간 기준으로 기간별 MTBA / 공정 통계 / 클릭 Drill-down 기반 MTBA 현황 / Alarm 차이 분석</div>",
    unsafe_allow_html=True
)


# =========================================================
# 카드 / 표 높이 설정
# =========================================================
SIGNAL_CARD_HEIGHT = 245
SNAPSHOT_CARD_HEIGHT = 215
LEFT_CARD_OVERLAP = 12                 # 카드 간 여백 제거용
RIGHT_SECTION_TITLE_SPACE = 54         # 오른쪽 제목+caption 영역
ALARM_GRID_HEIGHT = SIGNAL_CARD_HEIGHT + SNAPSHOT_CARD_HEIGHT - LEFT_CARD_OVERLAP - RIGHT_SECTION_TITLE_SPACE


# =========================================================
# 패널 상태 관리
# =========================================================
if "panel_ids" not in st.session_state:
    st.session_state.panel_ids = [1]

if "next_panel_id" not in st.session_state:
    st.session_state.next_panel_id = 2

if "active_alarm_popup" not in st.session_state:
    st.session_state.active_alarm_popup = None

if "active_alarm_popup_event_id" not in st.session_state:
    st.session_state.active_alarm_popup_event_id = None

if "dashboard_last_alarm_click" not in st.session_state:
    st.session_state.dashboard_last_alarm_click = {}

if "active_alarm_popup_event_id" not in st.session_state:
    st.session_state.active_alarm_popup_event_id = None

def insert_panel_after(current_panel_id: int):
    panel_ids = st.session_state.panel_ids[:]
    idx = panel_ids.index(current_panel_id)
    new_id = st.session_state.next_panel_id
    st.session_state.next_panel_id += 1
    panel_ids.insert(idx + 1, new_id)
    st.session_state.panel_ids = panel_ids


def remove_panel(current_panel_id: int):
    panel_ids = st.session_state.panel_ids[:]
    if len(panel_ids) <= 1:
        return
    panel_ids.remove(current_panel_id)
    st.session_state.panel_ids = panel_ids


# =========================================================
# 기본 조회
# =========================================================
TEAM_OPTIONS = ["전체", "FOL팀", "MOL팀", "EOL팀"]

models_df = get_models(engine)
model_options = dict(zip(models_df["model_name"], models_df["model_id"]))

all_process_df = get_all_processes(engine).copy()
if all_process_df.empty:
    st.error("dim_process에 공정 데이터가 없습니다. ETL 적재 상태를 확인해주세요.")
    st.stop()

all_process_df["process_id"] = all_process_df["process_id"].astype(int)
all_process_df = all_process_df.sort_values(["process_name"]).reset_index(drop=True)

process_label_map = {
    int(row["process_id"]): f'{row["process_short_name"]} ({row["process_name"]})'
    for _, row in all_process_df.iterrows()
}

min_date, max_date = get_date_range(engine)
if min_date is None or max_date is None:
    st.error("DB에 조회 가능한 날짜 데이터가 없습니다. ETL 적재 상태를 확인해주세요.")
    st.stop()


# =========================================================
# 공통 helper
# =========================================================
def get_default_this_week_range(min_date, max_date):
    today = pd.Timestamp.today().date()
    default_end = min(today, max_date)

    this_monday = default_end - timedelta(days=default_end.weekday())
    default_start = max(min_date, this_monday)

    return default_start, default_end


def format_selected_period(start_date, end_date) -> str:
    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")
    return start_str if start_str == end_str else f"{start_str} ~ {end_str}"


def get_saved_team_process_ids(team_name: str):
    if team_name == "전체":
        return []
    return [int(x) for x in get_team_process_ids(engine, team_name)]


def get_display_process_names_from_ids(process_ids):
    if not process_ids:
        return []
    return all_process_df.loc[
        all_process_df["process_id"].isin(process_ids),
        "process_short_name"
    ].tolist()


def normalize_aggrid_selected_rows(selected_rows):
    if selected_rows is None:
        return []

    if isinstance(selected_rows, pd.DataFrame):
        if selected_rows.empty:
            return []
        return selected_rows.to_dict("records")

    if isinstance(selected_rows, list):
        return selected_rows

    return []


# -------------------------------
# 선택 공정 상태 (single source of truth)
# -------------------------------
def get_selected_processes(panel_id: int) -> list:
    return st.session_state.get(f"selected_processes_{panel_id}", [])


def get_summary_editor_version(panel_id: int) -> int:
    return st.session_state.get(f"summary_editor_version_{panel_id}", 0)


def bump_summary_editor_version(panel_id: int):
    st.session_state[f"summary_editor_version_{panel_id}"] = get_summary_editor_version(panel_id) + 1


def get_chart_version(panel_id: int) -> int:
    return st.session_state.get(f"chart_version_{panel_id}", 0)


def bump_chart_version(panel_id: int):
    st.session_state[f"chart_version_{panel_id}"] = get_chart_version(panel_id) + 1


def get_alarm_grid_version(panel_id: int) -> int:
    return st.session_state.get(f"alarm_grid_version_{panel_id}", 0)


def bump_alarm_grid_version(panel_id: int):
    st.session_state[f"alarm_grid_version_{panel_id}"] = get_alarm_grid_version(panel_id) + 1


def reset_summary_editor_state(panel_id: int):
    bump_summary_editor_version(panel_id)


def reset_chart_state(panel_id: int):
    bump_chart_version(panel_id)


def set_selected_processes(panel_id: int, process_names: list, source: str = "unknown") -> bool:
    """
    그래프/요약표가 공유하는 공정 선택 상태
    - 전체 평균 제외
    - 최대 5개
    - 변경 시 True 반환
    """
    deduped = []
    seen = set()

    for p in process_names:
        if not p or p == "전체 평균":
            continue
        if p not in seen:
            deduped.append(p)
            seen.add(p)

    if len(deduped) > 5:
        deduped = deduped[:5]
        st.warning("공정은 최대 5개까지 선택할 수 있습니다. 처음 5개만 반영합니다.")

    key = f"selected_processes_{panel_id}"
    current = st.session_state.get(key, [])

    if current != deduped:
        st.session_state[key] = deduped
        st.session_state[f"scroll_to_mtba_{panel_id}"] = True

        if source == "chart":
            reset_summary_editor_state(panel_id)
            st.session_state[f"skip_table_apply_once_{panel_id}"] = True

        if source == "table":
            reset_chart_state(panel_id)

        if source == "clear":
            reset_summary_editor_state(panel_id)
            reset_chart_state(panel_id)
            st.session_state[f"skip_table_apply_once_{panel_id}"] = True

        # 다른 작업으로 popup 뜨는 문제 방지
        st.session_state.active_alarm_popup = None
        st.session_state.active_alarm_popup_event_id = None

        return True

    return False


# =========================================================
# Alarm Annotation Popup
# =========================================================
def render_alarm_annotation_editor(alarm_code, alarm_name, panel_id, save_button_label="저장", save_button_key=None, close_after_save=False):
    existing = get_alarm_annotation(engine, alarm_code, alarm_name)

    default_text = ""
    existing_image_path = None
    existing_image_name = None

    if existing:
        default_text = existing.get("note_text") or ""
        existing_image_path = existing.get("image_path")
        existing_image_name = existing.get("image_name")

    note_key = f"alarm_note_text_{panel_id}_{alarm_code}_{alarm_name}"
    if note_key not in st.session_state:
        st.session_state[note_key] = default_text

    st.text_area("Text 내용", key=note_key, height=220)

    if existing_image_path:
        st.markdown("#### 기존 저장 이미지")
        if Path(existing_image_path).exists():
            st.image(existing_image_path, caption=existing_image_name or "기존 저장 이미지")
        else:
            st.warning("기존 저장 이미지 경로는 있으나 실제 파일을 찾을 수 없습니다.")

    uploaded_file = st.file_uploader(
        "새 이미지 업로드 (업로드 시 기존 이미지 대체)",
        type=["png", "jpg", "jpeg", "bmp"],
        key=f"alarm_note_upload_{panel_id}_{alarm_code}_{alarm_name}",
    )

    if uploaded_file is not None:
        st.markdown("#### 새 업로드 이미지 미리보기")
        st.image(uploaded_file, caption=uploaded_file.name)

    save_key = save_button_key or f"save_alarm_annotation_{panel_id}_{alarm_code}_{alarm_name}"
    if st.button(save_button_label, key=save_key, use_container_width=True):
        upsert_alarm_annotation(
            engine=engine,
            alarm_code=alarm_code,
            alarm_name=alarm_name,
            note_text=st.session_state.get(note_key, ""),
            uploaded_file=uploaded_file,
        )
        st.success("저장되었습니다.")
        if close_after_save:
            st.session_state.active_alarm_popup = None
            st.session_state.active_alarm_popup_event_id = None
            st.session_state.dashboard_last_alarm_click.pop(str(panel_id), None)
            bump_alarm_grid_version(panel_id)
        st.rerun()


def insert_alarm_comment(payload):
    sql = text(f"""
        INSERT INTO mtba.alarm_comment_history
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


def load_alarm_comment_history(popup_payload, alarm_name, alarm_code=None, limit=100):
    params = {
        "popup_scope": str(popup_payload.get("popup_scope", "standard")),
        "equipment_id": popup_payload.get("equipment_id"),
        "base_date": popup_payload.get("base_date"),
        "alarm_name": alarm_name,
        "alarm_code": alarm_code,
        "process_name": popup_payload.get("process_name"),
        "equipment_name": popup_payload.get("equipment_name"),
        "equipment_no": popup_payload.get("equipment_no"),
        "limit": int(limit),
    }

    where_sql = [
        "popup_scope = :popup_scope",
        "base_date = :base_date",
        "alarm_name = :alarm_name",
    ]

    # Detail View standard popup과 동일하게 equipment_id 기준으로 맞춤
    if popup_payload.get("equipment_id") is not None:
        where_sql.append("COALESCE(equipment_id,-1) = COALESCE(:equipment_id,-1)")
    else:
        where_sql.extend([
            "COALESCE(process_name,'') = COALESCE(:process_name,'')",
            "COALESCE(equipment_name,'') = COALESCE(:equipment_name,'')",
            "COALESCE(equipment_no,'') = COALESCE(:equipment_no,'')",
        ])

    if alarm_code:
        where_sql.append("COALESCE(alarm_code,'') = COALESCE(:alarm_code,'')")

    sql = text(f"""
        SELECT
            id,
            created_at,
            COALESCE(created_by,'-') AS created_by,
            COALESCE(alarm_code,'-') AS alarm_code,
            alarm_name,
            comment_text
        FROM mtba.alarm_comment_history
        WHERE {' AND '.join(where_sql)}
        ORDER BY created_at DESC, id DESC
        LIMIT :limit
    """)
    return pd.read_sql(sql, engine, params=params)


def render_dashboard_comment_section(payload, panel_id):
    rows = payload.get("rows", []) or []
    if not rows:
        st.info("Comment를 남길 알람 정보가 없습니다.")
        return

    alarm_options = []
    option_map = {}
    for r in rows:
        code = str(r.get("alarm_code") or "").strip()
        name = str(r.get("alarm_name") or "").strip()
        label = f"[{code}] {name}" if code else name
        if label not in option_map:
            alarm_options.append(label)
            option_map[label] = {"alarm_code": code, "alarm_name": name}

    st.markdown("### Comment 입력")
    selected_label = st.selectbox(
        "알람 선택",
        alarm_options,
        key=f"dashboard_comment_alarm_select_{panel_id}",
    )
    selected_alarm = option_map[selected_label]

    text_key = f"dashboard_comment_text_{panel_id}_{selected_alarm['alarm_name']}"
    if text_key not in st.session_state:
        st.session_state[text_key] = ""

    st.text_area(
        "Comment",
        key=text_key,
        height=120,
        placeholder="알람 원인, 조치 내용, 재발 방지 대책 등을 입력하세요.",
    )

    # 버튼 텍스트 줄바꿈 방지 및 버튼 높이/글자 크기 확대

    st.markdown(
        """
        <style>
        div.stButton > button {
            white-space: nowrap !important;
            min-height: 46px !important;
            font-size: 15px !important;
            font-weight: 700 !important;
            padding-left: 14px !important;
            padding-right: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    history_key = f"dashboard_comment_history_open_{panel_id}_{selected_alarm['alarm_name']}"

    btn_col1, btn_col2, _blank = st.columns([2.5, 2.5, 2])

    with btn_col1:
        save_clicked = st.button(
            "Comment 저장",
            key=f"dashboard_comment_save_{panel_id}",
            type="primary",
            use_container_width=True,
        )

    with btn_col2:
        history_clicked = st.button(
            "이력 조회",
            key=f"dashboard_comment_history_btn_{panel_id}",
            use_container_width=True,
        )

    if history_clicked:
        st.session_state[history_key] = True

    if save_clicked:
        text_value = (st.session_state.get(text_key) or "").strip()
        if not text_value:
            st.warning("저장할 Comment 내용을 입력해 주세요.")
        else:
            insert_alarm_comment({
                "popup_scope": payload.get("popup_scope", "standard"),
                "equipment_id": payload.get("equipment_id"),
                "segment_name": None,
                "base_date": payload.get("base_date"),
                "alarm_code": selected_alarm["alarm_code"] or None,
                "alarm_name": selected_alarm["alarm_name"],
                "model_name": payload.get("model_name"),
                "process_name": payload.get("process_name"),
                "equipment_name": payload.get("equipment_name"),
                "equipment_no": payload.get("equipment_no"),
                "comment_text": text_value,
                "created_by": st.session_state.get("user_name", None),
            })
            # text_area 위젯 생성 후에는 같은 run에서 st.session_state[text_key]를 직접 수정하지 않음
            # rerun하지 않고 같은 dialog 안에서 저장 성공/이력 표시만 수행해 팝업 안정성을 높임
            st.session_state[history_key] = True
            st.success("Comment가 저장되었습니다.")

    if st.session_state.get(history_key, False):
        st.markdown("#### Comment 이력")
        hist_df = load_alarm_comment_history(
            payload,
            selected_alarm["alarm_name"],
            selected_alarm["alarm_code"],
            limit=100,
        )
        if hist_df.empty:
            st.info("저장된 Comment 이력이 없습니다.")
        else:
            hist_df = hist_df.copy()
            hist_df["created_at"] = pd.to_datetime(hist_df["created_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            hist_df = hist_df.rename(columns={
                "created_at": "저장일시",
                "created_by": "작성자",
                "alarm_code": "알람코드",
                "alarm_name": "알람명",
                "comment_text": "Comment",
            })
            st.dataframe(
                hist_df[["저장일시", "작성자", "알람코드", "알람명", "Comment"]],
                use_container_width=True,
                hide_index=True,
            )


def render_dashboard_snapshot_table(payload):
    snapshot_rows = payload.get("snapshot_rows", []) or []
    if not snapshot_rows:
        return

    snap_df = pd.DataFrame(snapshot_rows)
    keep_cols = [c for c in ["구분", "호기", "Runtime(분)", "알람 횟수", "MTBA"] if c in snap_df.columns]
    if keep_cols:
        st.markdown("### Best / Worst 호기 요약")
        st.dataframe(snap_df[keep_cols], use_container_width=True, hide_index=True)


def render_dashboard_compare_table(payload):
    row = payload.get("selected_row", {}) or {}

    def _to_float(v, default=0.0):
        try:
            return float(v if v is not None else default)
        except Exception:
            return float(default)

    compare_df = pd.DataFrame([
        {
            "구분": str(payload.get("worst_eq_name") or "Worst"),
            "알람수": int(round(_to_float(row.get("worst_count", 0)))),
            "알람율(%)": f"{_to_float(row.get('worst_alarm_rate_pct', 0)):.1f}%",
            "점유율(%)": f"{_to_float(row.get('worst_share_pct', 0)):.0f}%",
        },
        {
            "구분": str(payload.get("best_eq_name") or "Best"),
            "알람수": int(round(_to_float(row.get("best_count", 0)))),
            "알람율(%)": f"{_to_float(row.get('best_alarm_rate_pct', 0)):.1f}%",
            "점유율(%)": f"{_to_float(row.get('best_share_pct', 0)):.0f}%",
        },
    ])

    st.markdown("### 선택 알람 비교")
    st.dataframe(compare_df, use_container_width=True, hide_index=True)


@st.dialog("Alarm 메모 / 이미지")
def alarm_annotation_dialog(alarm_code, alarm_name, panel_id):
    st.markdown(f"### 알람코드: `{alarm_code}`")
    st.markdown(f"### 알람명: `{alarm_name}`")
    render_alarm_annotation_editor(alarm_code, alarm_name, panel_id)

    if st.button(
        "닫기",
        key=f"close_alarm_annotation_{panel_id}_{alarm_code}_{alarm_name}",
        use_container_width=True
    ):
        st.session_state.active_alarm_popup = None
        st.session_state.active_alarm_popup_event_id = None
        st.session_state.dashboard_last_alarm_click.pop(str(panel_id), None)
        bump_alarm_grid_version(panel_id)
        st.rerun()




def render_fast_dialog_close_button(button_text="팝업 닫기"):
    """Streamlit dialog의 우측 상단 X 버튼을 JS로 클릭해 즉시 닫는 버튼.
    서버 rerun 없이 클라이언트에서 dialog만 닫아 기존 Dashboard 화면을 유지한다.
    """
    components.html(f"""
    <button id="fastCloseDialogBtn" style="
        width:100%;
        height:46px;
        border:0;
        border-radius:10px;
        background:#A50034;
        color:white;
        font-weight:800;
        font-size:15px;
        cursor:pointer;
        white-space:nowrap;
    ">{escape(str(button_text))}</button>
    <script>
    const btn = document.getElementById('fastCloseDialogBtn');
    btn.addEventListener('click', function() {{
        const doc = window.parent.document;
        const buttons = Array.from(doc.querySelectorAll('button'));
        const closeBtn = buttons.find(function(b) {{
            const label = (b.getAttribute('aria-label') || '').toLowerCase();
            const title = (b.getAttribute('title') || '').toLowerCase();
            const txt = (b.innerText || '').trim();
            return label.includes('close') || title.includes('close') || txt === '×' || txt === '✕';
        }});
        if (closeBtn) {{
            closeBtn.click();
        }} else {{
            doc.dispatchEvent(new KeyboardEvent('keydown', {{key:'Escape', code:'Escape', keyCode:27, which:27, bubbles:true}}));
        }}
    }});
    </script>
    """, height=58)

@st.dialog("상세 정보")
def dashboard_alarm_detail_dialog(payload, panel_id):
    """경량화 팝업: 헤더/선택 알람 비교 우선, Snapshot/Comment 이력은 expander."""
    alarm_code = str(payload.get("alarm_code") or "")
    alarm_name = str(payload.get("alarm_name") or "-")
    process_name = str(payload.get("process_name") or "-")

    start_date = pd.to_datetime(payload.get("start_date"), errors="coerce")
    end_date = pd.to_datetime(payload.get("end_date"), errors="coerce")
    if pd.isna(start_date) and pd.isna(end_date):
        period_text = "-"
    else:
        s = start_date.strftime("%Y-%m-%d") if not pd.isna(start_date) else "-"
        e = end_date.strftime("%Y-%m-%d") if not pd.isna(end_date) else "-"
        period_text = s if s == e else f"{s} ~ {e}"

    st.markdown(f"""
    <div class='soft-card'>
      <div class='section-title'>[{escape(alarm_code)}] {escape(alarm_name)}</div>
      <div class='muted-note'>공정명 : {escape(process_name)} / 선택일자 : {escape(period_text)} / Best : {escape(str(payload.get('best_eq_name') or 'Best'))} / Worst : {escape(str(payload.get('worst_eq_name') or 'Worst'))}</div>
    </div>
    """, unsafe_allow_html=True)

    render_dashboard_compare_table(payload)

    with st.expander("Best / Worst 호기 요약 보기", expanded=False):
        render_dashboard_snapshot_table(payload)

    render_dashboard_comment_section(payload, panel_id)

    # 서버 rerun 없이 우측상단 X와 동일하게 빠르게 닫기
    render_fast_dialog_close_button("팝업 닫기")


def maybe_render_alarm_popup(panel_id):
    popup = st.session_state.get("active_alarm_popup")
    event_id = st.session_state.get("active_alarm_popup_event_id")

    if not popup or not event_id:
        return

    if str(popup.get("panel_id")) != str(panel_id):
        return

    if str(popup.get("popup_type") or "") == "dashboard_compare":
        dashboard_alarm_detail_dialog(popup, panel_id)
    else:
        alarm_annotation_dialog(
            popup["alarm_code"],
            popup["alarm_name"],
            popup["panel_id"],
        )


def render_alarm_top5_compare_grid(alarm_df, best_eq_name, worst_eq_name, panel_id, popup_context=None):
    if alarm_df.empty:
        st.info("알람 비교 데이터가 없습니다.")
        return

    popup_context = popup_context or {}
    st.markdown(
        "<div class='soft-card'><div class='section-title'>Best vs Worst 호기 Alarm 차이 분석</div><div class='muted-note'>※ 알람명 셀을 더블클릭하면 상세 팝업이 열립니다.</div></div>",
        unsafe_allow_html=True,
    )

    display_df = alarm_df.copy()
    for col in [
        "worst_count", "worst_alarm_rate_pct", "worst_share_pct",
        "best_count", "best_alarm_rate_pct", "best_share_pct"
    ]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").fillna(0)

    display_df["alarm_display"] = display_df["alarm_name"].astype(str)
    display_df["popup_key"] = display_df.apply(
        lambda r: f"{panel_id}||{str(r.get('alarm_code', ''))}||{str(r.get('alarm_name', ''))}",
        axis=1,
    )

    payload_map = {}
    for row in display_df.to_dict("records"):
        popup_key = row["popup_key"]
        payload_map[popup_key] = {
            "popup_type": "dashboard_compare",
            "panel_id": panel_id,
            "popup_key": popup_key,
            "popup_scope": "standard",
            "equipment_id": popup_context.get("worst_equipment_id"),
            "base_date": popup_context.get("end_date") or popup_context.get("start_date"),
            "start_date": popup_context.get("start_date"),
            "end_date": popup_context.get("end_date"),
            "model_name": popup_context.get("model_name"),
            "process_name": popup_context.get("process_name"),
            "equipment_name": popup_context.get("worst_eq_name", worst_eq_name),
            "equipment_no": popup_context.get("worst_eq_name", worst_eq_name),
            "best_eq_name": popup_context.get("best_eq_name", best_eq_name),
            "worst_eq_name": popup_context.get("worst_eq_name", worst_eq_name),
            "snapshot_rows": popup_context.get("snapshot_rows", []),
            "alarm_code": str(row.get("alarm_code") or ""),
            "alarm_name": str(row.get("alarm_name") or ""),
            "selected_row": row,
            "rows": [{
                "alarm_code": str(row.get("alarm_code") or ""),
                "alarm_name": str(row.get("alarm_name") or ""),
            }],
        }

    if not AGGRID_AVAILABLE:
        fallback_cols = [
            c for c in [
                "alarm_name",
                "worst_count", "worst_alarm_rate_pct", "worst_share_pct",
                "best_count", "best_alarm_rate_pct", "best_share_pct",
            ] if c in display_df.columns
        ]
        st.dataframe(display_df[fallback_cols], use_container_width=True, hide_index=True)
        return

    grid_df = display_df[[
        "alarm_display",
        "worst_count", "worst_alarm_rate_pct", "worst_share_pct",
        "best_count", "best_alarm_rate_pct", "best_share_pct",
        "popup_key",
    ]].copy()

    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(
        editable=False,
        sortable=False,
        filter=False,
        resizable=True,
        wrapText=True,
        autoHeight=False,
    )
    gb.configure_selection(
        selection_mode="single",
        use_checkbox=False,
        rowMultiSelectWithClick=False,
        suppressRowDeselection=False,
    )
    grid_options = gb.build()

    double_click_js = JsCode("""
        function(event) {
            const colId = (event && event.column && event.column.colId) ? String(event.column.colId) : '';
            if (colId !== 'alarm_display') { return; }
            if (event && event.node) {
                event.node.setSelected(true, true);
            }
        }
    """)

    grid_options["onCellDoubleClicked"] = double_click_js
    grid_options["suppressRowClickSelection"] = True
    grid_options["rowSelection"] = "single"
    grid_options["headerHeight"] = 42
    grid_options["groupHeaderHeight"] = 44
    grid_options["rowHeight"] = 52
    grid_options["animateRows"] = False
    grid_options["suppressMovableColumns"] = True
    grid_options["columnDefs"] = [
        {"headerName": "알람명", "field": "alarm_display", "flex": 2.7, "minWidth": 220, "cellClass": "alarm-name-cell"},
        {
            "headerName": f"{worst_eq_name} (Worst)",
            "marryChildren": True,
            "headerClass": "worst-group-header",
            "children": [
                {"headerName": "횟수", "field": "worst_count", "flex": 0.8, "minWidth": 72, "type": ["numericColumn"], "headerClass": "worst-col-header", "cellClass": "worst-cell"},
                {"headerName": "알람율(%)", "field": "worst_alarm_rate_pct", "flex": 1.0, "minWidth": 90, "type": ["numericColumn"], "headerClass": "worst-col-header", "cellClass": "worst-cell", "valueFormatter": "x.toFixed(1) + '%'"},
                {"headerName": "점유율(%)", "field": "worst_share_pct", "flex": 1.0, "minWidth": 90, "type": ["numericColumn"], "headerClass": "worst-col-header", "cellClass": "worst-cell", "valueFormatter": "x.toFixed(0) + '%'"},
            ],
        },
        {
            "headerName": f"{best_eq_name} (Best)",
            "marryChildren": True,
            "headerClass": "best-group-header",
            "children": [
                {"headerName": "횟수", "field": "best_count", "flex": 0.8, "minWidth": 72, "type": ["numericColumn"], "headerClass": "best-col-header", "cellClass": "best-cell"},
                {"headerName": "알람율(%)", "field": "best_alarm_rate_pct", "flex": 1.0, "minWidth": 90, "type": ["numericColumn"], "headerClass": "best-col-header", "cellClass": "best-cell", "valueFormatter": "x.toFixed(1) + '%'"},
                {"headerName": "점유율(%)", "field": "best_share_pct", "flex": 1.0, "minWidth": 90, "type": ["numericColumn"], "headerClass": "best-col-header", "cellClass": "best-cell", "valueFormatter": "x.toFixed(0) + '%'"},
            ],
        },
        {"field": "popup_key", "hide": True},
    ]

    custom_css = {
        ".ag-root-wrapper": {"border": "1px solid #E8D8DE !important", "border-radius": "20px !important", "overflow": "hidden !important"},
        ".ag-header": {"background": "linear-gradient(180deg, #F7E7EC, #FFFDFE) !important"},
        ".ag-header-cell, .ag-header-group-cell": {"justify-content": "center !important", "text-align": "center !important", "font-size": "13px !important", "font-weight": "800 !important", "border-right": "1px solid #E8D8DE !important", "color": "#A50034 !important"},
        ".ag-cell": {"display": "flex !important", "align-items": "center !important", "justify-content": "center !important", "font-size": "12px !important", "font-weight": "700 !important", "color": "#3D2430 !important", "border-right": "1px solid #E8D8DE !important", "border-bottom": "1px solid #F0E5EA !important"},
        ".worst-group-header": {"background-color": "#F6D9DF !important", "color": "#A50034 !important"},
        ".best-group-header": {"background-color": "#E8F0FD !important", "color": "#A50034 !important"},
        ".worst-col-header": {"background-color": "#FAECEF !important"},
        ".best-col-header": {"background-color": "#EEF3FB !important"},
        ".worst-cell": {"background-color": "#FCF1F2 !important"},
        ".best-cell": {"background-color": "#F2F6FD !important"},
        ".alarm-name-cell": {"justify-content": "flex-start !important", "text-align": "left !important", "padding-left": "12px !important", "cursor": "pointer !important", "font-weight": "800 !important", "background-color": "#F6F1F4 !important"},
        ".alarm-name-cell:hover": {"background-color": "#F3E7EC !important"},
    }

    try:
        grid_response = AgGrid(
            grid_df,
            gridOptions=grid_options,
            key=f"alarm_grid_{panel_id}_{get_alarm_grid_version(panel_id)}",
            allow_unsafe_jscode=True,
            update_on=["selectionChanged", "cellDoubleClicked"],
            data_return_mode=DataReturnMode.AS_INPUT,
            fit_columns_on_grid_load=True,
            theme="streamlit",
            height=ALARM_GRID_HEIGHT,
            reload_data=False,
            custom_css=custom_css,
        )
    except TypeError:
        grid_response = AgGrid(
            grid_df,
            gridOptions=grid_options,
            key=f"alarm_grid_{panel_id}_{get_alarm_grid_version(panel_id)}",
            allow_unsafe_jscode=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            fit_columns_on_grid_load=True,
            theme="streamlit",
            height=ALARM_GRID_HEIGHT,
            reload_data=False,
            custom_css=custom_css,
        )

    selected_rows = normalize_aggrid_selected_rows(grid_response.get("selected_rows"))
    if selected_rows:
        selected = selected_rows[0]
        popup_key = str(selected.get("popup_key") or "").strip()
        if popup_key and popup_key in payload_map:
            current_popup = st.session_state.get("active_alarm_popup") or {}
            current_key = str(current_popup.get("popup_key") or "")
            if popup_key != current_key:
                st.session_state.dashboard_last_alarm_click[str(panel_id)] = popup_key
                st.session_state.active_alarm_popup = None
                st.session_state.active_alarm_popup_event_id = None
                st.session_state.dashboard_popup_fast_once = False
                dashboard_alarm_detail_dialog(payload_map[popup_key], panel_id)
                return

    maybe_render_alarm_popup(panel_id)



def get_equipment_alarm_total_count(engine, model_id, equipment_id, start_date, end_date, fallback_value=None):
    """선택 기간/모델/호기의 전체 알람 횟수 합계.
    - 우선 fact_alarm_detail_daily.alarm_count를 합산
    - model_id 컬럼/값 문제로 0이 되는 경우를 막기 위해 model 조건 없이 한 번 더 fallback
    """
    if equipment_id is None:
        return fallback_value

    sql_with_model = text("""
        SELECT COALESCE(SUM(COALESCE(alarm_count, 0)), 0) AS alarm_count
        FROM mtba.fact_alarm_detail_daily
        WHERE equipment_id = :equipment_id
          AND base_date BETWEEN :start_date AND :end_date
          AND model_id = :model_id
    """)
    sql_without_model = text("""
        SELECT COALESCE(SUM(COALESCE(alarm_count, 0)), 0) AS alarm_count
        FROM mtba.fact_alarm_detail_daily
        WHERE equipment_id = :equipment_id
          AND base_date BETWEEN :start_date AND :end_date
    """)

    params = {
        "equipment_id": int(equipment_id),
        "start_date": start_date,
        "end_date": end_date,
        "model_id": model_id,
    }

    try:
        values = []
        # 1차: model_id 조건 포함
        if model_id is not None:
            df = pd.read_sql(sql_with_model, engine, params=params)
            if not df.empty:
                values.append(int(round(float(df.loc[0, "alarm_count"] or 0))))
        # 2차: model_id 조건 제외. 1차가 0이면 이 값을 사용
        df2 = pd.read_sql(sql_without_model, engine, params=params)
        if not df2.empty:
            values.append(int(round(float(df2.loc[0, "alarm_count"] or 0))))

        if values:
            non_zero = [v for v in values if v > 0]
            if non_zero:
                return max(non_zero)
            return values[-1]
    except Exception:
        pass

    return fallback_value


def enforce_snapshot_total_alarm_counts(snapshot_df, summary_info, model_id, start_date, end_date):
    """Best/Worst Snapshot의 알람 횟수를 해당 호기의 전체 알람 합계로 보정."""
    if snapshot_df is None or snapshot_df.empty or "구분" not in snapshot_df.columns or "알람 횟수" not in snapshot_df.columns:
        return snapshot_df

    corrected = snapshot_df.copy()
    target_map = {
        "best": summary_info.get("best_equipment_id"),
        "worst": summary_info.get("worst_equipment_id"),
    }

    for idx, row in corrected.iterrows():
        key = str(row.get("구분", "")).strip().lower()
        equipment_id = target_map.get(key)
        fallback = row.get("알람 횟수", None)
        total_alarm_count = get_equipment_alarm_total_count(
            engine=engine,
            model_id=model_id,
            equipment_id=equipment_id,
            start_date=start_date,
            end_date=end_date,
            fallback_value=fallback,
        )
        if total_alarm_count is not None:
            corrected.at[idx, "알람 횟수"] = int(round(float(total_alarm_count or 0)))

    return corrected

# =========================================================
# 섹션 2 카드 렌더링 helper
# =========================================================
def render_signal_summary_card(summary_info: dict, process_name: str):
    best_mtba_text = "-" if summary_info["best_mtba"] is None else f"{summary_info['best_mtba']:.0f}분"
    worst_mtba_text = "-" if summary_info["worst_mtba"] is None else f"{summary_info['worst_mtba']:.0f}분"
    avg_mtba_text = "-" if summary_info["avg_mtba"] is None else f"{summary_info['avg_mtba']:.0f}분"

    best_eq = "-" if not summary_info.get("best_equipment_name") else escape(str(summary_info["best_equipment_name"]))
    worst_eq = "-" if not summary_info.get("worst_equipment_name") else escape(str(summary_info["worst_equipment_name"]))

    html = dedent(f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: Arial, Helvetica, sans-serif;
        }}
        .card {{
          border: 1px solid #d9d9d9;
          border-radius: 10px;
          padding: 14px 16px;
          min-height: 228px;
          background: #ffffff;
          box-sizing: border-box;
        }}
        .title {{
          font-weight: 700;
          font-size: 16px;
          margin-bottom: 8px;
        }}
        .total {{
          font-weight: 700;
          margin-bottom: 12px;
        }}
        .light-row {{
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 8px 0;
          color: #111111;
        }}
        .dot {{
          display: inline-block;
          width: 16px;
          height: 16px;
          border-radius: 50%;
        }}
        .dot-green {{ background: #16a34a; }}
        .dot-yellow {{ background: #facc15; }}
        .dot-red {{ background: #dc2626; }}

        .summary {{
          line-height: 1.9;
          margin-top: 14px;
          font-size: 14px;
        }}

        .best-row {{
          color: #1d4ed8;
          font-weight: 700;
        }}

        .worst-row {{
          color: #b91c1c;
          font-weight: 700;
        }}

        .avg-row {{
          color: #111111;
          font-weight: 600;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="title">공정: {escape(str(process_name))}</div>
        <div class="total">Total 가동 설비 : {summary_info['total_active_equipment']}대</div>

        <div>
          <div class="light-row">
            <span class="dot dot-green"></span>
            <span>120min↑ : {summary_info['green_count']}대</span>
          </div>
          <div class="light-row">
            <span class="dot dot-yellow"></span>
            <span>60~120min : {summary_info['yellow_count']}대</span>
          </div>
          <div class="light-row">
            <span class="dot dot-red"></span>
            <span>60min↓ : {summary_info['red_count']}대</span>
          </div>
        </div>

        <div class="summary">
          <div class="best-row">Best : {best_mtba_text} ({best_eq})</div>
          <div class="worst-row">Worst : {worst_mtba_text} ({worst_eq})</div>
          <div class="avg-row">평균 : {avg_mtba_text}</div>
        </div>
      </div>
    </body>
    </html>
    """).strip()

    components.html(html, height=SIGNAL_CARD_HEIGHT, scrolling=False)


def render_best_worst_snapshot_card(snapshot_df: pd.DataFrame, process_name: str):
    if snapshot_df.empty:
        st.info("Best/Worst 호기 데이터가 없습니다.")
        return

    order_map = {"Worst": 0, "Best": 1}
    snap = snapshot_df.copy()
    if "구분" in snap.columns:
        snap["_ord"] = snap["구분"].map(order_map).fillna(99)
        snap = snap.sort_values("_ord").drop(columns="_ord")

    rows_html = []
    for _, row in snap.iterrows():
        row_type = str(row["구분"]).strip().lower()

        if row_type == "worst":
            row_color = "#b91c1c"
            row_bg = "#fef2f2"
            row_weight = "700"
        elif row_type == "best":
            row_color = "#1d4ed8"
            row_bg = "#eff6ff"
            row_weight = "700"
        else:
            row_color = "#111111"
            row_bg = "#ffffff"
            row_weight = "400"

        rows_html.append(f"""
        <tr style="color:{row_color}; background:{row_bg}; font-weight:{row_weight};">
            <td>{escape(str(row["구분"]))}</td>
            <td>{escape(str(row["호기"]))}</td>
            <td>{float(row["Runtime(분)"]):.1f}</td>
            <td>{int(row["알람 횟수"])}</td>
            <td>{float(row["MTBA"]):.0f}분</td>
        </tr>
        """)

    html = dedent(f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: Arial, Helvetica, sans-serif;
        }}
        .card {{
          border: 1px solid #d9d9d9;
          border-radius: 10px;
          padding: 12px 12px 10px 12px;
          min-height: 198px;
          background: #ffffff;
          box-sizing: border-box;
        }}
        .title {{
          font-weight: 700;
          font-size: 16px;
          margin-bottom: 10px;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          font-size: 13px;
        }}
        th, td {{
          border: 1px solid #d9d9d9;
          padding: 8px 6px;
          text-align: center;
          vertical-align: middle;
          word-break: break-word;
        }}
        thead tr {{
          background: #f3f4f6;
          color: #111111;
          font-weight: 700;
        }}
        th:nth-child(1) {{ width: 14%; }}
        th:nth-child(2) {{ width: 30%; }}
        th:nth-child(3) {{ width: 20%; }}
        th:nth-child(4) {{ width: 18%; }}
        th:nth-child(5) {{ width: 18%; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="title">■ {escape(str(process_name))} Best / Worst 호기</div>
        <table>
          <thead>
            <tr>
              <th>구분</th>
              <th>호기</th>
              <th>Runtime(분)</th>
              <th>알람 횟수</th>
              <th>MTBA</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
      </div>
    </body>
    </html>
    """).strip()

    components.html(html, height=SNAPSHOT_CARD_HEIGHT, scrolling=False)




# =========================================================
# 메모 / 이미지 저장
# =========================================================
def save_note_and_image(panel_key, model_id, process_id, start_date, end_date, note_text, uploaded_file):
    with engine.begin() as conn:
        note_row = conn.execute(text("""
            INSERT INTO mtba.report_note
            (panel_key, model_id, process_id, selected_period_key, note_text)
            VALUES
            (:panel_key, :model_id, :process_id, :selected_period_key, :note_text)
            RETURNING note_id
        """), {
            "panel_key": panel_key,
            "model_id": model_id,
            "process_id": process_id,
            "selected_period_key": f"{start_date} ~ {end_date}",
            "note_text": note_text
        }).mappings().first()

        note_id = note_row["note_id"]

        if uploaded_file is not None:
            save_path = UPLOAD_DIR / uploaded_file.name
            content = uploaded_file.getbuffer()
            with open(save_path, "wb") as f:
                f.write(content)

            width_px = None
            height_px = None
            try:
                img = Image.open(save_path)
                width_px, height_px = img.size
            except Exception:
                pass

            conn.execute(text("""
                INSERT INTO mtba.report_image
                (note_id, file_name, file_path, mime_type, file_size, width_px, height_px)
                VALUES
                (:note_id, :file_name, :file_path, :mime_type, :file_size, :width_px, :height_px)
            """), {
                "note_id": note_id,
                "file_name": uploaded_file.name,
                "file_path": str(save_path),
                "mime_type": uploaded_file.type,
                "file_size": uploaded_file.size,
                "width_px": width_px,
                "height_px": height_px
            })


# =========================================================
# 패널 렌더링
# =========================================================
def render_panel(panel_id: int):
    st.markdown(f"<div class='soft-card'><div class='section-title'>MTBA 분석 Reporting #{panel_id}</div></div>", unsafe_allow_html=True)

    top1, top2, top3 = st.columns([1.2, 1.8, 2.2])

    with top1:
        team_name = st.selectbox(
            f"팀 선택 #{panel_id}",
            options=TEAM_OPTIONS,
            index=0,
            key=f"team_{panel_id}"
        )

    with top2:
        model_name = st.selectbox(
            f"모델 선택 #{panel_id}",
            options=list(model_options.keys()),
            key=f"model_{panel_id}"
        )
        model_id = model_options[model_name]

    with top3:
        default_start, default_end = get_default_this_week_range(min_date, max_date)

        selected_period = st.date_input(
            f"기간 선택 #{panel_id}",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date,
            key=f"period_range_{panel_id}"
        )

        if isinstance(selected_period, tuple) and len(selected_period) == 2:
            selected_start, selected_end = selected_period
        elif isinstance(selected_period, list) and len(selected_period) == 2:
            selected_start, selected_end = selected_period[0], selected_period[1]
        else:
            selected_start, selected_end = selected_period, selected_period

    ui_signature = (team_name, model_id, selected_start, selected_end)
    sig_key = f"ui_signature_{panel_id}"
    if st.session_state.get(sig_key) != ui_signature:
        st.session_state[sig_key] = ui_signature
        st.session_state.active_alarm_popup = None
        st.session_state.active_alarm_popup_event_id = None
        bump_alarm_grid_version(panel_id)

    selected_period_label = format_selected_period(selected_start, selected_end)

    team_process_ids = None

    if team_name == "전체":
        st.caption("※ 팀 = 전체 : 모든 공정을 대상으로 조회합니다.")
    else:
        saved_team_process_ids = set(get_saved_team_process_ids(team_name))
        selected_team_process_ids = []

        with st.expander(f"{team_name} 공정 선택", expanded=False):
            st.caption("※ 필요한 공정만 체크한 뒤 '팀 공정 저장' 버튼을 눌러주세요.")

            process_container = st.container()
            checkbox_cols = process_container.columns(4)

            for idx, row in all_process_df.iterrows():
                process_id = int(row["process_id"])
                label = process_label_map[process_id]
                checkbox_key = f"team_process_chk_{panel_id}_{team_name}_{process_id}"

                with checkbox_cols[idx % 4]:
                    checked = st.checkbox(
                        label,
                        value=(process_id in saved_team_process_ids),
                        key=checkbox_key
                    )

                if checked:
                    selected_team_process_ids.append(process_id)

            save_col1, save_col2 = st.columns([1.2, 6])

            with save_col1:
                if st.button("팀 공정 저장", key=f"save_team_process_{panel_id}_{team_name}"):
                    save_team_process_ids(engine, team_name, selected_team_process_ids)
                    st.success(f"{team_name} 공정 설정이 저장되었습니다.")
                    st.session_state.active_alarm_popup = None
                    st.session_state.active_alarm_popup_event_id = None
                    bump_alarm_grid_version(panel_id)
                    st.rerun()

            with save_col2:
                if selected_team_process_ids:
                    selected_names = get_display_process_names_from_ids(selected_team_process_ids)
                    st.caption(f"현재 체크 공정: {', '.join(selected_names)}")

        team_process_ids = selected_team_process_ids

        if not team_process_ids:
            st.warning(f"{team_name}에 선택된 공정이 없습니다. expander를 열어 공정을 체크 후 저장해주세요.")
            return

        selected_team_process_names = get_display_process_names_from_ids(team_process_ids)
        if selected_team_process_names:
            st.caption(f"※ {team_name} 적용 공정: {', '.join(selected_team_process_names)}")

    selected_processes = get_selected_processes(panel_id)
    if selected_processes:
        st.caption(f"※ 현재 선택 공정: {', '.join(selected_processes)}")

    st.caption("※ 그래프 구간: 선택한 기간 / 1주전 / 2주전 / 지난달 전체 / 2달전 전체 / 지난해 전체")
    st.caption("※ MTBA가 0이거나 없는 설비는 자동 제외 후, 유효 설비만 평균하여 MTBA를 계산합니다.")
    st.caption("※ 그래프 가시성을 위해 막대 높이는 최대 120까지만 표시되며, 라벨은 실제 MTBA 값을 표시합니다.")
    st.caption("※ 그래프는 다중 선택 가능, 요약표 체크박스와 연동됩니다. 최대 5개 공정까지 섹션 2에 표시됩니다.")

    # =====================================================
    # 1. 그래프
    # =====================================================
    st.markdown(f"### 1. {model_name} 공정별 MTBA 기간 비교")

    compare_df = get_period_compare_by_process(
        engine=engine,
        model_id=model_id,
        start_date=selected_start,
        end_date=selected_end,
        include_total_avg=True,
        process_ids=team_process_ids
    )

    if compare_df.empty:
        st.warning("선택한 조건에서 그래프를 그릴 데이터가 없습니다.")
        summary_df = pd.DataFrame()
    else:
        selected_processes = get_selected_processes(panel_id)
        chart_version = get_chart_version(panel_id)

        fig = make_mtba_process_bar_chart(
            compare_df=compare_df,
            model_name=model_name,
            warn_line=60,
            target_line=120,
            selected_process_names=selected_processes,
        )

        plot_event = st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"mtba_chart_{panel_id}_{chart_version}",
            on_select="rerun",
            selection_mode=("points", "box", "lasso")
        )

        if plot_event:
            selected_points = plot_event.get("selection", {}).get("points", [])
            if selected_points:
                graph_selected_processes = []
                for point in selected_points:
                    customdata = point.get("customdata")
                    if isinstance(customdata, (list, tuple)) and len(customdata) >= 1:
                        graph_selected_processes.append(customdata[0])

                if graph_selected_processes:
                    changed = set_selected_processes(
                        panel_id=panel_id,
                        process_names=graph_selected_processes,
                        source="chart"
                    )
                    if changed:
                        st.rerun()

        selected_processes = get_selected_processes(panel_id)
        if selected_processes:
            st.caption(f"※ 현재 선택 공정: {', '.join(selected_processes)}")

        with st.expander("그래프 데이터 보기"):
            st.dataframe(compare_df, use_container_width=True, hide_index=True)

        select_btn_col1, select_btn_col2, _ = st.columns([1, 1.8, 5.2])

        with select_btn_col1:
            if st.button("선택 초기화", key=f"clear_selected_processes_{panel_id}"):
                changed = set_selected_processes(panel_id, [], source="clear")
                if changed:
                    st.rerun()

        with select_btn_col2:
            st.caption("※ Shift+클릭 / Box / Lasso로 여러 공정을 선택할 수 있습니다.")

    # =====================================================
    # 1-2. 공정별 요약
    # =====================================================
    summary_title_col, summary_option_col = st.columns([6, 1.2])

    with summary_title_col:
        st.markdown(f"### {selected_period_label} 공정별 요약")

    with summary_option_col:
        use_short_name = st.checkbox(
            "공정명 축약",
            value=False,
            key=f"use_short_{panel_id}"
        )

    summary_df = get_process_summary(
        engine=engine,
        model_id=model_id,
        start_date=selected_start,
        end_date=selected_end,
        use_short_name=use_short_name,
        process_ids=team_process_ids
    )

    selected_focus_processes = []

    if summary_df.empty:
        st.warning("선택한 기간 공정별 데이터가 없습니다.")
    else:
        selected_processes = get_selected_processes(panel_id)

        editor_view_df = summary_df[["공정", "Best MTBA", "Worst MTBA", "Avg MTBA", "Stdev MTBA"]].copy()
        editor_view_df.insert(0, "선택", summary_df["원본공정명"].isin(selected_processes))

        editor_version = get_summary_editor_version(panel_id)

        edited_df = st.data_editor(
            editor_view_df,
            use_container_width=True,
            hide_index=True,
            key=f"summary_editor_{panel_id}_{editor_version}",
            column_config={
                "선택": st.column_config.CheckboxColumn(
                    "선택",
                    help="최대 5개 공정까지 선택 가능",
                    default=False,
                ),
            },
            disabled=["공정", "Best MTBA", "Worst MTBA", "Avg MTBA", "Stdev MTBA"]
        )

        checked_indices = edited_df.index[edited_df["선택"]].tolist()
        checked_processes = summary_df.iloc[checked_indices]["원본공정명"].tolist() if checked_indices else []

        if st.session_state.get(f"skip_table_apply_once_{panel_id}", False):
            st.session_state[f"skip_table_apply_once_{panel_id}"] = False
        else:
            changed = set_selected_processes(
                panel_id=panel_id,
                process_names=checked_processes,
                source="table"
            )
            if changed:
                st.rerun()

        # =====================================================
        # 2. MTBA 현황
        # =====================================================
        st.markdown(f"<div id='mtba_status_{panel_id}'></div>", unsafe_allow_html=True)

        if st.session_state.get(f"scroll_to_mtba_{panel_id}", False):
            components.html(f"""
            <script>
                const target = window.parent.document.getElementById("mtba_status_{panel_id}");
                if (target) {{
                    target.scrollIntoView({{behavior: "smooth", block: "start"}});
                }}
            </script>
            """, height=0)
            st.session_state[f"scroll_to_mtba_{panel_id}"] = False

        selected_focus_processes = get_selected_processes(panel_id)

        if not selected_focus_processes and not summary_df.empty:
            selected_focus_processes = [summary_df.iloc[0]["원본공정명"]]

        st.markdown(f"### 2. MTBA 현황({selected_period_label})")

        if not selected_focus_processes:
            st.info("그래프 또는 공정별 요약 표에서 공정을 선택하면 해당 공정 기준의 MTBA 현황이 표시됩니다.")
        else:
            process_id_for_note = None

            for idx, focus_process_name in enumerate(selected_focus_processes[:5]):
                summary_info, process_week_df = get_process_week_status(
                    engine=engine,
                    model_id=model_id,
                    process_name=focus_process_name,
                    week_start=selected_start,
                    week_end=selected_end,
                    process_ids=team_process_ids
                )

                if process_week_df.empty:
                    st.warning(f"선택된 공정 [{focus_process_name}] 의 데이터가 없습니다.")
                    continue

                if process_id_for_note is None:
                    process_id_for_note = summary_info["process_id"]

                if idx > 0:
                    st.markdown("---")

                # 사진처럼: 왼쪽 2개카드 / 오른쪽 큰 알람표
                outer_left_col, outer_right_col = st.columns([1.0, 1.75])

                with outer_left_col:
                    render_signal_summary_card(summary_info, focus_process_name)

                    # 위아래 여백 제거
                    st.markdown(
                        f"<div style='margin-top:-{LEFT_CARD_OVERLAP}px;'></div>",
                        unsafe_allow_html=True
                    )

                    snapshot_df = get_process_best_worst_snapshot(summary_info, process_week_df)
                    snapshot_df = enforce_snapshot_total_alarm_counts(
                        snapshot_df=snapshot_df,
                        summary_info=summary_info,
                        model_id=model_id,
                        start_date=selected_start,
                        end_date=selected_end,
                    )
                    render_best_worst_snapshot_card(snapshot_df, focus_process_name)

                with outer_right_col:
                    alarm_top5_df = get_best_worst_alarm_top5_by_worst(
                        engine=engine,
                        model_id=model_id,
                        week_start=selected_start,
                        week_end=selected_end,
                        best_equipment_id=summary_info["best_equipment_id"],
                        worst_equipment_id=summary_info["worst_equipment_id"],
                        top_n=5
                    )

                    render_alarm_top5_compare_grid(
                        alarm_df=alarm_top5_df,
                        best_eq_name=summary_info["best_equipment_name"],
                        worst_eq_name=summary_info["worst_equipment_name"],
                        panel_id=f"{panel_id}_{idx}",
                        popup_context={
                            "start_date": selected_start,
                            "end_date": selected_end,
                            "model_name": model_name,
                            "process_name": focus_process_name,
                            "snapshot_rows": snapshot_df.to_dict("records") if isinstance(snapshot_df,
                                                                                          pd.DataFrame) and not snapshot_df.empty else [],
                            "best_eq_name": summary_info["best_equipment_name"],
                            "worst_eq_name": summary_info["worst_equipment_name"],
                            "worst_equipment_id": summary_info["worst_equipment_id"],
                        }
                    )

    # =====================================================
    # 4. 메모 / 이미지
    # =====================================================
    st.markdown("### 4. 메모 / 이미지 업로드")

    process_id_for_note = None
    if selected_focus_processes:
        summary_info_tmp, _ = get_process_week_status(
            engine=engine,
            model_id=model_id,
            process_name=selected_focus_processes[0],
            week_start=selected_start,
            week_end=selected_end,
            process_ids=team_process_ids
        )

        process_id_for_note = summary_info_tmp.get("process_id")

    note_text = st.text_area(
        f"메모 입력 #{panel_id}",
        placeholder="Worst 설비 원인, 개선 액션, 현장 코멘트 등을 입력",
        height=140,
        key=f"note_text_{panel_id}"
    )

    uploaded_file = st.file_uploader(
        f"이미지 업로드 #{panel_id}",
        type=["png", "jpg", "jpeg", "bmp"],
        key=f"img_upload_{panel_id}"
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption=uploaded_file.name)

    if st.button(f"메모/이미지 저장 #{panel_id}", key=f"save_note_img_{panel_id}"):
        save_note_and_image(
            panel_key=f"panel_{panel_id}",
            model_id=model_id,
            process_id=process_id_for_note,
            start_date=selected_start,
            end_date=selected_end,
            note_text=note_text,
            uploaded_file=uploaded_file
        )
        st.success("저장되었습니다.")

    # =====================================================
    # 패널 하단 추가 / 제거
    # =====================================================
    bottom1, bottom2, bottom3 = st.columns([1, 1, 6])

    with bottom1:
        if st.button(f"이 패널 아래에 추가 #{panel_id}", key=f"add_after_{panel_id}"):
            insert_panel_after(panel_id)
            st.session_state.active_alarm_popup = None
            st.session_state.active_alarm_popup_event_id = None
            st.rerun()

    with bottom2:
        remove_disabled = len(st.session_state.panel_ids) <= 1
        if st.button(
            f"이 패널 제거 #{panel_id}",
            key=f"remove_panel_{panel_id}",
            disabled=remove_disabled
        ):
            remove_panel(panel_id)
            st.session_state.active_alarm_popup = None
            st.session_state.active_alarm_popup_event_id = None
            st.rerun()



# =========================================================
# 패널 렌더링
# =========================================================
for panel_id in st.session_state.panel_ids:
    render_panel(panel_id)