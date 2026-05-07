from __future__ import annotations

import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from auth_guard import require_login
require_login(
    page_name="MaxCapa_Chat",
    page_path="pages/5_MaxCapa_Chat.py"
)

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

FASTAPI_BASE_URL = "http://localhost:9000"


def render_header():
    st.title("MaxCapa Chat(대화형 생산지표조회)")
    st.caption("기본 조회는 MES UPH(uph_input_runtime_daily_model), 질문에 ITAS를 명시하면 ITAS UPH(itas_uph_result)로 조회합니다.")
    st.markdown("""
지원 예시:
- 최근 3일 APS Test 공정의 UPH는 얼마인가?
- 오늘 APS Test 호기별 UPH 보여줘
- 최근 7일 APS Test 3호기 UPH 추이 보여줘
- 오늘 APS Test best worst 호기는?
- 최근 7일 APS Test 공정의 R53A 모델 UPH는?
- itas uph 기준 최근 3일 APS Test의 UPH는 얼마인가?
""")


def init_session_state():
    if "llm_plan" not in st.session_state:
        st.session_state["llm_plan"] = None
    if "llm_result" not in st.session_state:
        st.session_state["llm_result"] = None
    if "llm_question" not in st.session_state:
        st.session_state["llm_question"] = ""


def render_question_input():
    st.session_state["llm_question"] = st.text_area(
        "질문 입력",
        value=st.session_state.get("llm_question", ""),
        height=100,
        placeholder="예: 최근 3일 APS Test 공정의 UPH는 얼마인가?",
    )


