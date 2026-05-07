import os
import sqlite3
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


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
SAVE_OUTPUT_FILES = True   # True면 엑셀/CSV도 같이 저장
DEFAULT_THEME = "default"


# =========================
# 데이터 처리 함수
# =========================
def set_korean_font():
    candidate_fonts = [
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
    ]

    available = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in available:
            rcParams["font.family"] = font_name
            rcParams["axes.unicode_minus"] = False
            return font_name

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

    df["access_time"] = pd.to_datetime(df["access_time"], errors="coerce")
    df = df.dropna(subset=["access_time"]).copy()
    if df.empty:
        raise ValueError("access_time 변환 가능한 데이터가 없습니다.")

    df["page_name"] = df["page_name"].fillna("UNKNOWN").astype(str)
    df["client_ip"] = df["client_ip"].fillna("UNKNOWN").astype(str)

    df["date"] = df["access_time"].dt.normalize()
    df["month"] = df["access_time"].dt.to_period("M").astype(str)

    iso = df["access_time"].dt.isocalendar()
    df["iso_year"] = iso["year"].astype(int)
    df["iso_week"] = iso["week"].astype(int)
    df["year_week"] = df["iso_year"].astype(str) + "-W" + df["iso_week"].astype(str).str.zfill(2)

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
    summary["최초접속"] = summary["최초접속"].dt.strftime("%Y-%m-%d %H:%M:%S")
    summary["최근접속"] = summary["최근접속"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return summary



def build_daily_stats(df: pd.DataFrame):
    daily = (
        df.groupby(["date", "page_name"], dropna=False)
          .agg(
              접속수=("id", "count"),
              고유IP수=("client_ip", lambda x: x.nunique())
          )
          .reset_index()
          .sort_values(["date", "page_name"])
    )
    daily["date_str"] = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m-%d")
    daily_pivot = daily.pivot(index="date_str", columns="page_name", values="접속수").fillna(0).astype(int)
    return daily, daily_pivot



def build_weekly_stats(df: pd.DataFrame):
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



def build_monthly_stats(df: pd.DataFrame):
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



def save_output_files(summary, daily, daily_pivot, weekly, weekly_pivot, monthly, monthly_pivot):
    ensure_output_dir(OUTPUT_DIR)

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="요약", index=False)
        daily.to_excel(writer, sheet_name="일간통계", index=False)
        daily_pivot.to_excel(writer, sheet_name="일간통계_피벗")
        weekly.to_excel(writer, sheet_name="주간통계", index=False)
        weekly_pivot.to_excel(writer, sheet_name="주간통계_피벗")
        monthly.to_excel(writer, sheet_name="월간통계", index=False)
        monthly_pivot.to_excel(writer, sheet_name="월간통계_피벗")

    summary.to_csv(os.path.join(OUTPUT_DIR, "summary.csv"), index=False, encoding="utf-8-sig")
    daily.to_csv(os.path.join(OUTPUT_DIR, "daily_stats.csv"), index=False, encoding="utf-8-sig")
    weekly.to_csv(os.path.join(OUTPUT_DIR, "weekly_stats.csv"), index=False, encoding="utf-8-sig")
    monthly.to_csv(os.path.join(OUTPUT_DIR, "monthly_stats.csv"), index=False, encoding="utf-8-sig")


# =========================
# UI 헬퍼 함수
# =========================
def create_treeview(parent, dataframe: pd.DataFrame, show_index: bool = False):
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)

    df = dataframe.copy()
    if show_index:
        df = df.reset_index()

    columns = list(df.columns)
    tree = ttk.Treeview(frame, columns=columns, show="headings")

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    for col in columns:
        tree.heading(col, text=str(col))
        max_len = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)])
        width = min(max(80, max_len * 8), 260)
        tree.column(col, width=width, anchor="center")

    for _, row in df.iterrows():
        values = ["" if pd.isna(v) else str(v) for v in row.tolist()]
        tree.insert("", "end", values=values)

    return tree



def draw_chart(parent, x_values, y_map: dict, title: str, xlabel: str, ylabel: str, kind: str = "line"):
    fig = Figure(figsize=(10, 4.8), dpi=100)
    ax = fig.add_subplot(111)

    if kind == "bar":
        # grouped bar chart
        labels = list(map(str, x_values))
        n_series = max(1, len(y_map))
        x = list(range(len(labels)))
        total_width = 0.8
        bar_width = total_width / n_series
        offsets = [(-total_width / 2) + (i + 0.5) * bar_width for i in range(n_series)]

        for idx, (name, y_vals) in enumerate(y_map.items()):
            shifted_x = [xi + offsets[idx] for xi in x]
            ax.bar(shifted_x, y_vals, width=bar_width, label=str(name))
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    else:
        for name, y_vals in y_map.items():
            ax.plot(list(map(str, x_values)), y_vals, marker="o", label=str(name))
        ax.tick_params(axis="x", rotation=45)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(title="페이지")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.pack(fill="both", expand=True)
    return canvas



