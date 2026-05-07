import os
import sys
import sqlite3
import subprocess
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# =========================
# 사용자 설정
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "access_logs.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "access_stats_output")
EXCEL_PATH = os.path.join(OUTPUT_DIR, "access_stats_report.xlsx")

LOOKBACK_DAYS = 90     # 일간 통계 최근 N일
LOOKBACK_WEEKS = 26    # 주간 통계 최근 N주
LOOKBACK_MONTHS = 12   # 월간 통계 최근 N개월
OPEN_OUTPUT_FOLDER = False  # True면 완료 후 결과 폴더 자동 열기


# =========================
# 유틸 함수
# =========================
def set_korean_font():
    """Windows/PyCharm 환경에서 한글 폰트가 깨지지 않도록 설정"""
    candidate_fonts = [
        "Malgun Gothic",     # Windows
        "AppleGothic",       # macOS
        "NanumGothic",       # Linux/별도 설치
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]

    available = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in available:
            rcParams["font.family"] = font_name
            rcParams["axes.unicode_minus"] = False
            return font_name

    # 폰트를 못 찾더라도 실행은 계속
    rcParams["axes.unicode_minus"] = False
    return None



def ensure_output_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)



def read_access_log(db_path: str) -> pd.DataFrame:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB 파일이 없습니다: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT
                id,
                access_time,
                page_name,
                client_ip,
                forwarded_for,
                user_agent,
                host,
                url,
                session_key
            FROM access_log
            ORDER BY access_time
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if df.empty:
        raise ValueError("access_log 테이블에 데이터가 없습니다.")

    # 날짜 변환
    df["access_time"] = pd.to_datetime(df["access_time"], errors="coerce")
    df = df.dropna(subset=["access_time"]).copy()

    if df.empty:
        raise ValueError("access_time 변환 가능한 데이터가 없습니다.")

    # 기본 컬럼 정리
    df["page_name"] = df["page_name"].fillna("UNKNOWN").astype(str)
    df["client_ip"] = df["client_ip"].fillna("UNKNOWN").astype(str)

    # 파생 컬럼
    df["date"] = df["access_time"].dt.normalize()
    df["month"] = df["access_time"].dt.to_period("M").astype(str)

    iso = df["access_time"].dt.isocalendar()
    df["iso_year"] = iso["year"].astype(int)
    df["iso_week"] = iso["week"].astype(int)
    df["year_week"] = df["iso_year"].astype(str) + "-W" + df["iso_week"].astype(str).str.zfill(2)

    # ISO 주 시작일(월요일)
    df["week_start"] = df["access_time"] - pd.to_timedelta(df["access_time"].dt.weekday, unit="D")
    df["week_start"] = df["week_start"].dt.normalize()

    return df



def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("page_name", dropna=False)
          .agg(
              총접속수=("id", "count"),
              고유IP수=("client_ip", lambda x: x.nunique()),
              최초접속=("access_time", "min"),
              최근접속=("access_time", "max")
          )
          .reset_index()
          .sort_values(["총접속수", "page_name"], ascending=[False, True])
    )
    return summary



def build_daily_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = (
        df.groupby(["date", "page_name"], dropna=False)
          .agg(
              접속수=("id", "count"),
              고유IP수=("client_ip", lambda x: x.nunique())
          )
          .reset_index()
          .sort_values(["date", "page_name"])
    )
    daily_pivot = daily.pivot(index="date", columns="page_name", values="접속수").fillna(0).astype(int)
    return daily, daily_pivot



def build_weekly_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    weekly = (
        df.groupby(["week_start", "year_week", "page_name"], dropna=False)
          .agg(
              접속수=("id", "count"),
              고유IP수=("client_ip", lambda x: x.nunique())
          )
          .reset_index()
          .sort_values(["week_start", "page_name"])
    )
    weekly_pivot = weekly.pivot(index="year_week", columns="page_name", values="접속수").fillna(0).astype(int)
    return weekly, weekly_pivot



def build_monthly_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly = (
        df.groupby(["month", "page_name"], dropna=False)
          .agg(
              접속수=("id", "count"),
              고유IP수=("client_ip", lambda x: x.nunique())
          )
          .reset_index()
          .sort_values(["month", "page_name"])
    )
    monthly_pivot = monthly.pivot(index="month", columns="page_name", values="접속수").fillna(0).astype(int)
    return monthly, monthly_pivot