def request_analyze(question: str) -> dict:
    response = requests.post(
        f"{FASTAPI_BASE_URL}/chat/analyze",
        json={
            "session_id": "streamlit-session",
            "user_id": "user1",
            "question": question,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def request_continue(intent: dict, updates: dict) -> dict:
    response = requests.post(
        f"{FASTAPI_BASE_URL}/chat/continue",
        json={
            "session_id": "streamlit-session",
            "intent": intent,
            "updates": updates,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def request_execute(plan: dict) -> dict:
    response = requests.post(
        f"{FASTAPI_BASE_URL}/chat/execute",
        json={
            "session_id": "streamlit-session",
            "approved": True,
            "execution_plan": plan["execution_plan"],
            "intent": plan.get("intent"),
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def analyze_and_maybe_execute(question_override: str | None = None):
    question = question_override if question_override is not None else st.session_state.get("llm_question", "").strip()

    if not question:
        st.warning("질문을 입력하세요.")
        return

    try:
        plan = request_analyze(question)
        st.session_state["llm_plan"] = plan
        st.session_state["llm_result"] = None

        if plan.get("status") == "ready_for_approval":
            result = request_execute(plan)
            st.session_state["llm_result"] = result

    except Exception as e:
        st.error(f"질문 분석/실행 실패: {e}")


def render_clarification_ui(plan: dict):
    missing_slots = plan.get("missing_slots", [])
    candidates = plan.get("candidates", [])

    if "customer_model" in missing_slots and candidates:
        st.warning(plan.get("message", "추가 정보가 필요합니다."))

        option_map = {}
        for item in candidates:
            customer_model = item.get("customer_model", "")
            row_count = item.get("row_count", 0)
            latest_date = item.get("latest_date", "-")

            label = f"{customer_model} (rows={row_count}, latest={latest_date})"
            option_map[label] = customer_model

        selected_label = st.selectbox(
            "customer_model 선택",
            options=list(option_map.keys()),
            key="clarify_model_selectbox",
        )

        if st.button("선택한 모델로 계속 진행", key="clarify_model_retry_btn"):
            selected_model = option_map[selected_label]

            try:
                next_plan = request_continue(
                    intent=plan.get("intent", {}),
                    updates={"customer_model": selected_model},
                )
                st.session_state["llm_plan"] = next_plan
                st.session_state["llm_result"] = None

                if next_plan.get("status") == "ready_for_approval":
                    result = request_execute(next_plan)
                    st.session_state["llm_result"] = result

                st.rerun()

            except Exception as e:
                st.error(f"모델 선택 후 진행 실패: {e}")

    elif "process_name" in missing_slots and candidates:
        st.warning(plan.get("message", "추가 정보가 필요합니다."))

        option_map = {}

        for item in candidates:
            if isinstance(item, dict):
                candidate = item.get("candidate", "")
                score = item.get("score", None)
                if score is not None:
                    try:
                        label = f"{candidate} (score={float(score):.2f})"
                    except Exception:
                        label = f"{candidate} (score={score})"
                else:
                    label = candidate
                option_map[label] = candidate
            else:
                candidate = str(item)
                option_map[candidate] = candidate

        selected_label = st.selectbox(
            "공정명 선택",
            options=list(option_map.keys()),
            key="clarify_process_selectbox",
        )

        if st.button("선택한 공정으로 계속 진행", key="clarify_process_retry_btn"):
            selected_process = option_map[selected_label]

            try:
                next_plan = request_continue(
                    intent=plan.get("intent", {}),
                    updates={"process_name": selected_process},
                )
                st.session_state["llm_plan"] = next_plan
                st.session_state["llm_result"] = None

                if next_plan.get("status") == "ready_for_approval":
                    result = request_execute(next_plan)
                    st.session_state["llm_result"] = result

                st.rerun()

            except Exception as e:
                st.error(f"공정 선택 후 진행 실패: {e}")

    else:
        st.warning(plan.get("message", "추가 정보가 필요합니다."))
        with st.expander("상세 응답 보기", expanded=False):
            st.json(plan)


def render_interpretation_summary(plan: dict):
    """
    사용자 질문을 시스템이 어떻게 해석했는지 간단히 보여줌.
    """
    intent = plan.get("intent") or {}
    if not intent:
        return

    process_name = intent.get("process_name")
    customer_model = intent.get("customer_model")
    source_system = intent.get("source_system")
    selected_date = intent.get("selected_date")
    rank_direction = intent.get("rank_direction")
    ranking_mode = intent.get("ranking_mode")
    top_n = intent.get("top_n")

    rows = []
    if source_system:
        rows.append(("조회 소스", source_system))
    if process_name:
        rows.append(("해석된 공정명", process_name))
    if customer_model:
        rows.append(("해석된 모델", customer_model))
    if selected_date:
        rows.append(("해석된 날짜", selected_date))
    if rank_direction:
        rows.append(("순위 방향", rank_direction))
    if ranking_mode:
        rows.append(("랭킹 모드", ranking_mode))
    if top_n:
        rows.append(("순위 개수", top_n))

    if rows:
        with st.expander("질문 해석 보기", expanded=False):
            df = pd.DataFrame(rows, columns=["항목", "값"])
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_plan():
    plan = st.session_state.get("llm_plan")
    if not plan:
        return

    status = plan.get("status")

    st.markdown("## 분석 결과")

    if status == "unsupported":
        st.error(plan.get("message", "지원하지 않는 질문입니다."))
        with st.expander("상세 응답 보기", expanded=False):
            st.json(plan)
        return

    if status == "need_clarification":
        render_clarification_ui(plan)
        return

    if status == "error":
        st.error(plan.get("message", "오류가 발생했습니다."))
        with st.expander("상세 응답 보기", expanded=False):
            st.json(plan)
        return

    if status == "ready_for_approval":
        st.success(plan.get("message", "실행 계획이 준비되었습니다."))

        render_interpretation_summary(plan)

        with st.expander("실행 계획 / SQL 미리보기", expanded=False):
            st.markdown("### 실행 계획")
            st.json(plan.get("execution_plan", {}))

            st.markdown("### SQL 미리보기")
            st.code(plan.get("sql_preview", ""), language="sql")


def render_result_chart(df: pd.DataFrame):
    if df.empty:
        return

    cols = set(df.columns)

    if {"날짜", "uph"}.issubset(cols):
        work = df.copy()
        work["날짜"] = pd.to_datetime(work["날짜"], errors="coerce")
        work["uph"] = pd.to_numeric(work["uph"], errors="coerce")

        if "호기" in work.columns and work["호기"].nunique() == 1:
            fig = px.line(work, x="날짜", y="uph", title="UPH Trend")
            st.plotly_chart(fig, use_container_width=True)
            return

        if "호기" in work.columns and work["날짜"].nunique() == 1:
            fig = px.bar(work, x="호기", y="uph", title="호기별 UPH")
            st.plotly_chart(fig, use_container_width=True)
            return

        fig = px.line(work, x="날짜", y="uph", title="UPH Trend")
        st.plotly_chart(fig, use_container_width=True)


def render_ranked_result(result: dict, df: pd.DataFrame):
    """
    ranked 결과를 보기 좋게 표시
    - combined_rank=True 면 Best / Worst 분리 표시
    - 각 그룹에 bar chart 표시
    - Best/Worst 차트는 동일 y축 스케일 사용
    - overall_avg_uph가 있으면 빨간 점선 표시
    """
    summary = result.get("summary") or {}
    combined_rank = bool(summary.get("combined_rank", False))
    overall_avg_uph = summary.get("overall_avg_uph")

    if overall_avg_uph is not None:
        st.caption(f"전체 평균 UPH: {overall_avg_uph:,.2f}")

    if combined_rank and {"구분", "순위", "호기", "uph"}.issubset(df.columns):
        best_df = df[df["구분"] == "Best"].copy()
        worst_df = df[df["구분"] == "Worst"].copy()

        combined_uph = pd.concat(
            [
                pd.to_numeric(best_df.get("uph"), errors="coerce"),
                pd.to_numeric(worst_df.get("uph"), errors="coerce"),
            ],
            ignore_index=True,
        ).dropna()

        y_range = None
        if not combined_uph.empty:
            ymin = float(combined_uph.min())
            ymax = float(combined_uph.max())

            if overall_avg_uph is not None:
                ymin = min(ymin, float(overall_avg_uph))
                ymax = max(ymax, float(overall_avg_uph))

            gap = ymax - ymin
            pad = gap * 0.15 if gap > 0 else max(abs(ymax) * 0.1, 1.0)
            y_range = [max(0, ymin - pad), ymax + pad]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Best")
            if best_df.empty:
                st.info("Best 결과가 없습니다.")
            else:
                st.dataframe(best_df, use_container_width=True, hide_index=True)

                chart_df = best_df.copy()
                chart_df["호기"] = chart_df["호기"].astype(str)
                chart_df["uph"] = pd.to_numeric(chart_df["uph"], errors="coerce")

                fig = px.bar(
                    chart_df,
                    x="호기",
                    y="uph",
                    text="uph",
                    title="Best 호기 UPH"
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig.update_layout(height=320)

                if y_range is not None:
                    fig.update_yaxes(range=y_range)

                if overall_avg_uph is not None:
                    fig.add_hline(
                        y=float(overall_avg_uph),
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"평균 UPH: {overall_avg_uph:,.2f}",
                        annotation_position="top left",
                    )

                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### Worst")
            if worst_df.empty:
                st.info("Worst 결과가 없습니다.")
            else:
                st.dataframe(worst_df, use_container_width=True, hide_index=True)

                chart_df = worst_df.copy()
                chart_df["호기"] = chart_df["호기"].astype(str)
                chart_df["uph"] = pd.to_numeric(chart_df["uph"], errors="coerce")

                fig = px.bar(
                    chart_df,
                    x="호기",
                    y="uph",
                    text="uph",
                    title="Worst 호기 UPH"
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig.update_layout(height=320)

                if y_range is not None:
                    fig.update_yaxes(range=y_range)

                if overall_avg_uph is not None:
                    fig.add_hline(
                        y=float(overall_avg_uph),
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"평균 UPH: {overall_avg_uph:,.2f}",
                        annotation_position="top left",
                    )

                st.plotly_chart(fig, use_container_width=True)

    else:
        st.dataframe(df, use_container_width=True)

        if {"호기", "uph"}.issubset(df.columns):
            chart_df = df.copy()
            chart_df["호기"] = chart_df["호기"].astype(str)
            chart_df["uph"] = pd.to_numeric(chart_df["uph"], errors="coerce")

            y_range = None
            series = chart_df["uph"].dropna()
            if not series.empty:
                ymin = float(series.min())
                ymax = float(series.max())

                if overall_avg_uph is not None:
                    ymin = min(ymin, float(overall_avg_uph))
                    ymax = max(ymax, float(overall_avg_uph))

                gap = ymax - ymin
                pad = gap * 0.15 if gap > 0 else max(abs(ymax) * 0.1, 1.0)
                y_range = [max(0, ymin - pad), ymax + pad]

            fig = px.bar(
                chart_df,
                x="호기",
                y="uph",
                text="uph",
                title="호기별 UPH"
            )
            fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig.update_layout(height=320)

            if y_range is not None:
                fig.update_yaxes(range=y_range)

            if overall_avg_uph is not None:
                fig.add_hline(
                    y=float(overall_avg_uph),
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"평균 UPH: {overall_avg_uph:,.2f}",
                    annotation_position="top left",
                )

            st.plotly_chart(fig, use_container_width=True)


def render_result():
    result = st.session_state.get("llm_result")
    if not result:
        return

    st.markdown("## 실행 결과")

    if result.get("status") != "completed":
        st.error(result.get("message", "실행 중 오류가 발생했습니다."))
        with st.expander("상세 응답 보기", expanded=False):
            st.json(result)
        return

    if result.get("natural_response"):
        st.info(result["natural_response"])

    table = result.get("result_table")
    if not table:
        return

    df = pd.DataFrame(table)

    tool_name = result.get("tool_name", "")
    if tool_name in [
        "get_mes_best_worst_ranked_machines",
        "get_itas_best_worst_ranked_machines",
        "get_mes_ranked_machines",
        "get_itas_ranked_machines",
    ]:
        render_ranked_result(result, df)
    else:
        st.dataframe(df, use_container_width=True)
        render_result_chart(df)


def main():
    init_session_state()
    render_header()
    render_question_input()

    if st.button("질문 분석 및 실행", key="analyze_execute_btn"):
        analyze_and_maybe_execute()

    st.markdown("---")
    render_plan()
    render_result()


if __name__ == "__main__":
    main()