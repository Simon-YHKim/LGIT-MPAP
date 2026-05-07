from __future__ import annotations

import pandas as pd


def _table_name_by_source(source_system: str) -> str:
    return "public.itas_uph_result" if source_system == "ITAS" else "public.uph_input_runtime_daily_model"


def _rank_direction_ko(rank_direction: str | None) -> str:
    if rank_direction == "best":
        return "베스트"
    if rank_direction == "worst":
        return "워스트"
    return "순위"


def resolve_selected_date(selected_date_value, latest_date: pd.Timestamp | None) -> pd.Timestamp:
    if latest_date is None:
        raise ValueError("latest_date가 없어 상대 날짜를 해석할 수 없습니다.")

    if selected_date_value is None:
        return latest_date.normalize()

    text = str(selected_date_value).strip().lower()

    if text in ["today", "오늘"]:
        return latest_date.normalize()

    if text in ["yesterday", "어제"]:
        return (latest_date - pd.Timedelta(days=1)).normalize()

    return pd.to_datetime(selected_date_value).normalize()


def _build_mes_model_filter_sql(customer_model: str | None) -> str:
    if customer_model:
        return f"  AND customer_model = '{customer_model}'\n"
    return ""


def build_sql_preview(intent: dict, latest_date: pd.Timestamp | None) -> str:
    intent_name = intent.get("intent_name")
    source_system = intent.get("source_system", "MES")
    process_name = intent.get("process_name")
    customer_model = intent.get("customer_model")
    machine_no = intent.get("machine_no")
    rank_direction = intent.get("rank_direction")
    top_n = max(1, int(intent.get("top_n") or 3))

    table_name = _table_name_by_source(source_system)

    if latest_date is None:
        return "-- latest_date is None"

    model_filter_sql = _build_mes_model_filter_sql(customer_model) if source_system == "MES" else ""

    if intent_name == "get_uph_recent_days":
        recent_days = int(intent.get("recent_days") or 3)
        end_date = latest_date.normalize()
        start_date = end_date - pd.Timedelta(days=recent_days - 1)

        return f"""
SELECT
    work_date AS 날짜,
    AVG(uph) AS uph,
    CASE WHEN MAX(uph) > 0 THEN 1 - (AVG(uph) / MAX(uph)) END AS uph_deviation_rate,
    (MAX(uph) - MIN(uph)) AS bestworst_gap
FROM {table_name}
WHERE process_name = '{process_name}'
{model_filter_sql}  AND work_date BETWEEN '{start_date.date()}' AND '{end_date.date()}'
GROUP BY work_date
ORDER BY work_date;
""".strip()

    if intent_name == "get_uph_day_by_machine":
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)

        if source_system == "ITAS":
            return f"""
SELECT
    work_date AS 날짜,
    process_name AS 공정명,
    machine_no AS 호기,
    uph AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
  AND work_date = '{selected_date.date()}'
ORDER BY machine_no;
""".strip()

        return f"""
SELECT
    work_date AS 날짜,
    process_name AS 공정명,
    customer_model AS 모델,
    equipment_name AS 호기,
    SUM(uph) AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
{model_filter_sql}  AND work_date = '{selected_date.date()}'
GROUP BY work_date, process_name, customer_model, equipment_name
ORDER BY equipment_name;
""".strip()

    if intent_name == "get_uph_machine_trend":
        recent_days = int(intent.get("recent_days") or 7)
        end_date = latest_date.normalize()
        start_date = end_date - pd.Timedelta(days=recent_days - 1)

        if source_system == "ITAS":
            return f"""
SELECT
    work_date AS 날짜,
    machine_no AS 호기,
    uph AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
  AND machine_no = '{machine_no}'
  AND work_date BETWEEN '{start_date.date()}' AND '{end_date.date()}'
ORDER BY work_date;
""".strip()

        return f"""
SELECT
    work_date AS 날짜,
    equipment_name AS 호기,
    SUM(uph) AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
{model_filter_sql}  AND equipment_name = '{machine_no}'
  AND work_date BETWEEN '{start_date.date()}' AND '{end_date.date()}'
GROUP BY work_date, equipment_name
ORDER BY work_date;
""".strip()

    if intent_name == "get_ranked_machines":
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)

        if rank_direction not in ["best", "worst"]:
            return "-- rank_direction is invalid"

        order_sql = "DESC" if rank_direction == "best" else "ASC"

        if source_system == "ITAS":
            return f"""
SELECT
    machine_no AS 호기,
    uph AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
  AND work_date = '{selected_date.date()}'
  AND uph IS NOT NULL
ORDER BY uph {order_sql} NULLS LAST, machine_no
LIMIT {top_n};
""".strip()

        return f"""
SELECT
    equipment_name AS 호기,
    SUM(uph) AS uph
FROM {table_name}
WHERE process_name = '{process_name}'
{model_filter_sql}  AND work_date = '{selected_date.date()}'
  AND uph IS NOT NULL
GROUP BY equipment_name
ORDER BY uph {order_sql} NULLS LAST, equipment_name
LIMIT {top_n};
""".strip()

    if intent_name in ["get_best_worst_machine", "get_best_worst_ranked_machines"]:
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)
        top_n = max(1, int(intent.get("top_n") or 1 if intent_name == "get_best_worst_machine" else 3))

        if source_system == "ITAS":
            return f"""
WITH ranked_best AS (
    SELECT
        machine_no AS 호기,
        uph AS uph,
        ROW_NUMBER() OVER (ORDER BY uph DESC NULLS LAST, machine_no) AS rn
    FROM {table_name}
    WHERE process_name = '{process_name}'
      AND work_date = '{selected_date.date()}'
      AND uph IS NOT NULL
),
ranked_worst AS (
    SELECT
        machine_no AS 호기,
        uph AS uph,
        ROW_NUMBER() OVER (ORDER BY uph ASC NULLS LAST, machine_no) AS rn
    FROM {table_name}
    WHERE process_name = '{process_name}'
      AND work_date = '{selected_date.date()}'
      AND uph IS NOT NULL
)
SELECT 'Best' AS 구분, rn AS 순위, 호기, uph
FROM ranked_best
WHERE rn <= {top_n}
UNION ALL
SELECT 'Worst' AS 구분, rn AS 순위, 호기, uph
FROM ranked_worst
WHERE rn <= {top_n}
ORDER BY 구분, 순위;
""".strip()

        return f"""
WITH machine_uph AS (
    SELECT
        equipment_name AS 호기,
        SUM(uph) AS uph
    FROM {table_name}
    WHERE process_name = '{process_name}'
{model_filter_sql}      AND work_date = '{selected_date.date()}'
      AND uph IS NOT NULL
    GROUP BY equipment_name
),
ranked_best AS (
    SELECT
        호기,
        uph,
        ROW_NUMBER() OVER (ORDER BY uph DESC NULLS LAST, 호기) AS rn
    FROM machine_uph
),
ranked_worst AS (
    SELECT
        호기,
        uph,
        ROW_NUMBER() OVER (ORDER BY uph ASC NULLS LAST, 호기) AS rn
    FROM machine_uph
)
SELECT 'Best' AS 구분, rn AS 순위, 호기, uph
FROM ranked_best
WHERE rn <= {top_n}
UNION ALL
SELECT 'Worst' AS 구분, rn AS 순위, 호기, uph
FROM ranked_worst
WHERE rn <= {top_n}
ORDER BY 구분, 순위;
""".strip()

    return "-- unsupported"


