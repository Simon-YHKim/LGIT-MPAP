# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path
from datetime import timedelta
from collections import OrderedDict

import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text
from dateutil.relativedelta import relativedelta


# =========================================================
# 0. 공통 유틸
# =========================================================

def acronymize_process_name(process_name: str) -> str:
    """
    공정명을 짧은 축약형으로 변환
    """
    if process_name is None:
        return ""

    try:
        if pd.isna(process_name):
            return ""
    except Exception:
        pass

    s = str(process_name).strip()
    if not s or s.lower() in {"nan", "none", "<na>"}:
        return ""

    # 이미 충분히 짧으면 그대로 사용
    if len(s) <= 8 and re.fullmatch(r"[A-Za-z0-9/+\-_]+", s):
        return s.upper()

    upper_tokens = re.findall(r"[A-Z]{2,}", s)
    if upper_tokens:
        joined = "".join(upper_tokens)
        if 2 <= len(joined) <= 8:
            return joined

    tokens = re.split(r"[\s\-/_,.()]+", s)
    tokens = [t for t in tokens if t]

    alpha_num_tokens = [t for t in tokens if re.search(r"[A-Za-z0-9]", t)]
    if alpha_num_tokens:
        acronym = "".join(t[0] for t in alpha_num_tokens if t).upper()
        if acronym:
            return acronym[:8]

    return s


def _safe_short_label(process_name, process_short_name) -> str:
    """
    축약공정명이 비어 있거나 nan/none인 경우 안전하게 보정
    """
    short_val = ""
    try:
        if process_short_name is not None and not pd.isna(process_short_name):
            short_val = str(process_short_name).strip()
    except Exception:
        short_val = str(process_short_name).strip() if process_short_name is not None else ""

    if short_val and short_val.lower() not in {"nan", "none", "<na>"}:
        return short_val

    # fallback: 원본 공정명 축약
    base = ""
    try:
        if process_name is not None and not pd.isna(process_name):
            base = str(process_name).strip()
    except Exception:
        base = str(process_name).strip() if process_name is not None else ""

    if not base or base.lower() in {"nan", "none", "<na>"}:
        return "-"

    acr = acronymize_process_name(base)
    return acr if acr else base


def _safe_read_sql(sql, engine, params=None) -> pd.DataFrame:
    return pd.read_sql(sql, engine, params=params or {})


def _period_order():
    return ["선택 기간", "1주전", "2주전", "지난달 전체", "2달전 전체", "지난해 전체"]


def _build_compare_periods(start_date, end_date):
    """
    비교용 6개 구간 생성
    """
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    this_monday = start_date - timedelta(days=start_date.weekday())

    prev1_start = this_monday - timedelta(days=7)
    prev1_end = prev1_start + timedelta(days=6)

    prev2_start = this_monday - timedelta(days=14)
    prev2_end = prev2_start + timedelta(days=6)

    last_month_ref = start_date.replace(day=1) - relativedelta(months=1)
    last_month_start = last_month_ref.replace(day=1)
    last_month_end = (last_month_start + relativedelta(months=1)) - timedelta(days=1)

    two_month_ref = start_date.replace(day=1) - relativedelta(months=2)
    two_month_start = two_month_ref.replace(day=1)
    two_month_end = (two_month_start + relativedelta(months=1)) - timedelta(days=1)

    last_year_start = start_date.replace(year=start_date.year - 1, month=1, day=1)
    last_year_end = start_date.replace(year=start_date.year - 1, month=12, day=31)

    return OrderedDict([
        ("선택 기간", (start_date, end_date)),
        ("1주전", (prev1_start, prev1_end)),
        ("2주전", (prev2_start, prev2_end)),
        ("지난달 전체", (last_month_start, last_month_end)),
        ("2달전 전체", (two_month_start, two_month_end)),
        ("지난해 전체", (last_year_start, last_year_end)),
    ])


def _sanitize_id_list(values):
    cleaned = []
    for v in values or []:
        try:
            cleaned.append(int(v))
        except Exception:
            continue
    return sorted(set(cleaned))


def _build_process_filter_sql(process_ids, alias="md"):
    ids = _sanitize_id_list(process_ids)
    if not ids:
        return ""
    id_str = ",".join(str(x) for x in ids)
    return f" AND {alias}.process_id IN ({id_str}) "


# =========================================================
# 1. 팀별 공정 필터 저장 테이블
# =========================================================

