import json
import time
import streamlit as st
import psycopg2
from psycopg2.extras import Json

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


# ==================================================================
# ===== Analytics extensions (Vitals self-hosted GA + Clarity) =====
# ==================================================================
# All functions below are NEW and ADDITIVE. They write to the new
# analytics.* schema (see SQL/analytics_schema.sql) and never touch
# the legacy user_sessions / page_view_logs tables.
#
# Public functions (do NOT rename — pages depend on these):
#   - log_pageview_start(...)        -> int pageview_id
#   - log_pageview_duration(pageview_id, duration_sec)
#   - log_event(...)
#   - log_error(...)
#   - log_event_batch([...])
#   - aggregate_heatmap_daily(date)
# ==================================================================


def _safe_int(v, default=None):
    try:
        if v is None or v == "":
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _truncate(s, n):
    if s is None:
        return None
    s = str(s)
    return s if len(s) <= n else s[:n]


# ------------------------------------------------------------------
# Pageview lifecycle
# ------------------------------------------------------------------
def log_pageview_start(
    user_id: str,
    dept: str,
    page_path: str,
    page_name: str = None,
    referrer: str = None,
    user_agent: str = None,
    viewport_w: int = None,
    viewport_h: int = None,
    session_id: int = None,
) -> int:
    """Insert a new analytics_pageview row, return its id.

    Caller (typically ui.analytics.inject_tracker) should stash the
    returned id in st.session_state so subsequent events / the unload
    duration can reference it.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO analytics.analytics_pageview (
                session_id, user_id, dept, page_path, page_name,
                referrer, user_agent, viewport_w, viewport_h, started_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING pageview_id;
            """,
            (
                session_id,
                user_id,
                dept,
                page_path,
                page_name,
                _truncate(referrer, 1000),
                _truncate(user_agent, 500),
                _safe_int(viewport_w),
                _safe_int(viewport_h),
            ),
        )
        pv_id = cur.fetchone()[0]
        conn.commit()
        return int(pv_id)
    finally:
        cur.close()
        conn.close()


