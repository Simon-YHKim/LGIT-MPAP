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
# 페이지 헤더
# ==================================================
st.title("📊 관리자 분석 대시보드")
st.caption("사용자 로그인 / 페이지 조회 로그 기반 분석")

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "개요",
    "일/주/월 통계",
    "페이지 분석",
    "팀 분석",
    "사용자 분석",
    "원본 로그"
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

    st.markdown("### TOP 10 페이지")
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

    st.markdown("### TOP 10 사용자")
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

        st.markdown("### 팀 × 페이지 조회 매트릭스")
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

        st.markdown("### 사용자별 총 조회 TOP 20")
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