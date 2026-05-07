import streamlit as st
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Patch Note", page_icon="📌", layout="wide")

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()


def get_conn():
    return psycopg2.connect(
        host=st.secrets["db"]["host"],
        dbname=st.secrets["db"]["name"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        port=st.secrets["db"]["port"],
    )


def get_board_posts(category="patch"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, category, tag, title, created_by, created_at
        FROM board_posts
        WHERE category = %s
          AND is_published = TRUE
        ORDER BY created_at DESC;
        """,
        (category,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_board_post_detail(post_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, category, tag, title, content, created_by, created_at, updated_at
        FROM board_posts
        WHERE id = %s
          AND is_published = TRUE;
        """,
        (post_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def create_board_post(category, tag, title, content, created_by):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO board_posts (category, tag, title, content, created_by)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (category, tag, title, content, created_by)
        )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def update_board_post(post_id, tag, title, content):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE board_posts
            SET tag = %s,
                title = %s,
                content = %s,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (tag, title, content, post_id)
        )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def delete_board_post(post_id):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE board_posts
            SET is_published = FALSE,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (post_id,)
        )

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def apply_board_styles():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #0A0C10 0%, #11151b 100%);
            color: white;
        }
        
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
        
        [data-testid="stToolbar"] {
            background: transparent !important;
        }
        
        [data-testid="stDecoration"] {
            background: transparent !important;
        }

        .block-container {
            max-width: 1400px !important;
            padding-top: 3rem !important;
            padding-bottom: 2rem !important;
        }

        .board-top-title {
            font-size: 30px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.02em;
            margin-bottom: 6px;
        }

        .board-top-sub {
            color: rgba(255,255,255,0.68);
            font-size: 13px;
            margin-bottom: 24px;
        }

        .board-panel-bg {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            min-height: 620px;
            border-radius: 18px;
            background: rgba(10,12,16,0.58);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow:
                0 16px 34px rgba(0,0,0,0.22),
                inset 0 1px 0 rgba(255,255,255,0.04);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            pointer-events: none;
            z-index: 0;
        }

        [data-testid="column"] {
            position: relative;
            z-index: 1;
        }

        .board-inner {
            position: relative;
            z-index: 1;
            padding: 18px 18px 16px 18px;
        }

        .board-section-title {
            font-size: 13px;
            font-weight: 700;
            color: rgba(255,255,255,0.82);
            letter-spacing: .04em;
            margin-bottom: 12px;
        }

        .board-meta {
            color: rgba(255,255,255,0.60);
            font-size: 12px;
            line-height: 1.5;
        }

        .board-detail-title {
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.3;
            margin-bottom: 8px;
        }

        .board-tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            margin-right: 8px;
            vertical-align: middle;
        }

        .board-tag-new {
            background: rgba(31,139,76,0.24);
            border: 1px solid rgba(31,139,76,0.42);
            color: #d7ffe5;
        }

        .board-tag-upd {
            background: rgba(37,99,235,0.24);
            border: 1px solid rgba(37,99,235,0.42);
            color: #dbeafe;
        }

        .board-tag-fix {
            background: rgba(165,0,52,0.25);
            border: 1px solid rgba(165,0,52,0.40);
            color: #ffe4ec;
        }

        .board-tag-default {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.16);
            color: #ffffff;
        }

        div[data-testid="stButton"] > button {
            border-radius: 10px !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            color: rgba(255,255,255,0.86) !important;
            text-align: left !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] p {
            text-align: left !important;
            width: 100% !important;
            margin: 0 !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            color: #ffffff !important;
            text-decoration: underline !important;
            background: transparent !important;
        }

        [data-testid="stExpander"] {
            background: rgba(10,12,16,0.52);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background: rgba(255,255,255,0.96) !important;
        }

        .board-list-row {
            border-top: 1px dashed rgba(255,255,255,0.08);
            margin: 6px 0;
        }

        .board-list-date {
            color: rgba(255,255,255,0.68);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .05em;
            padding-top: 6px;
            white-space: nowrap;
        }

        .board-list-tag-wrap {
            padding-top: 2px;
        }

        .board-list-title button {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_board_panel_background():
    st.markdown(
        """
        <div class="board-panel-bg"></div>
        """,
        unsafe_allow_html=True
    )


def tag_class(tag: str) -> str:
    tag_upper = (tag or "").upper()
    if tag_upper == "NEW":
        return "board-tag board-tag-new"
    elif tag_upper == "UPD":
        return "board-tag board-tag-upd"
    elif tag_upper == "FIX":
        return "board-tag board-tag-fix"
    return "board-tag board-tag-default"


# ----------------------------
# session state
# ----------------------------
if "role" not in st.session_state:
    st.session_state.role = "user"

if "selected_post_id" not in st.session_state:
    st.session_state.selected_post_id = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False


# ----------------------------
# query parameter에서 post_id 읽기
# ----------------------------
query_params = st.query_params
query_post_id = query_params.get("post_id", None)

if query_post_id:
    try:
        st.session_state.selected_post_id = int(query_post_id)
    except ValueError:
        st.session_state.selected_post_id = None


apply_board_styles()

st.markdown('<div class="board-top-title">Patch Note · 패치노트</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="board-top-sub">최신 변경 이력을 확인하고 상세 내용을 조회할 수 있습니다.</div>',
    unsafe_allow_html=True
)

# ----------------------------
# 운영자만 등록 가능
# ----------------------------
if st.session_state.role == "admin":
    with st.expander("게시글 등록", expanded=False):
        tag = st.selectbox("태그", ["NEW", "FIX", "UPD", "INFO"])
        title = st.text_input("제목")
        content = st.text_area("내용", height=220)

        if st.button("등록"):
            if not title.strip():
                st.error("제목을 입력하세요.")
            elif not content.strip():
                st.error("내용을 입력하세요.")
            else:
                try:
                    created_by = st.session_state.get("user_email", None)

                    if not created_by:
                        st.error("로그인 사용자 정보가 없습니다. 다시 로그인해주세요.")
                    else:
                        create_board_post(
                            category="patch",
                            tag=tag,
                            title=title.strip(),
                            content=content.strip(),
                            created_by=created_by
                        )
                        st.success("등록되었습니다.")
                        st.query_params.clear()
                        st.session_state.selected_post_id = None
                        st.session_state.edit_mode = False
                        st.rerun()

                except Exception as e:
                    st.error(f"등록 중 오류가 발생했습니다: {e}")


posts = get_board_posts(category="patch")

if not st.session_state.selected_post_id and posts:
    st.session_state.selected_post_id = posts[0][0]

col1, col2 = st.columns([1.05, 1.95], gap="large")

with col1:
    render_board_panel_background()
    st.markdown('<div class="board-inner">', unsafe_allow_html=True)

    left_pad, content_col, right_pad = st.columns([0.04, 0.92, 0.04], gap="small")

    with content_col:
        st.markdown('<div class="board-section-title">목록</div>', unsafe_allow_html=True)

        for idx, (post_id, category, tag, title, created_by, created_at) in enumerate(posts):
            if idx > 0:
                st.markdown('<div class="board-list-row"></div>', unsafe_allow_html=True)

            date_col, tag_col, title_col = st.columns([0.16, 0.18, 0.66], gap="small")

            with date_col:
                st.markdown(
                    f'<div class="board-list-date">{created_at.strftime("%m-%d")}</div>',
                    unsafe_allow_html=True
                )

            with tag_col:
                st.markdown(
                    f'<div class="board-list-tag-wrap"><span class="{tag_class(tag)}">{tag}</span></div>',
                    unsafe_allow_html=True
                )

            with title_col:
                if st.button(
                    title,
                    key=f"post_{post_id}",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.selected_post_id = post_id
                    st.session_state.edit_mode = False
                    st.query_params["post_id"] = str(post_id)
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    render_board_panel_background()
    st.markdown('<div class="board-inner">', unsafe_allow_html=True)

    left_pad, content_col, right_pad = st.columns([0.04, 0.92, 0.04], gap="small")

    with content_col:
        st.markdown('<div class="board-section-title">상세</div>', unsafe_allow_html=True)

        if st.session_state.selected_post_id:
            detail = get_board_post_detail(st.session_state.selected_post_id)

            if detail:
                _, category, tag, title, content, created_by, created_at, updated_at = detail

                st.markdown(
                    f'<div class="{tag_class(tag)}">{tag}</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div class="board-detail-title">{title}</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div class="board-meta">작성자: {created_by}<br>작성일: {created_at.strftime("%Y-%m-%d %H:%M")}</div>',
                    unsafe_allow_html=True
                )

                if updated_at and updated_at != created_at:
                    st.markdown(
                        f'<div class="board-meta">수정일: {updated_at.strftime("%Y-%m-%d %H:%M")}</div>',
                        unsafe_allow_html=True
                    )

                st.divider()
                st.write(content)

                if st.session_state.role == "admin":
                    st.divider()

                    col_edit, col_delete = st.columns([1, 1])

                    with col_edit:
                        if st.button("수정", key=f"edit_post_{st.session_state.selected_post_id}"):
                            st.session_state.edit_mode = True

                    with col_delete:
                        if st.button("삭제", key=f"delete_post_{st.session_state.selected_post_id}"):
                            try:
                                delete_board_post(st.session_state.selected_post_id)
                                st.success("삭제되었습니다.")
                                st.session_state.selected_post_id = None
                                st.session_state.edit_mode = False
                                st.query_params.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"삭제 중 오류가 발생했습니다: {e}")

                    if st.session_state.edit_mode:
                        st.markdown("### 게시글 수정")

                        tag_options = ["NEW", "FIX", "UPD", "INFO"]
                        edit_tag = st.selectbox(
                            "태그",
                            tag_options,
                            index=tag_options.index(tag) if tag in tag_options else 0,
                            key="edit_tag"
                        )

                        edit_title = st.text_input("제목", value=title, key="edit_title")
                        edit_content = st.text_area("내용", value=content, height=220, key="edit_content")

                        col_save, col_cancel = st.columns([1, 1])

                        with col_save:
                            if st.button("수정 저장", key=f"save_post_{st.session_state.selected_post_id}"):
                                if not edit_title.strip():
                                    st.error("제목을 입력하세요.")
                                elif not edit_content.strip():
                                    st.error("내용을 입력하세요.")
                                else:
                                    try:
                                        update_board_post(
                                            post_id=st.session_state.selected_post_id,
                                            tag=edit_tag,
                                            title=edit_title.strip(),
                                            content=edit_content.strip()
                                        )
                                        st.success("수정되었습니다.")
                                        st.session_state.edit_mode = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"수정 중 오류가 발생했습니다: {e}")

                        with col_cancel:
                            if st.button("수정 취소", key=f"cancel_edit_{st.session_state.selected_post_id}"):
                                st.session_state.edit_mode = False
                                st.rerun()

            else:
                st.info("게시글을 찾을 수 없습니다.")
        else:
            st.info("왼쪽 목록에서 게시글을 선택하세요.")

    st.markdown('</div>', unsafe_allow_html=True)