def dataframe_to_series_map(pivot_df: pd.DataFrame):
    x_values = list(pivot_df.index)
    y_map = {str(col): pivot_df[col].tolist() for col in pivot_df.columns}
    return x_values, y_map


# =========================
# 메인 UI
# =========================
class AccessStatsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("접속 통계 리포트")
        self.geometry("1550x930")
        self.minsize(1280, 760)

        try:
            ttk.Style(self).theme_use(DEFAULT_THEME)
        except Exception:
            pass

        self.summary = None
        self.daily = None
        self.daily_pivot = None
        self.weekly = None
        self.weekly_pivot = None
        self.monthly = None
        self.monthly_pivot = None
        self.daily_recent = None
        self.weekly_recent = None
        self.monthly_recent = None
        self.daily_recent_pivot = None
        self.weekly_recent_pivot = None
        self.monthly_recent_pivot = None

        self._build_layout()
        self.load_and_render()

    def _build_layout(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="DB 경로:").pack(side="left")
        self.db_path_var = tk.StringVar(value=DB_PATH)
        ttk.Entry(top, textvariable=self.db_path_var, width=80).pack(side="left", padx=(5, 10))
        ttk.Button(top, text="새로고침", command=self.load_and_render).pack(side="left")

        self.info_var = tk.StringVar(value="대기 중")
        ttk.Label(top, textvariable=self.info_var).pack(side="left", padx=(15, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _clear_notebook(self):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)

    def load_and_render(self):
        try:
            self._clear_notebook()
            set_korean_font()
            db_path = self.db_path_var.get().strip()
            df = read_access_log(db_path)

            self.summary = build_summary(df)
            self.daily, self.daily_pivot = build_daily_stats(df)
            self.weekly, self.weekly_pivot = build_weekly_stats(df)
            self.monthly, self.monthly_pivot = build_monthly_stats(df)

            self.daily_recent = trim_recent_daily(self.daily, LOOKBACK_DAYS)
            self.weekly_recent = trim_recent_weekly(self.weekly, LOOKBACK_WEEKS)
            self.monthly_recent = trim_recent_monthly(self.monthly, LOOKBACK_MONTHS)

            self.daily_recent_pivot = self.daily_recent.pivot(index="date_str", columns="page_name", values="접속수").fillna(0).astype(int) if not self.daily_recent.empty else pd.DataFrame()
            self.weekly_recent_pivot = self.weekly_recent.pivot(index="year_week", columns="page_name", values="접속수").fillna(0).astype(int) if not self.weekly_recent.empty else pd.DataFrame()
            self.monthly_recent_pivot = self.monthly_recent.pivot(index="month", columns="page_name", values="접속수").fillna(0).astype(int) if not self.monthly_recent.empty else pd.DataFrame()

            if SAVE_OUTPUT_FILES:
                save_output_files(
                    self.summary,
                    self.daily,
                    self.daily_pivot,
                    self.weekly,
                    self.weekly_pivot,
                    self.monthly,
                    self.monthly_pivot,
                )

            self._build_summary_tab(df)
            self._build_daily_tab()
            self._build_weekly_tab()
            self._build_monthly_tab()

            start_time = df["access_time"].min().strftime("%Y-%m-%d %H:%M:%S")
            end_time = df["access_time"].max().strftime("%Y-%m-%d %H:%M:%S")
            self.info_var.set(
                f"로그 {len(df):,}건 | 페이지 {df['page_name'].nunique():,}개 | 기간 {start_time} ~ {end_time}"
            )
        except Exception as e:
            self.info_var.set("오류 발생")
            traceback.print_exc()
            messagebox.showerror("오류", f"리포트를 생성하는 중 오류가 발생했습니다.\n\n{e}")

    def _build_summary_tab(self, raw_df: pd.DataFrame):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="요약")

        upper = ttk.Frame(tab, padding=8)
        upper.pack(fill="x")

        total_access = len(raw_df)
        unique_ip = raw_df["client_ip"].nunique()
        unique_page = raw_df["page_name"].nunique()
        latest_access = raw_df["access_time"].max().strftime("%Y-%m-%d %H:%M:%S")

        ttk.Label(upper, text=f"총 접속 수: {total_access:,}", font=(None, 11, "bold")).pack(side="left", padx=(0, 20))
        ttk.Label(upper, text=f"고유 IP 수: {unique_ip:,}", font=(None, 11, "bold")).pack(side="left", padx=(0, 20))
        ttk.Label(upper, text=f"페이지 수: {unique_page:,}", font=(None, 11, "bold")).pack(side="left", padx=(0, 20))
        ttk.Label(upper, text=f"최근 접속: {latest_access}", font=(None, 11, "bold")).pack(side="left")

        paned = ttk.Panedwindow(tab, orient="vertical")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        frame_table = ttk.Labelframe(paned, text="페이지별 요약 데이터", padding=6)
        frame_chart = ttk.Labelframe(paned, text="페이지별 총 접속 수", padding=6)
        paned.add(frame_table, weight=1)
        paned.add(frame_chart, weight=1)

        create_treeview(frame_table, self.summary)

        chart_df = self.summary[["page_name", "총접속수"]].copy()
        x_values = chart_df["page_name"].tolist()
        y_map = {"총접속수": chart_df["총접속수"].tolist()}
        draw_chart(frame_chart, x_values, y_map, "페이지별 총 접속 수", "페이지", "접속 수", kind="bar")

    def _build_period_tab(self, tab_title: str, table_df: pd.DataFrame, pivot_df: pd.DataFrame,
                          left_title: str, right_title: str, period_col: str,
                          x_label: str, chart_kind: str):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tab_title)

        paned = ttk.Panedwindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Labelframe(paned, text=left_title, padding=6)
        right = ttk.Labelframe(paned, text=right_title, padding=6)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        create_treeview(left, table_df)

        if pivot_df.empty:
            ttk.Label(right, text="표시할 데이터가 없습니다.").pack(fill="both", expand=True)
            return

        upper = ttk.Frame(right)
        upper.pack(fill="x", pady=(0, 6))
        ttk.Label(upper, text="페이지 선택:").pack(side="left")

        page_names = list(pivot_df.columns)
        selected_page = tk.StringVar(value="전체")
        options = ["전체"] + page_names
        combo = ttk.Combobox(upper, textvariable=selected_page, values=options, state="readonly", width=30)
        combo.pack(side="left", padx=(6, 0))

        chart_container = ttk.Frame(right)
        chart_container.pack(fill="both", expand=True)

        def render_chart(*_):
            for child in chart_container.winfo_children():
                child.destroy()

            selected = selected_page.get()
            if selected == "전체":
                x_values, y_map = dataframe_to_series_map(pivot_df)
                title = f"{tab_title} - 전체 페이지"
            else:
                x_values = list(pivot_df.index)
                y_map = {selected: pivot_df[selected].tolist()}
                title = f"{tab_title} - {selected}"

            draw_chart(chart_container, x_values, y_map, title, x_label, "접속 수", kind=chart_kind)

        combo.bind("<<ComboboxSelected>>", render_chart)
        render_chart()

    def _build_daily_tab(self):
        daily_table = self.daily_recent[["date_str", "page_name", "접속수", "고유IP수"]].copy() if not self.daily_recent.empty else pd.DataFrame(columns=["date_str", "page_name", "접속수", "고유IP수"])
        self._build_period_tab(
            tab_title=f"일간 ({LOOKBACK_DAYS}일)",
            table_df=daily_table,
            pivot_df=self.daily_recent_pivot,
            left_title="일간 접속 데이터",
            right_title="일간 접속 그래프",
            period_col="date_str",
            x_label="일자",
            chart_kind="line",
        )

    def _build_weekly_tab(self):
        weekly_table = self.weekly_recent[["year_week", "page_name", "접속수", "고유IP수"]].copy() if not self.weekly_recent.empty else pd.DataFrame(columns=["year_week", "page_name", "접속수", "고유IP수"])
        self._build_period_tab(
            tab_title=f"주간 ({LOOKBACK_WEEKS}주)",
            table_df=weekly_table,
            pivot_df=self.weekly_recent_pivot,
            left_title="주간 접속 데이터",
            right_title="주간 접속 그래프",
            period_col="year_week",
            x_label="주차",
            chart_kind="bar",
        )

    def _build_monthly_tab(self):
        monthly_table = self.monthly_recent[["month", "page_name", "접속수", "고유IP수"]].copy() if not self.monthly_recent.empty else pd.DataFrame(columns=["month", "page_name", "접속수", "고유IP수"])
        self._build_period_tab(
            tab_title=f"월간 ({LOOKBACK_MONTHS}개월)",
            table_df=monthly_table,
            pivot_df=self.monthly_recent_pivot,
            left_title="월간 접속 데이터",
            right_title="월간 접속 그래프",
            period_col="month",
            x_label="월",
            chart_kind="bar",
        )


def main():
    app = AccessStatsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