def save_excel_report(summary: pd.DataFrame,
                      daily: pd.DataFrame,
                      daily_pivot: pd.DataFrame,
                      weekly: pd.DataFrame,
                      weekly_pivot: pd.DataFrame,
                      monthly: pd.DataFrame,
                      monthly_pivot: pd.DataFrame,
                      excel_path: str):
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="요약", index=False)
        daily.to_excel(writer, sheet_name="일간통계", index=False)
        daily_pivot.to_excel(writer, sheet_name="일간통계_피벗")
        weekly.to_excel(writer, sheet_name="주간통계", index=False)
        weekly_pivot.to_excel(writer, sheet_name="주간통계_피벗")
        monthly.to_excel(writer, sheet_name="월간통계", index=False)
        monthly_pivot.to_excel(writer, sheet_name="월간통계_피벗")



def plot_overall_series(pivot_df: pd.DataFrame, title: str, xlabel: str, ylabel: str, output_path: str, chart_type: str = "line"):
    if pivot_df.empty:
        return

    plt.figure(figsize=(14, 6))
    if chart_type == "bar":
        pivot_df.plot(kind="bar", ax=plt.gca())
    else:
        pivot_df.plot(ax=plt.gca(), marker="o")

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, axis="y", alpha=0.3)
    plt.legend(title="페이지", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()



def plot_per_page_series(df_long: pd.DataFrame,
                         period_col: str,
                         value_col: str,
                         title_prefix: str,
                         xlabel: str,
                         ylabel: str,
                         output_dir: str,
                         chart_type: str = "line"):
    if df_long.empty:
        return

    for page_name in sorted(df_long["page_name"].dropna().unique()):
        page_df = df_long[df_long["page_name"] == page_name].copy()
        if page_df.empty:
            continue

        page_df = page_df.sort_values(period_col)
        safe_name = str(page_name).replace("/", "_").replace("\\", "_").replace(":", "_")
        output_path = os.path.join(output_dir, f"{safe_name}.png")

        plt.figure(figsize=(12, 5))
        if chart_type == "bar":
            plt.bar(page_df[period_col].astype(str), page_df[value_col])
        else:
            plt.plot(page_df[period_col].astype(str), page_df[value_col], marker="o")

        plt.title(f"{title_prefix} - {page_name}")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True, axis="y", alpha=0.3)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()



def trim_recent_daily(daily: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    if daily.empty:
        return daily.copy()
    max_date = pd.to_datetime(daily["date"].max())
    start_date = max_date - pd.Timedelta(days=lookback_days - 1)
    return daily[daily["date"] >= start_date].copy()



def trim_recent_weekly(weekly: pd.DataFrame, lookback_weeks: int) -> pd.DataFrame:
    if weekly.empty:
        return weekly.copy()
    max_week_start = pd.to_datetime(weekly["week_start"].max())
    start_week = max_week_start - pd.Timedelta(weeks=lookback_weeks - 1)
    return weekly[weekly["week_start"] >= start_week].copy()



def trim_recent_monthly(monthly: pd.DataFrame, lookback_months: int) -> pd.DataFrame:
    if monthly.empty:
        return monthly.copy()
    month_periods = pd.PeriodIndex(monthly["month"], freq="M")
    max_period = month_periods.max()
    min_period = max_period - (lookback_months - 1)
    keep_mask = month_periods >= min_period
    return monthly[keep_mask].copy()



def open_folder_windows(path: str):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"[안내] 결과 폴더 자동 열기에 실패했습니다: {e}")