def log_pageview_duration(pageview_id: int, duration_sec: int):
    """Close out an open pageview row with its measured duration."""
    if not pageview_id:
        return
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE analytics.analytics_pageview
            SET ended_at = NOW(),
                duration_sec = %s
            WHERE pageview_id = %s
              AND ended_at IS NULL;
            """,
            (_safe_int(duration_sec, 0), int(pageview_id)),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------------
# Generic events (click / scroll / submit / rage / dead / custom)
# ------------------------------------------------------------------
def log_event(
    user_id: str,
    page_path: str,
    event_type: str,
    element_id: str = None,
    element_label: str = None,
    position_x: int = None,
    position_y: int = None,
    viewport_w: int = None,
    viewport_h: int = None,
    scroll_depth_pct: int = None,
    pageview_id: int = None,
    session_id: int = None,
    extra: dict = None,
):
    """Single-event insert. Use log_event_batch() for high-volume flushes."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO analytics.analytics_event (
                pageview_id, session_id, user_id, page_path, event_type,
                element_id, element_label, position_x, position_y,
                viewport_w, viewport_h, scroll_depth_pct, extra, ts
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, NOW()
            );
            """,
            (
                pageview_id,
                session_id,
                user_id,
                page_path,
                event_type,
                _truncate(element_id, 200),
                _truncate(element_label, 500),
                _safe_int(position_x),
                _safe_int(position_y),
                _safe_int(viewport_w),
                _safe_int(viewport_h),
                _safe_int(scroll_depth_pct),
                Json(extra) if extra else None,
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def log_event_batch(events: list):
    """Insert many events in a single round trip.

    Each event is a dict with keys matching log_event() params plus
    page_path / event_type. user_id, pageview_id, session_id are required
    on each row (the JS sender attaches them).
    """
    if not events:
        return

    rows = []
    for e in events:
        rows.append((
            e.get("pageview_id"),
            e.get("session_id"),
            e.get("user_id"),
            e.get("page_path") or "",
            e.get("event_type") or "custom",
            _truncate(e.get("element_id"), 200),
            _truncate(e.get("element_label"), 500),
            _safe_int(e.get("position_x")),
            _safe_int(e.get("position_y")),
            _safe_int(e.get("viewport_w")),
            _safe_int(e.get("viewport_h")),
            _safe_int(e.get("scroll_depth_pct")),
            Json(e.get("extra")) if e.get("extra") else None,
        ))

    conn = get_conn()
    cur = conn.cursor()
    try:
        # executemany() is fine for our volume (events are batched in JS,
        # and Streamlit reruns naturally throttle dispatch).
        cur.executemany(
            """
            INSERT INTO analytics.analytics_event (
                pageview_id, session_id, user_id, page_path, event_type,
                element_id, element_label, position_x, position_y,
                viewport_w, viewport_h, scroll_depth_pct, extra, ts
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, NOW()
            );
            """,
            rows,
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------
def log_error(
    user_id: str,
    page_path: str,
    message: str,
    stack: str = None,
    source: str = None,
    line_no: int = None,
    col_no: int = None,
    user_agent: str = None,
    pageview_id: int = None,
    session_id: int = None,
):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO analytics.analytics_error (
                pageview_id, session_id, user_id, page_path,
                message, stack, source, line_no, col_no, user_agent, ts
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, NOW()
            );
            """,
            (
                pageview_id,
                session_id,
                user_id,
                page_path,
                _truncate(message, 2000),
                _truncate(stack, 8000),
                _truncate(source, 1000),
                _safe_int(line_no),
                _safe_int(col_no),
                _truncate(user_agent, 500),
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def log_error_batch(errors: list):
    if not errors:
        return
    rows = []
    for e in errors:
        rows.append((
            e.get("pageview_id"),
            e.get("session_id"),
            e.get("user_id"),
            e.get("page_path") or "",
            _truncate(e.get("message"), 2000),
            _truncate(e.get("stack"), 8000),
            _truncate(e.get("source"), 1000),
            _safe_int(e.get("line_no")),
            _safe_int(e.get("col_no")),
            _truncate(e.get("user_agent"), 500),
        ))
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.executemany(
            """
            INSERT INTO analytics.analytics_error (
                pageview_id, session_id, user_id, page_path,
                message, stack, source, line_no, col_no, user_agent, ts
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, NOW()
            );
            """,
            rows,
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ------------------------------------------------------------------
# Heatmap daily aggregation — batch job
# ------------------------------------------------------------------
def aggregate_heatmap_daily(target_date):
    """Roll up raw click events into 50x50 grid bins per page for one day.

    Idempotent: re-running for the same date deletes that date's rows
    first, so it's safe to run from a cron / scripts/ dir on a schedule
    or from the admin UI on demand.

    target_date: datetime.date or 'YYYY-MM-DD' string
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM analytics.analytics_click_heatmap_agg WHERE bucket_date = %s;",
            (target_date,),
        )
        cur.execute(
            """
            INSERT INTO analytics.analytics_click_heatmap_agg (
                page_path, grid_x, grid_y,
                click_count, rage_click_count, dead_click_count,
                bucket_date
            )
            SELECT
                page_path,
                FLOOR(position_x / 50)::int  AS grid_x,
                FLOOR(position_y / 50)::int  AS grid_y,
                SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END)::int AS click_count,
                SUM(CASE WHEN event_type = 'rage_click' THEN 1 ELSE 0 END)::int AS rage_click_count,
                SUM(CASE WHEN event_type = 'dead_click' THEN 1 ELSE 0 END)::int AS dead_click_count,
                %s::date
            FROM analytics.analytics_event
            WHERE event_type IN ('click', 'rage_click', 'dead_click')
              AND position_x IS NOT NULL
              AND position_y IS NOT NULL
              AND DATE(ts) = %s
            GROUP BY page_path, grid_x, grid_y;
            """,
            (target_date, target_date),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