def build_execution_plan(intent: dict, latest_date: pd.Timestamp | None) -> dict:
    intent_name = intent.get("intent_name")
    source_system = intent.get("source_system", "MES")
    process_name = intent.get("process_name")
    customer_model = intent.get("customer_model")

    if not intent_name or intent_name == "unsupported":
        return {
            "status": "unsupported",
            "message": "현재는 UPH 관련 일부 질문만 지원합니다."
        }

    if intent.get("need_clarification"):
        return {
            "status": "need_clarification",
            "message": "질문 해석에 필요한 정보가 부족합니다.",
            "missing_slots": intent.get("missing_slots") or [],
            "intent": intent,
        }

    if not process_name:
        return {
            "status": "need_clarification",
            "message": "공정명이 필요합니다.",
            "missing_slots": ["process_name"],
            "intent": intent,
        }

    if latest_date is None:
        return {
            "status": "error",
            "message": "최신 기준일을 확인할 수 없습니다."
        }

    if intent_name == "get_uph_recent_days":
        recent_days = int(intent.get("recent_days") or 3)
        end_date = latest_date.normalize()
        start_date = end_date - pd.Timedelta(days=recent_days - 1)

        tool_name = "get_itas_uph_recent_days" if source_system == "ITAS" else "get_mes_uph_recent_days"

        return {
            "status": "ready_for_approval",
            "message": f"{source_system} 기준 최근 N일 공정 평균 UPH 조회 계획이 준비되었습니다.",
            "intent": intent,
            "execution_plan": {
                "tool_name": tool_name,
                "arguments": {
                    "source_system": source_system,
                    "process_name": process_name,
                    "customer_model": customer_model,
                    "start_date": str(start_date.date()),
                    "end_date": str(end_date.date()),
                    "recent_days": recent_days,
                },
            },
            "sql_preview": build_sql_preview(intent, latest_date),
        }

    if intent_name == "get_uph_day_by_machine":
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)
        fixed_intent = {**intent, "selected_date": str(selected_date.date())}

        tool_name = "get_itas_uph_day_by_machine" if source_system == "ITAS" else "get_mes_uph_day_by_machine"

        return {
            "status": "ready_for_approval",
            "message": f"{source_system} 기준 특정 날짜 호기별 UPH 조회 계획이 준비되었습니다.",
            "intent": fixed_intent,
            "execution_plan": {
                "tool_name": tool_name,
                "arguments": {
                    "source_system": source_system,
                    "process_name": process_name,
                    "customer_model": customer_model,
                    "selected_date": str(selected_date.date()),
                },
            },
            "sql_preview": build_sql_preview(fixed_intent, latest_date),
        }

    if intent_name == "get_uph_machine_trend":
        machine_no = intent.get("machine_no")
        if not machine_no:
            return {
                "status": "need_clarification",
                "message": "호기 번호가 필요합니다.",
                "missing_slots": ["machine_no"],
                "intent": intent,
            }

        recent_days = int(intent.get("recent_days") or 7)
        end_date = latest_date.normalize()
        start_date = end_date - pd.Timedelta(days=recent_days - 1)

        tool_name = "get_itas_uph_machine_trend" if source_system == "ITAS" else "get_mes_uph_machine_trend"

        return {
            "status": "ready_for_approval",
            "message": f"{source_system} 기준 호기별 UPH 추이 조회 계획이 준비되었습니다.",
            "intent": intent,
            "execution_plan": {
                "tool_name": tool_name,
                "arguments": {
                    "source_system": source_system,
                    "process_name": process_name,
                    "customer_model": customer_model,
                    "machine_no": machine_no,
                    "start_date": str(start_date.date()),
                    "end_date": str(end_date.date()),
                    "recent_days": recent_days,
                },
            },
            "sql_preview": build_sql_preview(intent, latest_date),
        }

    if intent_name == "get_ranked_machines":
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)
        rank_direction = intent.get("rank_direction")
        top_n = max(1, int(intent.get("top_n") or 3))

        if rank_direction not in ["best", "worst"]:
            return {
                "status": "need_clarification",
                "message": "베스트인지 워스트인지 구분이 필요합니다.",
                "missing_slots": ["rank_direction"],
                "intent": intent,
            }

        tool_name = "get_itas_ranked_machines" if source_system == "ITAS" else "get_mes_ranked_machines"
        fixed_intent = {
            **intent,
            "selected_date": str(selected_date.date()),
            "rank_direction": rank_direction,
            "ranking_mode": rank_direction,
            "top_n": top_n,
        }

        return {
            "status": "ready_for_approval",
            "message": f"{source_system} 기준 {_rank_direction_ko(rank_direction)} 호기 {top_n}개 조회 계획이 준비되었습니다.",
            "intent": fixed_intent,
            "execution_plan": {
                "tool_name": tool_name,
                "arguments": {
                    "source_system": source_system,
                    "process_name": process_name,
                    "customer_model": customer_model,
                    "selected_date": str(selected_date.date()),
                    "rank_direction": rank_direction,
                    "ranking_mode": rank_direction,
                    "top_n": top_n,
                },
            },
            "sql_preview": build_sql_preview(fixed_intent, latest_date),
        }

    # --------------------------------------------------
    # best/worst 1개도 내부적으로는 both + top_n=1 로 통합
    # --------------------------------------------------
    if intent_name in ["get_best_worst_machine", "get_best_worst_ranked_machines"]:
        selected_date = resolve_selected_date(intent.get("selected_date"), latest_date)
        top_n = max(1, int(intent.get("top_n") or 1 if intent_name == "get_best_worst_machine" else 3))

        tool_name = "get_itas_best_worst_ranked_machines" if source_system == "ITAS" else "get_mes_best_worst_ranked_machines"

        fixed_intent = {
            **intent,
            "selected_date": str(selected_date.date()),
            "ranking_mode": "both",
            "top_n": top_n,
        }

        message = (
            f"{source_system} 기준 Best/Worst 호기 조회 계획이 준비되었습니다."
            if top_n == 1
            else f"{source_system} 기준 베스트/워스트 각각 {top_n}개 호기 조회 계획이 준비되었습니다."
        )

        sql_preview_intent = {
            **fixed_intent,
            "intent_name": "get_best_worst_ranked_machines",
        }

        return {
            "status": "ready_for_approval",
            "message": message,
            "intent": fixed_intent,
            "execution_plan": {
                "tool_name": tool_name,
                "arguments": {
                    "source_system": source_system,
                    "process_name": process_name,
                    "customer_model": customer_model,
                    "selected_date": str(selected_date.date()),
                    "ranking_mode": "both",
                    "top_n": top_n,
                },
            },
            "sql_preview": build_sql_preview(sql_preview_intent, latest_date),
        }

    return {
        "status": "unsupported",
        "message": "현재 지원하지 않는 질문 유형입니다."
    }