# =========================
# 메인 실행
# =========================
def main():
    print("[시작] 접속 통계 리포트 생성을 시작합니다.")
    font_name = set_korean_font()
    if font_name:
        print(f"[정보] 한글 폰트 적용: {font_name}")
    else:
        print("[경고] 사용할 한글 폰트를 찾지 못했습니다. 일부 환경에서 그래프 한글이 깨질 수 있습니다.")

    ensure_output_dir(OUTPUT_DIR)
    charts_dir = os.path.join(OUTPUT_DIR, "charts")
    daily_dir = os.path.join(charts_dir, "daily")
    weekly_dir = os.path.join(charts_dir, "weekly")
    monthly_dir = os.path.join(charts_dir, "monthly")
    for path in [charts_dir, daily_dir, weekly_dir, monthly_dir]:
        ensure_output_dir(path)

    df = read_access_log(DB_PATH)
    print(f"[정보] 원본 로그 건수: {len(df):,}")
    print(f"[정보] 페이지 수: {df['page_name'].nunique():,}")
    print(f"[정보] 로그 기간: {df['access_time'].min()} ~ {df['access_time'].max()}")

    summary = build_summary(df)
    daily, daily_pivot_all = build_daily_stats(df)
    weekly, weekly_pivot_all = build_weekly_stats(df)
    monthly, monthly_pivot_all = build_monthly_stats(df)

    # 최근 구간만 그래프화
    daily_recent = trim_recent_daily(daily, LOOKBACK_DAYS)
    weekly_recent = trim_recent_weekly(weekly, LOOKBACK_WEEKS)
    monthly_recent = trim_recent_monthly(monthly, LOOKBACK_MONTHS)

    daily_recent_pivot = daily_recent.pivot(index="date", columns="page_name", values="접속수").fillna(0).astype(int) if not daily_recent.empty else pd.DataFrame()
    weekly_recent_pivot = weekly_recent.pivot(index="year_week", columns="page_name", values="접속수").fillna(0).astype(int) if not weekly_recent.empty else pd.DataFrame()
    monthly_recent_pivot = monthly_recent.pivot(index="month", columns="page_name", values="접속수").fillna(0).astype(int) if not monthly_recent.empty else pd.DataFrame()

    save_excel_report(
        summary=summary,
        daily=daily,
        daily_pivot=daily_pivot_all,
        weekly=weekly,
        weekly_pivot=weekly_pivot_all,
        monthly=monthly,
        monthly_pivot=monthly_pivot_all,
        excel_path=EXCEL_PATH,
    )
    print(f"[완료] 엑셀 리포트 저장: {EXCEL_PATH}")

    # 전체 그래프
    plot_overall_series(
        daily_recent_pivot,
        title=f"일간 접속 통계 (최근 {LOOKBACK_DAYS}일)",
        xlabel="일자",
        ylabel="접속 수",
        output_path=os.path.join(charts_dir, "overall_daily.png"),
        chart_type="line",
    )
    plot_overall_series(
        weekly_recent_pivot,
        title=f"주간 접속 통계 (최근 {LOOKBACK_WEEKS}주)",
        xlabel="주차",
        ylabel="접속 수",
        output_path=os.path.join(charts_dir, "overall_weekly.png"),
        chart_type="bar",
    )
    plot_overall_series(
        monthly_recent_pivot,
        title=f"월간 접속 통계 (최근 {LOOKBACK_MONTHS}개월)",
        xlabel="월",
        ylabel="접속 수",
        output_path=os.path.join(charts_dir, "overall_monthly.png"),
        chart_type="bar",
    )

    # 페이지별 그래프
    plot_per_page_series(
        daily_recent,
        period_col="date",
        value_col="접속수",
        title_prefix=f"일간 접속 통계 (최근 {LOOKBACK_DAYS}일)",
        xlabel="일자",
        ylabel="접속 수",
        output_dir=daily_dir,
        chart_type="line",
    )
    plot_per_page_series(
        weekly_recent,
        period_col="year_week",
        value_col="접속수",
        title_prefix=f"주간 접속 통계 (최근 {LOOKBACK_WEEKS}주)",
        xlabel="주차",
        ylabel="접속 수",
        output_dir=weekly_dir,
        chart_type="bar",
    )
    plot_per_page_series(
        monthly_recent,
        period_col="month",
        value_col="접속수",
        title_prefix=f"월간 접속 통계 (최근 {LOOKBACK_MONTHS}개월)",
        xlabel="월",
        ylabel="접속 수",
        output_dir=monthly_dir,
        chart_type="bar",
    )

    # 보조 CSV 저장(엑셀 외에도 바로 확인 가능하도록)
    summary.to_csv(os.path.join(OUTPUT_DIR, "summary.csv"), index=False, encoding="utf-8-sig")
    daily.to_csv(os.path.join(OUTPUT_DIR, "daily_stats.csv"), index=False, encoding="utf-8-sig")
    weekly.to_csv(os.path.join(OUTPUT_DIR, "weekly_stats.csv"), index=False, encoding="utf-8-sig")
    monthly.to_csv(os.path.join(OUTPUT_DIR, "monthly_stats.csv"), index=False, encoding="utf-8-sig")

    print(f"[완료] 그래프 폴더: {charts_dir}")
    print("[완료] 모든 통계 및 시각화 생성이 끝났습니다.")

    if OPEN_OUTPUT_FOLDER:
        open_folder_windows(OUTPUT_DIR)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[오류] {e}")
        raise