def ensure_team_process_filter_table(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mtba.team_process_filter (
                team_name   TEXT NOT NULL,
                process_id  BIGINT NOT NULL REFERENCES mtba.dim_process(process_id) ON DELETE CASCADE,
                created_at  TIMESTAMP DEFAULT NOW(),
                updated_at  TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (team_name, process_id)
            )
        """))


def get_all_processes(engine) -> pd.DataFrame:
    sql = text("""
        SELECT
            process_id,
            process_name,
            COALESCE(process_short, process_name) AS process_short_name
        FROM mtba.dim_process
        ORDER BY process_name
    """)
    df = _safe_read_sql(sql, engine)

    if df.empty:
        return df

    df["process_short_name"] = df.apply(
        lambda r: _safe_short_label(r["process_name"], r["process_short_name"]),
        axis=1
    )
    return df


def get_team_process_ids(engine, team_name: str):
    if team_name == "전체":
        return []

    ensure_team_process_filter_table(engine)

    sql = text("""
        SELECT process_id
        FROM mtba.team_process_filter
        WHERE team_name = :team_name
        ORDER BY process_id
    """)
    df = _safe_read_sql(sql, engine, params={"team_name": team_name})

    if df.empty:
        return []

    return [int(x) for x in df["process_id"].dropna().tolist()]


def save_team_process_ids(engine, team_name: str, process_ids):
    if team_name == "전체":
        return

    ensure_team_process_filter_table(engine)
    process_ids = _sanitize_id_list(process_ids)

    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM mtba.team_process_filter WHERE team_name = :team_name"),
            {"team_name": team_name}
        )

        for pid in process_ids:
            conn.execute(text("""
                INSERT INTO mtba.team_process_filter (team_name, process_id)
                VALUES (:team_name, :process_id)
                ON CONFLICT (team_name, process_id) DO NOTHING
            """), {
                "team_name": team_name,
                "process_id": pid
            })


# =========================================================
# 2. 기본 조회
# =========================================================

ALLOWED_MODELS = ["R53A", "R53B", "R50", "R63A", "R63B", "R70"]

def get_models(engine) -> pd.DataFrame:
    sql = text("""
        SELECT
            model_id,
            model_name
        FROM mtba.dim_model
        WHERE model_name IS NOT NULL
        ORDER BY model_name
    """)
    df = pd.read_sql(sql, engine)

    if df.empty:
        return df

    df = df[df["model_name"].isin(ALLOWED_MODELS)].copy()
    return df.reset_index(drop=True)


def get_date_range(engine):
    sql = text("""
        SELECT
            MIN(base_date) AS min_date,
            MAX(base_date) AS max_date
        FROM mtba.fact_runtime_daily
    """)
    df = _safe_read_sql(sql, engine)

    if df.empty:
        return None, None

    min_date = df.loc[0, "min_date"]
    max_date = df.loc[0, "max_date"]

    if pd.isna(min_date) or pd.isna(max_date):
        return None, None

    return pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()


# =========================================================
# 3. whitelist helper
# =========================================================

def _allowed_alarm_match_sql(
    alarm_code_expr: str = "da.alarm_code",
    alarm_name_expr: str = "da.alarm_name",
) -> str:
    """
    whitelist 에 포함된 알람코드 + 알람명 세트만 허용
    """
    return f"""
        EXISTS (
            SELECT 1
            FROM mtba.alarm_whitelist aw
            WHERE aw.alarm_code = CAST({alarm_code_expr} AS TEXT)
              AND aw.alarm_name = TRIM(COALESCE({alarm_name_expr}, ''))
        )
    """


# =========================================================
# 4. 공통 SQL 조각
# =========================================================

def _equipment_model_daily_cte() -> str:
    """
    설비-일자 기준 대표 모델 선정 + MTBA 일별 계산용 공통 CTE
    """
    allowed_alarm_sql = _allowed_alarm_match_sql("da.alarm_code", "da.alarm_name")

    return f"""
        WITH prod_rank AS (
            SELECT
                fp.base_date,
                fp.equipment_id,
                fp.model_id,
                SUM(COALESCE(fp.output_qty, 0)) AS sum_output_qty,
                SUM(COALESCE(fp.input_qty, 0)) AS sum_input_qty,
                ROW_NUMBER() OVER (
                    PARTITION BY fp.base_date, fp.equipment_id
                    ORDER BY
                        SUM(COALESCE(fp.output_qty, 0)) DESC,
                        SUM(COALESCE(fp.input_qty, 0)) DESC,
                        fp.model_id
                ) AS rn
            FROM mtba.fact_production_daily fp
            GROUP BY
                fp.base_date,
                fp.equipment_id,
                fp.model_id
        ),
        prod_map AS (
            SELECT
                base_date,
                equipment_id,
                model_id
            FROM prod_rank
            WHERE rn = 1
        ),
        alarm_filtered_daily AS (
            SELECT
                fad.base_date,
                fad.equipment_id,
                SUM(COALESCE(fad.alarm_count, 0)) AS alarm_count_total
            FROM mtba.fact_alarm_detail_daily fad
            JOIN mtba.dim_alarm da
              ON fad.alarm_id = da.alarm_id
            WHERE {allowed_alarm_sql}
            GROUP BY
                fad.base_date,
                fad.equipment_id
        ),
        mtba_daily AS (
            SELECT
                rt.base_date,
                rt.plant_id,
                rt.process_id,
                rt.equipment_id,
                pm.model_id,
                rt.runtime_minutes,
                COALESCE(afd.alarm_count_total, 0) AS alarm_count_total,
                CASE
                    WHEN COALESCE(afd.alarm_count_total, 0) > 0
                    THEN rt.runtime_minutes::numeric / afd.alarm_count_total::numeric
                    ELSE rt.runtime_minutes::numeric
                END AS mtba
            FROM mtba.fact_runtime_daily rt
            LEFT JOIN alarm_filtered_daily afd
              ON rt.base_date = afd.base_date
             AND rt.equipment_id = afd.equipment_id
            LEFT JOIN prod_map pm
              ON rt.base_date = pm.base_date
             AND rt.equipment_id = pm.equipment_id
        )
    """


# =========================================================
# 5. 그래프용 공정별 MTBA 기간 비교
# =========================================================

def get_period_compare_by_process(
    engine,
    model_id,
    start_date,
    end_date,
    include_total_avg=True,
    process_ids=None
) -> pd.DataFrame:
    """
    선택 모델의 공정별 기간 비교
    - '전체 평균'은 항상 마지막에 오도록 category 순서를 분리 관리
    """
    periods = _build_compare_periods(start_date, end_date)
    result_frames = []
    process_filter_sql = _build_process_filter_sql(process_ids, alias="md")

    sql = text(f"""
        {_equipment_model_daily_cte()}
        ,
        equip_level AS (
            SELECT
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name) AS process_short_name,
                md.equipment_id,
                SUM(COALESCE(md.runtime_minutes, 0)) AS sum_runtime_minutes,
                SUM(COALESCE(md.alarm_count_total, 0)) AS sum_alarm_count,
                CASE
                    WHEN SUM(COALESCE(md.alarm_count_total, 0)) > 0
                    THEN SUM(COALESCE(md.runtime_minutes, 0))::numeric
                         / SUM(COALESCE(md.alarm_count_total, 0))::numeric
                    ELSE NULL
                END AS equipment_mtba
            FROM mtba_daily md
            JOIN mtba.dim_equipment de
              ON md.equipment_id = de.equipment_id
            JOIN mtba.dim_process dp
              ON de.process_id = dp.process_id
            WHERE md.model_id = :model_id
              AND md.base_date BETWEEN :start_date AND :end_date
              {process_filter_sql}
            GROUP BY
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name),
                md.equipment_id
        )
        SELECT
            process_name,
            process_short_name,
            AVG(equipment_mtba) AS mtba
        FROM equip_level
        WHERE equipment_mtba IS NOT NULL
          AND equipment_mtba > 0
        GROUP BY
            process_name,
            process_short_name
        ORDER BY
            process_name
    """)

    for period_name, (s_date, e_date) in periods.items():
        df = _safe_read_sql(
            sql,
            engine,
            params={
                "model_id": model_id,
                "start_date": s_date,
                "end_date": e_date,
            }
        )

        if df.empty:
            continue

        df["process_short_name"] = df.apply(
            lambda r: _safe_short_label(r["process_name"], r["process_short_name"]),
            axis=1
        )
        df["period_name"] = period_name

        result_frames.append(df[["period_name", "process_name", "process_short_name", "mtba"]])

    if not result_frames:
        return pd.DataFrame(columns=["period_name", "process_name", "process_short_name", "mtba"])

    result = pd.concat(result_frames, ignore_index=True)

    # 전체 평균 추가
    if include_total_avg:
        total_avg_df = (
            result.groupby("period_name", dropna=False)["mtba"]
            .mean()
            .reset_index()
        )
        total_avg_df["process_name"] = "전체 평균"
        total_avg_df["process_short_name"] = "전체 평균"

        result = pd.concat(
            [result, total_avg_df[["period_name", "process_name", "process_short_name", "mtba"]]],
            ignore_index=True
        )

    result["process_short_name"] = result.apply(
        lambda r: _safe_short_label(r["process_name"], r["process_short_name"]),
        axis=1
    )

    # 기간 category
    result["period_name"] = pd.Categorical(
        result["period_name"],
        categories=_period_order(),
        ordered=True
    )

    # 공정 category: 일반 공정 + 전체 평균 마지막
    normal_df = result[result["process_name"] != "전체 평균"].copy()

    selected_df = normal_df[normal_df["period_name"] == "선택 기간"].copy()
    if not selected_df.empty:
        normal_order = (
            selected_df.sort_values("mtba", ascending=True)["process_short_name"]
            .drop_duplicates()
            .tolist()
        )
    else:
        normal_order = (
            normal_df["process_short_name"]
            .drop_duplicates()
            .tolist()
        )

    if include_total_avg:
        process_order = normal_order + ["전체 평균"]
    else:
        process_order = normal_order

    result["process_short_name"] = pd.Categorical(
        result["process_short_name"],
        categories=process_order,
        ordered=True
    )

    result = result.sort_values(["process_short_name", "period_name"]).reset_index(drop=True)
    return result

def make_mtba_process_bar_chart(
    compare_df: pd.DataFrame,
    model_name=None,
    warn_line=60,
    target_line=120,
    selected_process_names=None,
):
    """
    공정별 MTBA 비교 그래프
    - '전체 평균'은 항상 x축 맨 마지막
    - 선택 공정은 ✅ 표시
    - hover는 실제 공정명 + 실제 MTBA 표시
    """
    fig = go.Figure()

    if compare_df.empty:
        fig.update_layout(
            title="모델별 MTBA 기간 비교",
            xaxis_title="공정",
            yaxis_title="MTBA",
            height=500
        )
        return fig

    work = compare_df.copy()
    selected_set = set(selected_process_names or [])

    # 안전한 표시 라벨
    work["display_label"] = work.apply(
        lambda r: _safe_short_label(r["process_name"], r["process_short_name"]),
        axis=1
    )

    # -----------------------------
    # x축 공정 순서 결정
    # 일반 공정만 먼저 정렬하고 '전체 평균'은 무조건 마지막
    # -----------------------------
    normal_df = work[work["process_name"] != "전체 평균"].copy()
    total_avg_exists = (work["process_name"] == "전체 평균").any()

    selected_period_df = normal_df[normal_df["period_name"] == "선택 기간"].copy()

    if not selected_period_df.empty:
        normal_order = (
            selected_period_df.sort_values("mtba", ascending=True)["display_label"]
            .drop_duplicates()
            .tolist()
        )
    else:
        normal_order = (
            normal_df["display_label"]
            .drop_duplicates()
            .tolist()
        )

    # 혹시 선택기간에 없는 공정이 다른 기간에만 있으면 뒤에 이어붙임
    all_normal_labels = normal_df["display_label"].dropna().astype(str).drop_duplicates().tolist()
    normal_order = normal_order + [x for x in all_normal_labels if x not in normal_order]

    if total_avg_exists:
        process_order = normal_order + ["전체 평균"]
    else:
        process_order = normal_order

    # 선택 공정 라벨 강조
    label_map_df = work[["process_name", "display_label"]].drop_duplicates().copy()
    label_map_df["x_label"] = label_map_df.apply(
        lambda r: f"✅ {r['display_label']}" if r["process_name"] in selected_set else r["display_label"],
        axis=1
    )

    x_order = []
    seen = set()
    for lbl in process_order:
        row = label_map_df[label_map_df["display_label"] == lbl]
        if row.empty:
            xlbl = lbl
        else:
            xlbl = row.iloc[0]["x_label"]

        if xlbl not in seen:
            x_order.append(xlbl)
            seen.add(xlbl)

    period_order = ["지난해 전체", "2달전 전체", "지난달 전체", "2주전", "1주전", "선택 기간"]

    color_map = {
        "선택 기간": "#2F6DB3",
        "1주전": "#5A8FD8",
        "2주전": "#8EB4EA",
        "지난달 전체": "#D9DEE7",
        "2달전 전체": "#BFC7D5",
        "지난해 전체": "#8A94A6",
    }

    legend_name_map = {
        "선택 기간": "선택 기간",
        "1주전": "1주전",
        "2주전": "2주전",
        "지난달 전체": "지난달",
        "2달전 전체": "2달전 전체",
        "지난해 전체": "지난해 전체",
    }

    for period_name in period_order:
        part = work[work["period_name"] == period_name].copy()
        if part.empty:
            continue

        part = part.merge(
            label_map_df[["process_name", "x_label"]],
            on="process_name",
            how="left"
        )

        # x축 순서대로 정렬
        x_order_df = pd.DataFrame({"x_label": x_order})
        part = x_order_df.merge(part, on="x_label", how="left")

        part["actual_mtba"] = pd.to_numeric(part["mtba"], errors="coerce")
        part["display_mtba"] = part["actual_mtba"].clip(upper=120)
        part["label"] = part["actual_mtba"].apply(
            lambda x: None if pd.isna(x) else f"{x:.0f}"
        )

        line_colors = []
        line_widths = []

        for _, row in part.iterrows():
            process_name = row.get("process_name")
            if process_name in selected_set:
                line_colors.append("#FF6B00")
                line_widths.append(2.5)
            else:
                line_colors.append("rgba(0,0,0,0)")
                line_widths.append(0)

        fig.add_bar(
            name=legend_name_map.get(period_name, period_name),
            x=part["x_label"],
            y=part["display_mtba"],
            text=part["label"],
            textposition="outside",
            marker=dict(
                color=color_map.get(period_name, "#999999"),
                line=dict(color=line_colors, width=line_widths)
            ),
            cliponaxis=False,
            customdata=part[["process_name", "actual_mtba"]],
            hovertemplate=(
                "공정: %{customdata[0]}<br>"
                "실제 MTBA: %{customdata[1]:.1f}<extra></extra>"
            )
        )

    if warn_line is not None:
        fig.add_hline(y=warn_line, line_dash="dot", line_color="#F1C232", line_width=1)

    if target_line is not None:
        fig.add_hline(y=target_line, line_dash="dot", line_color="#3C78D8", line_width=1)

    title = "모델별 MTBA 기간 비교"
    if model_name:
        title = f"{model_name} 공정별 MTBA 기간 비교"

    fig.update_layout(
        title=title,
        barmode="group",
        clickmode="event+select",
        xaxis_title="공정",
        yaxis_title="MTBA",
        height=540,
        legend_title="기간",
        margin=dict(l=20, r=20, t=60, b=60),
        yaxis=dict(range=[0, 120]),
        xaxis=dict(
            categoryorder="array",
            categoryarray=x_order,
            tickfont=dict(size=13)
        ),
    )

    return fig

# =========================================================
# 6. 선택 기간 공정별 요약
# =========================================================

def get_process_summary(engine, model_id, start_date, end_date, use_short_name=False, process_ids=None) -> pd.DataFrame:
    process_filter_sql = _build_process_filter_sql(process_ids, alias="md")

    sql = text(f"""
        {_equipment_model_daily_cte()}
        ,
        equip_level AS (
            SELECT
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name) AS process_short_name,
                md.equipment_id,
                SUM(COALESCE(md.runtime_minutes, 0)) AS sum_runtime_minutes,
                SUM(COALESCE(md.alarm_count_total, 0)) AS sum_alarm_count,
                CASE
                    WHEN SUM(COALESCE(md.alarm_count_total, 0)) > 0
                    THEN SUM(COALESCE(md.runtime_minutes, 0))::numeric
                         / SUM(COALESCE(md.alarm_count_total, 0))::numeric
                    ELSE NULL
                END AS equipment_mtba
            FROM mtba_daily md
            JOIN mtba.dim_equipment de
              ON md.equipment_id = de.equipment_id
            JOIN mtba.dim_process dp
              ON de.process_id = dp.process_id
            WHERE md.model_id = :model_id
              AND md.base_date BETWEEN :start_date AND :end_date
              {process_filter_sql}
            GROUP BY
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name),
                md.equipment_id
        )
        SELECT
            process_name AS raw_process_name,
            process_short_name,
            MAX(equipment_mtba) AS best_mtba,
            MIN(equipment_mtba) AS worst_mtba,
            AVG(equipment_mtba) AS avg_mtba,
            COALESCE(STDDEV_POP(equipment_mtba), 0) AS stdev_mtba
        FROM equip_level
        WHERE equipment_mtba IS NOT NULL
          AND equipment_mtba > 0
        GROUP BY
            raw_process_name,
            process_short_name
        ORDER BY
            avg_mtba ASC,
            raw_process_name
    """)

    df = _safe_read_sql(
        sql,
        engine,
        params={
            "model_id": model_id,
            "start_date": start_date,
            "end_date": end_date,
        }
    )

    if df.empty:
        return df

    for col in ["best_mtba", "worst_mtba", "avg_mtba", "stdev_mtba"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    df["process_short_name"] = df.apply(
        lambda r: _safe_short_label(r["raw_process_name"], r["process_short_name"]),
        axis=1
    )

    df["display_process_name"] = df["raw_process_name"]
    if use_short_name:
        df["display_process_name"] = df["process_short_name"]

    out = df.rename(columns={
        "raw_process_name": "원본공정명",
        "display_process_name": "공정",
        "best_mtba": "Best MTBA",
        "worst_mtba": "Worst MTBA",
        "avg_mtba": "Avg MTBA",
        "stdev_mtba": "Stdev MTBA",
    })

    return out[["원본공정명", "공정", "Best MTBA", "Worst MTBA", "Avg MTBA", "Stdev MTBA"]]


# =========================================================
# 7. 섹션 2 기준 주
# =========================================================

def get_last_target_week_range(start_date, end_date):
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    candidate_start = end_date - timedelta(days=end_date.weekday())
    candidate_end = candidate_start + timedelta(days=6)

    while candidate_start >= start_date:
        if candidate_start >= start_date and candidate_end <= end_date:
            return candidate_start, candidate_end, True

        candidate_start = candidate_start - timedelta(days=7)
        candidate_end = candidate_start + timedelta(days=6)

    start_week_monday = start_date - timedelta(days=start_date.weekday())
    prev_full_week_start = start_week_monday - timedelta(days=7)
    prev_full_week_end = prev_full_week_start + timedelta(days=6)

    return prev_full_week_start, prev_full_week_end, False


# =========================================================
# 8. 특정 공정의 주간 MTBA 현황
# =========================================================

def get_process_week_status(engine, model_id, process_name, week_start, week_end, process_ids=None):
    process_filter_sql = _build_process_filter_sql(process_ids, alias="md")

    sql = text(f"""
        {_equipment_model_daily_cte()}
        ,
        equip_level AS (
            SELECT
                dp.process_id,
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name) AS process_short_name,
                de.equipment_id,
                de.equipment_name,
                SUM(COALESCE(md.runtime_minutes, 0)) AS runtime_minutes,
                SUM(COALESCE(md.alarm_count_total, 0)) AS alarm_count_total,
                CASE
                    WHEN SUM(COALESCE(md.alarm_count_total, 0)) > 0
                    THEN SUM(COALESCE(md.runtime_minutes, 0))::numeric
                         / SUM(COALESCE(md.alarm_count_total, 0))::numeric
                    ELSE NULL
                END AS equipment_mtba
            FROM mtba_daily md
            JOIN mtba.dim_equipment de
              ON md.equipment_id = de.equipment_id
            JOIN mtba.dim_process dp
              ON de.process_id = dp.process_id
            WHERE md.model_id = :model_id
              AND dp.process_name = :process_name
              AND md.base_date BETWEEN :week_start AND :week_end
              {process_filter_sql}
            GROUP BY
                dp.process_id,
                dp.process_name,
                COALESCE(dp.process_short, dp.process_name),
                de.equipment_id,
                de.equipment_name
        )
        SELECT *
        FROM equip_level
        WHERE equipment_mtba IS NOT NULL
          AND equipment_mtba > 0
        ORDER BY equipment_mtba ASC, equipment_name
    """)

    df = _safe_read_sql(
        sql,
        engine,
        params={
            "model_id": model_id,
            "process_name": process_name,
            "week_start": week_start,
            "week_end": week_end,
        }
    )

    if df.empty:
        summary = {
            "process_name": process_name,
            "process_id": None,
            "total_active_equipment": 0,
            "green_count": 0,
            "yellow_count": 0,
            "red_count": 0,
            "best_equipment_id": None,
            "best_equipment_name": None,
            "best_mtba": None,
            "worst_equipment_id": None,
            "worst_equipment_name": None,
            "worst_mtba": None,
            "avg_mtba": None,
        }
        return summary, df

    df["runtime_minutes"] = pd.to_numeric(df["runtime_minutes"], errors="coerce").fillna(0)
    df["alarm_count_total"] = pd.to_numeric(df["alarm_count_total"], errors="coerce").fillna(0).astype(int)
    df["equipment_mtba"] = pd.to_numeric(df["equipment_mtba"], errors="coerce")

    total_active = int((df["equipment_mtba"] > 0).sum())
    green_count = int((df["equipment_mtba"] >= 120).sum())
    yellow_count = int(((df["equipment_mtba"] >= 60) & (df["equipment_mtba"] < 120)).sum())
    red_count = int((df["equipment_mtba"] < 60).sum())

    best_row = df.sort_values("equipment_mtba", ascending=False).iloc[0]
    worst_row = df.sort_values("equipment_mtba", ascending=True).iloc[0]

    summary = {
        "process_name": process_name,
        "process_id": int(best_row["process_id"]),
        "process_short_name": _safe_short_label(best_row["process_name"], best_row["process_short_name"]),
        "total_active_equipment": total_active,
        "green_count": green_count,
        "yellow_count": yellow_count,
        "red_count": red_count,
        "best_equipment_id": int(best_row["equipment_id"]),
        "best_equipment_name": best_row["equipment_name"],
        "best_mtba": round(float(best_row["equipment_mtba"]), 2),
        "worst_equipment_id": int(worst_row["equipment_id"]),
        "worst_equipment_name": worst_row["equipment_name"],
        "worst_mtba": round(float(worst_row["equipment_mtba"]), 2),
        "avg_mtba": round(float(df["equipment_mtba"].mean()), 2),
    }

    return summary, df


def get_process_best_worst_snapshot(summary: dict, detail_df: pd.DataFrame) -> pd.DataFrame:
    if detail_df.empty:
        return pd.DataFrame(columns=["구분", "호기", "Runtime(분)", "알람 횟수", "MTBA"])

    best_df = detail_df[detail_df["equipment_id"] == summary["best_equipment_id"]].copy()
    worst_df = detail_df[detail_df["equipment_id"] == summary["worst_equipment_id"]].copy()

    rows = []

    if not worst_df.empty:
        r = worst_df.iloc[0]
        rows.append({
            "구분": "Worst",
            "호기": r["equipment_name"],
            "Runtime(분)": round(float(r["runtime_minutes"]), 1),
            "알람 횟수": int(r["alarm_count_total"]),
            "MTBA": round(float(r["equipment_mtba"]), 2),
        })

    if not best_df.empty:
        r = best_df.iloc[0]
        rows.append({
            "구분": "Best",
            "호기": r["equipment_name"],
            "Runtime(분)": round(float(r["runtime_minutes"]), 1),
            "알람 횟수": int(r["alarm_count_total"]),
            "MTBA": round(float(r["equipment_mtba"]), 2),
        })

    return pd.DataFrame(rows)


# =========================================================
# 9. Worst 기준 Top5 알람 비교
# =========================================================

def get_best_worst_alarm_top5_by_worst(
    engine,
    model_id,
    week_start,
    week_end,
    best_equipment_id,
    worst_equipment_id,
    top_n=5
):
    allowed_alarm_sql = _allowed_alarm_match_sql("da.alarm_code", "da.alarm_name")

    def _run_query(use_model_filter: bool) -> pd.DataFrame:
        model_filter_alarm = "AND fad.model_id = :model_id" if use_model_filter else ""
        model_filter_prod = "AND model_id = :model_id" if use_model_filter else ""

        sql = text(f"""
            WITH worst_top_alarm AS (
                SELECT
                    CAST(da.alarm_code AS TEXT) AS alarm_code,
                    COALESCE(da.alarm_name, '') AS alarm_name,
                    SUM(COALESCE(fad.alarm_count, 0)) AS worst_count
                FROM mtba.fact_alarm_detail_daily fad
                JOIN mtba.dim_alarm da
                  ON fad.alarm_id = da.alarm_id
                WHERE fad.equipment_id = :worst_equipment_id
                  AND fad.base_date BETWEEN :week_start AND :week_end
                  {model_filter_alarm}
                  AND {allowed_alarm_sql}
                GROUP BY CAST(da.alarm_code AS TEXT), COALESCE(da.alarm_name, '')
                ORDER BY worst_count DESC, alarm_code
                LIMIT :top_n
            ),
            best_alarm AS (
                SELECT
                    CAST(da.alarm_code AS TEXT) AS alarm_code,
                    COALESCE(da.alarm_name, '') AS alarm_name,
                    SUM(COALESCE(fad.alarm_count, 0)) AS best_count
                FROM mtba.fact_alarm_detail_daily fad
                JOIN mtba.dim_alarm da
                  ON fad.alarm_id = da.alarm_id
                WHERE fad.equipment_id = :best_equipment_id
                  AND fad.base_date BETWEEN :week_start AND :week_end
                  {model_filter_alarm}
                  AND {allowed_alarm_sql}
                GROUP BY CAST(da.alarm_code AS TEXT), COALESCE(da.alarm_name, '')
            ),
            worst_alarm AS (
                SELECT
                    CAST(da.alarm_code AS TEXT) AS alarm_code,
                    COALESCE(da.alarm_name, '') AS alarm_name,
                    SUM(COALESCE(fad.alarm_count, 0)) AS worst_count
                FROM mtba.fact_alarm_detail_daily fad
                JOIN mtba.dim_alarm da
                  ON fad.alarm_id = da.alarm_id
                WHERE fad.equipment_id = :worst_equipment_id
                  AND fad.base_date BETWEEN :week_start AND :week_end
                  {model_filter_alarm}
                  AND {allowed_alarm_sql}
                GROUP BY CAST(da.alarm_code AS TEXT), COALESCE(da.alarm_name, '')
            ),
            best_input AS (
                SELECT COALESCE(SUM(COALESCE(input_qty, 0)), 0) AS best_input_qty
                FROM mtba.fact_production_daily
                WHERE equipment_id = :best_equipment_id
                  AND base_date BETWEEN :week_start AND :week_end
                  {model_filter_prod}
            ),
            worst_input AS (
                SELECT COALESCE(SUM(COALESCE(input_qty, 0)), 0) AS worst_input_qty
                FROM mtba.fact_production_daily
                WHERE equipment_id = :worst_equipment_id
                  AND base_date BETWEEN :week_start AND :week_end
                  {model_filter_prod}
            ),
            best_total_alarm AS (
                SELECT COALESCE(SUM(COALESCE(fad.alarm_count, 0)), 0) AS best_total_alarm_count
                FROM mtba.fact_alarm_detail_daily fad
                JOIN mtba.dim_alarm da
                  ON fad.alarm_id = da.alarm_id
                WHERE fad.equipment_id = :best_equipment_id
                  AND fad.base_date BETWEEN :week_start AND :week_end
                  {model_filter_alarm}
                  AND {allowed_alarm_sql}
            ),
            worst_total_alarm AS (
                SELECT COALESCE(SUM(COALESCE(fad.alarm_count, 0)), 0) AS worst_total_alarm_count
                FROM mtba.fact_alarm_detail_daily fad
                JOIN mtba.dim_alarm da
                  ON fad.alarm_id = da.alarm_id
                WHERE fad.equipment_id = :worst_equipment_id
                  AND fad.base_date BETWEEN :week_start AND :week_end
                  {model_filter_alarm}
                  AND {allowed_alarm_sql}
            )
            SELECT
                wta.alarm_code,
                wta.alarm_name,

                COALESCE(wa.worst_count, 0) AS worst_count,
                CASE
                    WHEN wi.worst_input_qty > 0
                    THEN ROUND(COALESCE(wa.worst_count, 0)::numeric / wi.worst_input_qty * 100, 2)
                    ELSE 0
                END AS worst_alarm_rate_pct,
                CASE
                    WHEN wta2.worst_total_alarm_count > 0
                    THEN ROUND(COALESCE(wa.worst_count, 0)::numeric / wta2.worst_total_alarm_count * 100, 2)
                    ELSE 0
                END AS worst_share_pct,

                COALESCE(ba.best_count, 0) AS best_count,
                CASE
                    WHEN bi.best_input_qty > 0
                    THEN ROUND(COALESCE(ba.best_count, 0)::numeric / bi.best_input_qty * 100, 2)
                    ELSE 0
                END AS best_alarm_rate_pct,
                CASE
                    WHEN bta.best_total_alarm_count > 0
                    THEN ROUND(COALESCE(ba.best_count, 0)::numeric / bta.best_total_alarm_count * 100, 2)
                    ELSE 0
                END AS best_share_pct

            FROM worst_top_alarm wta
            LEFT JOIN best_alarm ba
              ON wta.alarm_code = ba.alarm_code
             AND wta.alarm_name = ba.alarm_name
            LEFT JOIN worst_alarm wa
              ON wta.alarm_code = wa.alarm_code
             AND wta.alarm_name = wa.alarm_name
            CROSS JOIN best_input bi
            CROSS JOIN worst_input wi
            CROSS JOIN best_total_alarm bta
            CROSS JOIN worst_total_alarm wta2
            ORDER BY COALESCE(wa.worst_count, 0) DESC, wta.alarm_code
        """)

        params = {
            "model_id": model_id,
            "week_start": week_start,
            "week_end": week_end,
            "best_equipment_id": best_equipment_id,
            "worst_equipment_id": worst_equipment_id,
            "top_n": top_n,
        }

        return _safe_read_sql(sql, engine, params=params)

    df = _run_query(use_model_filter=True)
    model_filter_used = "Y"

    if df.empty:
        df = _run_query(use_model_filter=False)
        model_filter_used = "N"

    if df.empty:
        return pd.DataFrame(columns=[
            "alarm_code", "alarm_name",
            "worst_count", "worst_alarm_rate_pct", "worst_share_pct",
            "best_count", "best_alarm_rate_pct", "best_share_pct",
            "model_filter_used"
        ])

    for col in [
        "worst_count", "worst_alarm_rate_pct", "worst_share_pct",
        "best_count", "best_alarm_rate_pct", "best_share_pct"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["worst_count"] = df["worst_count"].astype(int)
    df["best_count"] = df["best_count"].astype(int)
    df["model_filter_used"] = model_filter_used

    return df


# =========================================================
# 10. Alarm Annotation
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ALARM_NOTE_UPLOAD_DIR = BASE_DIR / "uploads" / "alarm_annotations"
ALARM_NOTE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(text: str) -> str:
    text = str(text)
    text = re.sub(r"[^A-Za-z0-9가-힣_\-\.]+", "_", text)
    return text[:120]


def ensure_alarm_annotation_table(engine):
    sql = """
    CREATE TABLE IF NOT EXISTS mtba.alarm_annotation (
        alarm_annotation_id  BIGSERIAL PRIMARY KEY,
        alarm_code           TEXT NOT NULL,
        alarm_name           TEXT NOT NULL,
        note_text            TEXT,
        image_path           TEXT,
        image_name           TEXT,
        mime_type            TEXT,
        file_size            BIGINT,
        created_at           TIMESTAMP DEFAULT NOW(),
        updated_at           TIMESTAMP DEFAULT NOW(),
        UNIQUE (alarm_code, alarm_name)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(sql))


