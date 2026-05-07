import time
import streamlit as st
import psycopg2

# ==================================================
# DB 연결
# ==================================================
def get_conn():
    return psycopg2.connect(
        host=st.secrets["db"]["host"],
        dbname=st.secrets["db"]["name"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        port=st.secrets["db"]["port"],
    )


# ==================================================
# 이전에 종료되지 않은 세션 정리
# - 같은 사용자가 새로 로그인하면 이전 미종료 세션은 timeout 처리
# ==================================================
def close_previous_open_sessions(user_email: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE user_sessions
        SET logout_at = NOW(),
            session_end_reason = 'timeout',
            session_duration_sec = EXTRACT(EPOCH FROM (NOW() - login_at))::INT
        WHERE user_email = %s
          AND logout_at IS NULL;
        """,
        (user_email,)
    )

    conn.commit()
    cur.close()
    conn.close()


# ==================================================
# 로그인 세션 생성
# ==================================================
def create_login_session(user_email: str, department: str) -> int:
    # 기존 미종료 세션 정리
    close_previous_open_sessions(user_email)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO user_sessions (user_email, department, login_at)
        VALUES (%s, %s, NOW())
        RETURNING id;
        """,
        (user_email, department)
    )

    session_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return session_id


# ==================================================
# 로그인 세션 종료
# reason 예: logout / timeout / unknown
# ==================================================
def close_login_session(session_id: int, reason: str = "logout"):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE user_sessions
        SET logout_at = NOW(),
            session_end_reason = %s,
            session_duration_sec = EXTRACT(EPOCH FROM (NOW() - login_at))::INT
        WHERE id = %s
          AND logout_at IS NULL;
        """,
        (reason, session_id)
    )

    conn.commit()
    cur.close()
    conn.close()


# ==================================================
# 페이지 조회 로그 1건 기록
# ==================================================
def log_page_view(
    session_id: int,
    user_email: str,
    department: str,
    page_name: str,
    page_path: str = None
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO page_view_logs (
            session_id,
            user_email,
            department,
            page_name,
            page_path,
            viewed_at
        )
        VALUES (%s, %s, %s, %s, %s, NOW());
        """,
        (session_id, user_email, department, page_name, page_path)
    )

    conn.commit()
    cur.close()
    conn.close()


# ==================================================
# Streamlit rerun 특성 때문에 과다 기록 방지
# 같은 페이지를 너무 짧은 시간 안에 반복 기록하지 않음
# ==================================================
def log_page_view_once(
    page_name: str,
    page_path: str = None,
    min_interval_sec: int = 15
):
    if not st.session_state.get("login"):
        return

    session_id = st.session_state.get("session_id")
    user_email = st.session_state.get("user_email")
    department = st.session_state.get("department")

    if not session_id or not user_email:
        return

    now_ts = time.time()
    last_page = st.session_state.get("last_logged_page")
    last_time = st.session_state.get("last_logged_time", 0)

    # 같은 페이지를 min_interval_sec 이내 재조회하면 기록 생략
    if last_page == page_name and (now_ts - last_time) < min_interval_sec:
        return

    log_page_view(
        session_id=session_id,
        user_email=user_email,
        department=department,
        page_name=page_name,
        page_path=page_path
    )

    st.session_state.last_logged_page = page_name
    st.session_state.last_logged_time = now_ts

