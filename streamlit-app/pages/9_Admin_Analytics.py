import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date, timedelta

from auth_guard import require_login
from tracking import get_conn


def get_user_role(user_email: str) -> str | None:
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT role
            FROM users
            WHERE email = %s;
            """,
            (user_email,)
        )

        row = cur.fetchone()
        return row[0] if row else None

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ==================================================
# 로그인 및 관리자 권한 체크
# ==================================================
require_login(
    page_name="admin_analytics",
    page_path="pages/9_Admin_Analytics.py"
)

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

from ui.analytics import inject_tracker
inject_tracker(page_name="9_Admin_Analytics", page_path="pages/9_Admin_Analytics.py")

user_email = st.session_state.get("user_email")

if not user_email:
    st.error("로그인 정보가 없습니다. 다시 로그인해주세요.")
    st.stop()

user_role = st.session_state.get("role")
if not user_role:
    user_role = get_user_role(user_email)
    st.session_state.role = user_role

if user_role != "admin":
    st.error("관리자만 접근할 수 있습니다.")
    st.stop()

# ==================================================
# 유틸 함수
# ==================================================
def run_query(query: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


def format_duration(seconds):
    if pd.isna(seconds):
        return "-"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}시간 {m}분 {s}초"
    if m > 0:
        return f"{m}분 {s}초"
    return f"{s}초"


def download_df_button(df: pd.DataFrame, filename: str, label: str):
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv"
    )


# ==================================================
# 페이지 헤더 — preview sec-admin 와 정렬: vit-top-strip + flat page-head
# (이전 rounded card-style 헤더 제거, 'rectangles only' 원칙 준수)
# ==================================================
from ui.vitals.components import render_top_strip, render_sub_head
render_top_strip()
st.markdown(
    """
    <style>
    .vit-page-head {
        /* Vitals 'rectangles only' — radius / shadow 제거. left wine bar 만 유지. */
        background: var(--card-bg, #FFFFFF);
        border: 1px solid var(--border, #E5E7EB);
        border-left: 4px solid var(--primary, #A50034);
        padding: 18px 22px;
        margin-bottom: 14px;
    }
    .vit-page-head h1 {
        margin: 0;
        font-family: 'LG EI Headline', 'LG EI Text', sans-serif;
        font-size: 22px; font-weight: 700; letter-spacing:-0.01em;
        color: var(--ink-body, #1F2430);
    }
    .vit-page-head .sub {
        margin-top: 4px;
        font-size: 12px; color: var(--ink-muted, #6B7280);
    }
    /* Admin 카드 / 메트릭 컨테이너 — Vitals 토큰 정렬 (radius 제거) */
    div[data-testid="stMetric"] {
        background: var(--card-bg, #FFFFFF);
        border: 1px solid var(--border, #E5E7EB);
        padding: 12px 14px;
        color: var(--ink-body, #1F2430);
    }
    div[data-testid="stMetric"] label { color: var(--ink-muted, #6B7280) !important; }
    /* status semantic — 정상/경고/위험 라벨 */
    .vit-status-good { color: var(--status-good, #1F8B4C); font-weight: 700; }
    .vit-status-warn { color: var(--status-warn, #B57F1B); font-weight: 700; }
    .vit-status-bad  { color: var(--status-bad,  #B23A48); font-weight: 700; }
    /* DataFrame / Table — soft 토큰 (radius 제거) */
    div[data-testid="stDataFrame"] { background: var(--soft, #F1F3F5); }
    </style>
    <div class="vit-page-head">
        <h1>관리자 분석 대시보드</h1>
        <div class="sub">사용자 로그인 · 페이지 조회 로그 기반 분석</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# 필터
# ==================================================
today = date.today()
default_start = today - timedelta(days=30)

c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    start_date = st.date_input("시작일", value=default_start)

with c2:
    end_date = st.date_input("종료일", value=today)

with c3:
    dept_df = run_query(
        """
        SELECT DISTINCT department
        FROM users
        WHERE department IS NOT NULL
        ORDER BY department;
        """
    )
    dept_options = ["전체"] + dept_df["department"].dropna().tolist()
    selected_dept = st.selectbox("부서", dept_options)

if start_date > end_date:
    st.error("시작일이 종료일보다 클 수 없습니다.")
    st.stop()

session_params = [start_date, end_date]
view_params = [start_date, end_date]

dept_filter_sessions = ""
dept_filter_views = ""

if selected_dept != "전체":
    dept_filter_sessions = " AND department = %s "
    dept_filter_views = " AND department = %s "
    session_params.append(selected_dept)
    view_params.append(selected_dept)

# ==================================================
# KPI
# ==================================================
kpi_query = f"""
SELECT
    COUNT(*) AS total_sessions,
    COUNT(DISTINCT user_email) AS unique_users,
    COALESCE(AVG(session_duration_sec), 0) AS avg_session_duration_sec
FROM user_sessions
WHERE DATE(login_at) BETWEEN %s AND %s
{dept_filter_sessions}
"""

view_kpi_query = f"""
SELECT
    COUNT(*) AS total_page_views
FROM page_view_logs
WHERE DATE(viewed_at) BETWEEN %s AND %s
{dept_filter_views}
"""

kpi_df = run_query(kpi_query, tuple(session_params))
view_kpi_df = run_query(view_kpi_query, tuple(view_params))

total_sessions = int(kpi_df.iloc[0]["total_sessions"]) if not kpi_df.empty else 0
unique_users = int(kpi_df.iloc[0]["unique_users"]) if not kpi_df.empty else 0
avg_session_duration_sec = float(kpi_df.iloc[0]["avg_session_duration_sec"]) if not kpi_df.empty else 0
total_page_views = int(view_kpi_df.iloc[0]["total_page_views"]) if not view_kpi_df.empty else 0

# ==================================================
# KPI 카드
# ==================================================
k1, k2, k3, k4 = st.columns(4)
k1.metric("총 로그인 수", f"{total_sessions:,}")
k2.metric("유니크 사용자", f"{unique_users:,}")
k3.metric("총 페이지 조회", f"{total_page_views:,}")
k4.metric("평균 세션 시간", format_duration(avg_session_duration_sec))

st.divider()

# ==================================================
# 탭
# ==================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab_flow, tab_heat, tab_err, tab_sess = st.tabs([
    "개요",
    "일/주/월 통계",
    "페이지 분석",
    "팀 분석",
    "사용자 분석",
    "원본 로그",
    "User Flow",
    "Heatmap",
    "Errors",
    "Sessions",
])

# ==================================================
# TAB 1. 개요
# ==================================================
with tab1:
    st.subheader("일별 방문 추이")

    daily_query = f"""
    SELECT
        DATE(login_at) AS day,
        COUNT(*) AS session_count,
        COUNT(DISTINCT user_email) AS unique_user_count
    FROM user_sessions
    WHERE DATE(login_at) BETWEEN %s AND %s
    {dept_filter_sessions}
    GROUP BY DATE(login_at)
    ORDER BY day;
    """

    daily_df = run_query(daily_query, tuple(session_params))

    if not daily_df.empty:
        fig = px.line(
            daily_df,
            x="day",
            y=["session_count", "unique_user_count"],
            markers=True,
            labels={
                "day": "날짜",
                "value": "수",
                "variable": "지표"
            },
            title="일별 로그인 수 / 유니크 사용자 수"
        )
        st.plotly_chart(fig, use_container_width=True)

        show_df = daily_df.rename(columns={
            "day": "날짜",
            "session_count": "로그인 수",
            "unique_user_count": "유니크 사용자 수"
        })
        st.dataframe(show_df, use_container_width=True)
    else:
        st.info("해당 기간 데이터가 없습니다.")

    render_sub_head("TOP 10 페이지", "조회 빈도")
    top_page_query = f"""
    SELECT
        page_name,
        COUNT(*) AS total_views
    FROM page_view_logs
    WHERE DATE(viewed_at) BETWEEN %s AND %s
    {dept_filter_views}
    GROUP BY page_name
    ORDER BY total_views DESC
    LIMIT 10;
    """
    top_page_df = run_query(top_page_query, tuple(view_params))

    if not top_page_df.empty:
        fig = px.bar(
            top_page_df,
            x="page_name",
            y="total_views",
            text="total_views",
            title="TOP 10 페이지 조회 수"
        )
        st.plotly_chart(fig, use_container_width=True)

    render_sub_head("TOP 10 사용자", "활성도")
    top_user_query = f"""
    SELECT
        user_email,
        COUNT(*) AS total_views
    FROM page_view_logs
    WHERE DATE(viewed_at) BETWEEN %s AND %s
    {dept_filter_views}
    GROUP BY user_email
    ORDER BY total_views DESC
    LIMIT 10;
    """
    top_user_df = run_query(top_user_query, tuple(view_params))

    if not top_user_df.empty:
        fig = px.bar(
            top_user_df,
            x="user_email",
            y="total_views",
            text="total_views",
            title="TOP 10 사용자 조회 수"
        )
        st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 2. 일/주/월 통계
# ==================================================
with tab2:
    subtab1, subtab2, subtab3 = st.tabs(["일별", "주별", "월별"])

    with subtab1:
        q = f"""
        SELECT
            DATE(login_at) AS day,
            COUNT(*) AS login_count,
            COUNT(DISTINCT user_email) AS unique_users
        FROM user_sessions
        WHERE DATE(login_at) BETWEEN %s AND %s
        {dept_filter_sessions}
        GROUP BY DATE(login_at)
        ORDER BY day;
        """
        df = run_query(q, tuple(session_params))

        if not df.empty:
            show_df = df.rename(columns={
                "day": "날짜",
                "login_count": "로그인 수",
                "unique_users": "유니크 사용자 수"
            })
            st.dataframe(show_df, use_container_width=True)
            download_df_button(show_df, "daily_stats.csv", "일별 통계 다운로드")
        else:
            st.info("데이터가 없습니다.")

    with subtab2:
        q = f"""
        SELECT
            DATE_TRUNC('week', login_at)::date AS week_start,
            COUNT(*) AS login_count,
            COUNT(DISTINCT user_email) AS unique_users
        FROM user_sessions
        WHERE DATE(login_at) BETWEEN %s AND %s
        {dept_filter_sessions}
        GROUP BY DATE_TRUNC('week', login_at)
        ORDER BY week_start;
        """
        df = run_query(q, tuple(session_params))

        if not df.empty:
            show_df = df.rename(columns={
                "week_start": "주 시작일",
                "login_count": "로그인 수",
                "unique_users": "유니크 사용자 수"
            })
            st.dataframe(show_df, use_container_width=True)
            download_df_button(show_df, "weekly_stats.csv", "주별 통계 다운로드")
        else:
            st.info("데이터가 없습니다.")

    with subtab3:
        q = f"""
        SELECT
            DATE_TRUNC('month', login_at)::date AS month_start,
            COUNT(*) AS login_count,
            COUNT(DISTINCT user_email) AS unique_users
        FROM user_sessions
        WHERE DATE(login_at) BETWEEN %s AND %s
        {dept_filter_sessions}
        GROUP BY DATE_TRUNC('month', login_at)
        ORDER BY month_start;
        """
        df = run_query(q, tuple(session_params))

        if not df.empty:
            show_df = df.rename(columns={
                "month_start": "월 시작일",
                "login_count": "로그인 수",
                "unique_users": "유니크 사용자 수"
            })
            st.dataframe(show_df, use_container_width=True)
            download_df_button(show_df, "monthly_stats.csv", "월별 통계 다운로드")
        else:
            st.info("데이터가 없습니다.")

# ==================================================
# TAB 3. 페이지 분석
# ==================================================
with tab3:
    st.subheader("페이지별 조회 수")

    page_query = f"""
    SELECT
        page_name,
        COUNT(*) AS total_views
    FROM page_view_logs
    WHERE DATE(viewed_at) BETWEEN %s AND %s
    {dept_filter_views}
    GROUP BY page_name
    ORDER BY total_views DESC;
    """

    page_df = run_query(page_query, tuple(view_params))

    if not page_df.empty:
        fig = px.bar(
            page_df,
            x="page_name",
            y="total_views",
            text="total_views",
            title="페이지별 조회 수"
        )
        st.plotly_chart(fig, use_container_width=True)

        show_df = page_df.rename(columns={
            "page_name": "페이지명",
            "total_views": "조회 수"
        })
        st.dataframe(show_df, use_container_width=True)
        download_df_button(show_df, "page_stats.csv", "페이지 통계 다운로드")
    else:
        st.info("페이지 조회 데이터가 없습니다.")

# ==================================================
# TAB 4. 팀 분석
# ==================================================
with tab4:
    st.subheader("팀별 페이지 조회 현황")

    team_page_query = """
    SELECT
        department,
        page_name,
        COUNT(*) AS total_views
    FROM page_view_logs
    WHERE DATE(viewed_at) BETWEEN %s AND %s
    """

    team_page_params = [start_date, end_date]

    if selected_dept != "전체":
        team_page_query += " AND department = %s "
        team_page_params.append(selected_dept)

    team_page_query += """
    GROUP BY department, page_name
    ORDER BY department, total_views DESC;
    """

    team_page_df = run_query(team_page_query, tuple(team_page_params))

    if not team_page_df.empty:
        show_df = team_page_df.rename(columns={
            "department": "부서",
            "page_name": "페이지명",
            "total_views": "조회 수"
        })
        st.dataframe(show_df, use_container_width=True)
        download_df_button(show_df, "team_page_stats.csv", "팀별 페이지 조회 다운로드")

        render_sub_head("팀 × 페이지 조회 매트릭스", "팀별 페이지 활용도")
        pivot_df = team_page_df.pivot_table(
            index="department",
            columns="page_name",
            values="total_views",
            aggfunc="sum",
            fill_value=0
        )

        st.dataframe(pivot_df, use_container_width=True)

        heatmap_df = pivot_df.reset_index().melt(
            id_vars="department",
            var_name="page_name",
            value_name="views"
        )

        fig = px.density_heatmap(
            heatmap_df,
            x="page_name",
            y="department",
            z="views",
            color_continuous_scale="Reds",
            title="팀 × 페이지 조회 히트맵"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("팀별 데이터가 없습니다.")

# ==================================================
# TAB 5. 사용자 분석
# ==================================================
with tab5:
    st.subheader("사용자별 페이지 조회 현황")

    user_page_query = """
    SELECT
        user_email,
        department,
        page_name,
        COUNT(*) AS total_views
    FROM page_view_logs
    WHERE DATE(viewed_at) BETWEEN %s AND %s
    """

    user_page_params = [start_date, end_date]

    if selected_dept != "전체":
        user_page_query += " AND department = %s "
        user_page_params.append(selected_dept)

    user_page_query += """
    GROUP BY user_email, department, page_name
    ORDER BY user_email, total_views DESC;
    """

    user_page_df = run_query(user_page_query, tuple(user_page_params))

    if not user_page_df.empty:
        show_df = user_page_df.rename(columns={
            "user_email": "사용자 이메일",
            "department": "부서",
            "page_name": "페이지명",
            "total_views": "조회 수"
        })
        st.dataframe(show_df, use_container_width=True)
        download_df_button(show_df, "user_page_stats.csv", "사용자별 조회 다운로드")

        render_sub_head("사용자별 총 조회 TOP 20", "전체 기간")
        user_total_df = (
            user_page_df.groupby(["user_email", "department"], as_index=False)["total_views"]
            .sum()
            .sort_values("total_views", ascending=False)
            .head(20)
        )

        fig = px.bar(
            user_total_df,
            x="user_email",
            y="total_views",
            color="department",
            text="total_views",
            title="사용자별 총 조회 TOP 20"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("사용자별 데이터가 없습니다.")

# ==================================================
# TAB 6. 원본 로그
# ==================================================
with tab6:
    log_subtab1, log_subtab2 = st.tabs(["로그인 로그", "페이지 조회 로그"])

    with log_subtab1:
        st.subheader("최근 로그인 로그")

        recent_session_query = """
        SELECT
            user_email,
            department,
            login_at,
            logout_at,
            session_end_reason,
            session_duration_sec
        FROM user_sessions
        WHERE DATE(login_at) BETWEEN %s AND %s
        """

        recent_session_params = [start_date, end_date]

        if selected_dept != "전체":
            recent_session_query += " AND department = %s "
            recent_session_params.append(selected_dept)

        recent_session_query += """
        ORDER BY login_at DESC
        LIMIT 300;
        """

        recent_session_df = run_query(recent_session_query, tuple(recent_session_params))

        if not recent_session_df.empty:
            recent_session_df["session_duration_sec"] = recent_session_df["session_duration_sec"].apply(format_duration)

            show_df = recent_session_df.rename(columns={
                "user_email": "사용자 이메일",
                "department": "부서",
                "login_at": "로그인 시각",
                "logout_at": "로그아웃 시각",
                "session_end_reason": "종료 사유",
                "session_duration_sec": "세션 시간"
            })

            st.dataframe(show_df, use_container_width=True)
            download_df_button(show_df, "recent_login_logs.csv", "로그인 로그 다운로드")
        else:
            st.info("로그인 로그가 없습니다.")

    with log_subtab2:
        st.subheader("최근 페이지 조회 로그")

        recent_view_query = """
        SELECT
            user_email,
            department,
            page_name,
            page_path,
            viewed_at
        FROM page_view_logs
        WHERE DATE(viewed_at) BETWEEN %s AND %s
        """

        recent_view_params = [start_date, end_date]

        if selected_dept != "전체":
            recent_view_query += " AND department = %s "
            recent_view_params.append(selected_dept)

        recent_view_query += """
        ORDER BY viewed_at DESC
        LIMIT 300;
        """

        recent_view_df = run_query(recent_view_query, tuple(recent_view_params))

        if not recent_view_df.empty:
            show_df = recent_view_df.rename(columns={
                "user_email": "사용자 이메일",
                "department": "부서",
                "page_name": "페이지명",
                "page_path": "페이지 경로",
                "viewed_at": "조회 시각"
            })

            st.dataframe(show_df, use_container_width=True)
            download_df_button(show_df, "recent_page_view_logs.csv", "페이지 조회 로그 다운로드")
        else:
            st.info("페이지 조회 로그가 없습니다.")


# ==================================================================
# ===== Vitals self-hosted analytics tabs (additive) ===============
# ==================================================================
# These tabs read the new analytics.* schema. They are gracefully
# defensive — if the schema hasn't been migrated yet they show a
# friendly hint instead of an exception.
# ==================================================================
def _analytics_table_exists(table_name: str) -> bool:
    try:
        df = run_query(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'analytics' AND table_name = %s
            LIMIT 1;
            """,
            (table_name,),
        )
        return not df.empty
    except Exception:
        return False


_HAS_ANALYTICS = _analytics_table_exists("analytics_pageview")


# ------------------------------------------------------------------
# TAB. User Flow  — page-to-page transitions
# ------------------------------------------------------------------
with tab_flow:
    st.subheader("페이지 간 이동 분석 (User Flow)")
    if not _HAS_ANALYTICS:
        st.info("analytics 스키마가 아직 적용되지 않았습니다. SQL/analytics_schema.sql 을 실행해 주세요.")
    else:
        flow_query = f"""
        WITH ordered AS (
            SELECT
                user_id,
                session_id,
                page_path,
                started_at,
                LEAD(page_path) OVER (PARTITION BY user_id, session_id ORDER BY started_at) AS next_path
            FROM analytics.analytics_pageview
            WHERE DATE(started_at) BETWEEN %s AND %s
              {('AND dept = %s' if selected_dept != '전체' else '')}
        )
        SELECT
            page_path AS from_page,
            next_path AS to_page,
            COUNT(*) AS transitions
        FROM ordered
        WHERE next_path IS NOT NULL
        GROUP BY page_path, next_path
        ORDER BY transitions DESC
        LIMIT 200;
        """
        flow_params = [start_date, end_date]
        if selected_dept != "전체":
            flow_params.append(selected_dept)
        flow_df = run_query(flow_query, tuple(flow_params))

        if flow_df.empty:
            st.info("이동 데이터가 아직 없습니다.")
        else:
            st.markdown("#### TOP 페이지 전환")
            st.dataframe(
                flow_df.rename(columns={
                    "from_page": "이전 페이지",
                    "to_page": "다음 페이지",
                    "transitions": "이동 횟수",
                }),
                use_container_width=True,
            )

            # Sankey via plotly (lightweight — no new dep)
            try:
                import plotly.graph_objects as go
                top = flow_df.head(40).copy()
                nodes = list(pd.unique(pd.concat([top["from_page"], top["to_page"]])))
                idx = {n: i for i, n in enumerate(nodes)}
                fig = go.Figure(go.Sankey(
                    node=dict(label=nodes, pad=12, thickness=14),
                    link=dict(
                        source=top["from_page"].map(idx).tolist(),
                        target=top["to_page"].map(idx).tolist(),
                        value=top["transitions"].tolist(),
                    ),
                ))
                fig.update_layout(title_text="페이지 흐름 (TOP 40)", font_size=11, height=520)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.caption(f"Sankey 렌더 생략: {e}")


# ------------------------------------------------------------------
# TAB. Heatmap  — click density over a chosen page
# ------------------------------------------------------------------
with tab_heat:
    st.subheader("클릭 히트맵")
    if not _HAS_ANALYTICS:
        st.info("analytics 스키마가 아직 적용되지 않았습니다. SQL/analytics_schema.sql 을 실행해 주세요.")
    else:
        page_choices_df = run_query(
            """
            SELECT page_path, COUNT(*) AS clicks
            FROM analytics.analytics_event
            WHERE event_type = 'click'
              AND DATE(ts) BETWEEN %s AND %s
            GROUP BY page_path
            ORDER BY clicks DESC
            LIMIT 50;
            """,
            (start_date, end_date),
        )

        if page_choices_df.empty:
            st.info("클릭 데이터가 아직 수집되지 않았습니다.")
        else:
            chosen_page = st.selectbox(
                "페이지 선택",
                page_choices_df["page_path"].tolist(),
                key="heatmap_page_choice",
            )

            # Prefer the precomputed daily aggregate; fall back to live events.
            agg_df = run_query(
                """
                SELECT grid_x, grid_y,
                       SUM(click_count)      AS click_count,
                       SUM(rage_click_count) AS rage_click_count,
                       SUM(dead_click_count) AS dead_click_count
                FROM analytics.analytics_click_heatmap_agg
                WHERE page_path = %s
                  AND bucket_date BETWEEN %s AND %s
                GROUP BY grid_x, grid_y;
                """,
                (chosen_page, start_date, end_date),
            )

            if agg_df.empty:
                # Fallback — bin live events on the fly.
                agg_df = run_query(
                    """
                    SELECT (position_x / 50)::int AS grid_x,
                           (position_y / 50)::int AS grid_y,
                           SUM(CASE WHEN event_type='click'      THEN 1 ELSE 0 END) AS click_count,
                           SUM(CASE WHEN event_type='rage_click' THEN 1 ELSE 0 END) AS rage_click_count,
                           SUM(CASE WHEN event_type='dead_click' THEN 1 ELSE 0 END) AS dead_click_count
                    FROM analytics.analytics_event
                    WHERE page_path = %s
                      AND event_type IN ('click','rage_click','dead_click')
                      AND position_x IS NOT NULL AND position_y IS NOT NULL
                      AND DATE(ts) BETWEEN %s AND %s
                    GROUP BY 1, 2;
                    """,
                    (chosen_page, start_date, end_date),
                )
                st.caption("일별 집계 캐시가 없어 raw event 를 직접 집계했습니다 — 빠른 렌더링을 위해 `aggregate_heatmap_daily` 배치를 권장합니다.")

            if agg_df.empty:
                st.info("이 페이지의 클릭 데이터가 없습니다.")
            else:
                pivot = agg_df.pivot_table(
                    index="grid_y",
                    columns="grid_x",
                    values="click_count",
                    aggfunc="sum",
                    fill_value=0,
                ).sort_index()
                fig = px.imshow(
                    pivot.values,
                    labels=dict(x="X (50px bin)", y="Y (50px bin)", color="클릭"),
                    x=pivot.columns.tolist(),
                    y=pivot.index.tolist(),
                    color_continuous_scale="Reds",
                    aspect="auto",
                    title=f"클릭 히트맵 — {chosen_page}",
                )
                # Match screen orientation: top-of-page = top of chart.
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

                tot = int(agg_df["click_count"].sum())
                rage = int(agg_df["rage_click_count"].sum())
                dead = int(agg_df["dead_click_count"].sum())
                m1, m2, m3 = st.columns(3)
                m1.metric("총 클릭", f"{tot:,}")
                m2.metric("Rage clicks", f"{rage:,}")
                m3.metric("Dead clicks", f"{dead:,}")


# ------------------------------------------------------------------
# TAB. Errors  — recent JS errors grouped by message + page
# ------------------------------------------------------------------
with tab_err:
    st.subheader("JavaScript 에러")
    if not _HAS_ANALYTICS:
        st.info("analytics 스키마가 아직 적용되지 않았습니다. SQL/analytics_schema.sql 을 실행해 주세요.")
    else:
        err_group_df = run_query(
            """
            SELECT
                LEFT(COALESCE(message, ''), 200) AS message,
                page_path,
                COUNT(*) AS occurrences,
                COUNT(DISTINCT user_id) AS users_affected,
                MAX(ts) AS last_seen
            FROM analytics.analytics_error
            WHERE DATE(ts) BETWEEN %s AND %s
            GROUP BY 1, 2
            ORDER BY occurrences DESC
            LIMIT 100;
            """,
            (start_date, end_date),
        )

        if err_group_df.empty:
            st.success("기간 내 JavaScript 에러가 없습니다.")
        else:
            st.markdown("#### 메시지별 발생 (TOP 100)")
            st.dataframe(
                err_group_df.rename(columns={
                    "message": "메시지",
                    "page_path": "페이지",
                    "occurrences": "발생 횟수",
                    "users_affected": "영향 사용자",
                    "last_seen": "마지막 발생",
                }),
                use_container_width=True,
            )
            download_df_button(err_group_df, "errors_grouped.csv", "에러 그룹 다운로드")

            st.markdown("#### 최근 에러 100건")
            err_recent_df = run_query(
                """
                SELECT ts, user_id, page_path, message, source, line_no
                FROM analytics.analytics_error
                WHERE DATE(ts) BETWEEN %s AND %s
                ORDER BY ts DESC
                LIMIT 100;
                """,
                (start_date, end_date),
            )
            st.dataframe(err_recent_df, use_container_width=True)


# ------------------------------------------------------------------
# TAB. Sessions  — recent sessions w/ duration + pages visited
# ------------------------------------------------------------------
with tab_sess:
    st.subheader("최근 세션")
    if not _HAS_ANALYTICS:
        st.info("analytics 스키마가 아직 적용되지 않았습니다. SQL/analytics_schema.sql 을 실행해 주세요.")
    else:
        sess_query = """
        SELECT
            us.id AS session_id,
            us.user_email,
            us.department,
            us.login_at,
            us.logout_at,
            us.session_duration_sec,
            us.session_end_reason,
            COALESCE(pv.pages_visited, 0) AS pages_visited,
            COALESCE(pv.total_dwell_sec, 0) AS total_dwell_sec
        FROM user_sessions us
        LEFT JOIN (
            SELECT session_id,
                   COUNT(*) AS pages_visited,
                   SUM(COALESCE(duration_sec, 0)) AS total_dwell_sec
            FROM analytics.analytics_pageview
            GROUP BY session_id
        ) pv ON pv.session_id = us.id
        WHERE DATE(us.login_at) BETWEEN %s AND %s
        """
        sess_params = [start_date, end_date]
        if selected_dept != "전체":
            sess_query += " AND us.department = %s "
            sess_params.append(selected_dept)
        sess_query += " ORDER BY us.login_at DESC LIMIT 200;"

        sess_df = run_query(sess_query, tuple(sess_params))

        if sess_df.empty:
            st.info("세션 데이터가 없습니다.")
        else:
            display = sess_df.copy()
            display["session_duration_sec"] = display["session_duration_sec"].apply(format_duration)
            display["total_dwell_sec"] = display["total_dwell_sec"].apply(format_duration)
            st.dataframe(
                display.rename(columns={
                    "session_id": "세션ID",
                    "user_email": "사용자",
                    "department": "부서",
                    "login_at": "로그인",
                    "logout_at": "로그아웃",
                    "session_duration_sec": "세션 시간",
                    "session_end_reason": "종료 사유",
                    "pages_visited": "페이지 수",
                    "total_dwell_sec": "체류 시간 합",
                }),
                use_container_width=True,
            )

            st.markdown("#### 세션 타임라인 보기")
            sel = st.selectbox(
                "세션ID 선택",
                sess_df["session_id"].tolist(),
                format_func=lambda sid: f"#{sid} — {sess_df.loc[sess_df['session_id'] == sid, 'user_email'].iloc[0]}",
                key="session_timeline_pick",
            )
            if sel:
                tl_df = run_query(
                    """
                    SELECT page_name, page_path, started_at, ended_at, duration_sec
                    FROM analytics.analytics_pageview
                    WHERE session_id = %s
                    ORDER BY started_at;
                    """,
                    (int(sel),),
                )
                if tl_df.empty:
                    st.caption("이 세션에 대한 pageview 가 아직 기록되지 않았습니다.")
                else:
                    show = tl_df.copy()
                    show["duration_sec"] = show["duration_sec"].apply(format_duration)
                    st.dataframe(
                        show.rename(columns={
                            "page_name": "페이지명",
                            "page_path": "경로",
                            "started_at": "시작",
                            "ended_at": "종료",
                            "duration_sec": "체류",
                        }),
                        use_container_width=True,
                    )