def get_alarm_annotation(engine, alarm_code: str, alarm_name: str):
    sql = """
    SELECT
        alarm_annotation_id,
        alarm_code,
        alarm_name,
        note_text,
        image_path,
        image_name,
        mime_type,
        file_size,
        created_at,
        updated_at
    FROM mtba.alarm_annotation
    WHERE alarm_code = :alarm_code
      AND alarm_name = :alarm_name
    LIMIT 1
    """
    df = pd.read_sql(
        text(sql),
        engine,
        params={
            "alarm_code": str(alarm_code),
            "alarm_name": str(alarm_name)
        }
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def upsert_alarm_annotation(engine, alarm_code: str, alarm_name: str, note_text: str, uploaded_file):
    existing = get_alarm_annotation(engine, alarm_code, alarm_name)

    image_path = existing["image_path"] if existing else None
    image_name = existing["image_name"] if existing else None
    mime_type = existing["mime_type"] if existing else None
    file_size = existing["file_size"] if existing else None

    if uploaded_file is not None:
        suffix = Path(uploaded_file.name).suffix
        file_name = f"{safe_filename(alarm_code)}_{safe_filename(alarm_name)}{suffix}"
        save_path = ALARM_NOTE_UPLOAD_DIR / file_name

        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        image_path = str(save_path)
        image_name = uploaded_file.name
        mime_type = uploaded_file.type
        file_size = uploaded_file.size

    sql = """
    INSERT INTO mtba.alarm_annotation
    (
        alarm_code,
        alarm_name,
        note_text,
        image_path,
        image_name,
        mime_type,
        file_size,
        created_at,
        updated_at
    )
    VALUES
    (
        :alarm_code,
        :alarm_name,
        :note_text,
        :image_path,
        :image_name,
        :mime_type,
        :file_size,
        NOW(),
        NOW()
    )
    ON CONFLICT (alarm_code, alarm_name)
    DO UPDATE SET
        note_text = EXCLUDED.note_text,
        image_path = EXCLUDED.image_path,
        image_name = EXCLUDED.image_name,
        mime_type = EXCLUDED.mime_type,
        file_size = EXCLUDED.file_size,
        updated_at = NOW()
    """
    with engine.begin() as conn:
        conn.execute(
            text(sql),
            {
                "alarm_code": str(alarm_code),
                "alarm_name": str(alarm_name),
                "note_text": note_text,
                "image_path": image_path,
                "image_name": image_name,
                "mime_type": mime_type,
                "file_size": file_size,
            }
        )