from __future__ import annotations

import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from auth_guard import require_login
require_login(
    page_name="MaxCapa_Chat",
    page_path="pages/6_MaxCapa_Chat.py"
)

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()

# preview-streamlit-clone.html sec-chat parity marker (표현 layer)
import streamlit as _st_marker  # noqa: E402
_st_marker.markdown(
    '<div class="sc-page-section sc-chat-section is-active" data-sec="chat"></div>',
    unsafe_allow_html=True
)
# components.html iframe 으로 parent body class 조작 (markdown script 는 sanitize)
import streamlit.components.v1 as _comp_for_body_class  # noqa: E402
_comp_for_body_class.html(
    '<script>parent.document.body.classList.remove("is-login-active");'
    'parent.document.body.classList.add("is-chat-active");</script>',
    height=0
)
from ui.vitals import render_section_header as _render_section_header  # noqa: E402
_render_section_header("chat")
from ui.vitals.components import render_csv_export, render_sub_head  # noqa: E402

from ui.analytics import inject_tracker
inject_tracker(page_name="6_MaxCapa_Chat", page_path="pages/6_MaxCapa_Chat.py")

FASTAPI_BASE_URL = "http://localhost:9000"

CHAT_EXAMPLES = [
    "CM모델A의 어제 UPH 평균 알려줘",
    "FOL-A 라인 최근 1주일 일별 UPH 추이를 보여줘",
    "ITAS UPH 기준 CM모델A vs CM모델B 4월 비교해줘",
    "지난달 UPH 상위 5개 모델을 라인별로 정리해줘",
]


def render_header():
    """Preview sec-chat body: data-source hint, hero, and examples."""
    st.markdown(
        """
        <style>
        /* Status 시맨틱 — LLM 응답 검증 / API 가용성 라벨에 사용 */
        .chat-status-good { color: var(--status-good, #1F8B4C); font-weight: 700; }
        .chat-status-warn { color: var(--status-warn, #B57F1B); font-weight: 700; }
        .chat-status-bad  { color: var(--status-bad,  #B23A48); font-weight: 700; }
        .chat-hint {
            border: 1px solid var(--border);
            background: var(--card-bg);
            padding: 12px 14px;
            margin: 0 0 14px;
        }
        .chat-hint__title {
            font-family: var(--font-mono);
            font-size: 11px;
            letter-spacing: .08em;
            color: var(--ink-muted);
            margin-bottom: 5px;
        }
        .chat-hint__body {
            font-size: 13px;
            color: var(--ink-body);
            line-height: 1.55;
        }
        .chat-hint code,
        .chat-hero code {
            font-family: var(--font-mono);
            background: var(--soft); padding: 1px 6px;
            font-size: 11px; color: var(--primary-dark); font-weight: 600;
        }
        .chat-hero {
            display: flex;
            align-items: center;
            gap: 14px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            padding: 18px 20px;
            margin: 0 0 18px;
        }
        .chat-hero__mark {
            width: 44px;
            height: 44px;
            display: grid;
            place-items: center;
            background: var(--soft);
            color: var(--primary);
            flex: 0 0 auto;
        }
        .chat-hero__mark svg {
            width: 22px;
            height: 22px;
        }
        .chat-hero__title {
            margin: 0 0 4px;
            font-family: var(--font-display, var(--font-body));
            font-size: 24px;
            font-weight: 700;
            color: var(--ink-body);
            letter-spacing: 0;
        }
        .chat-hero__title em {
            color: var(--primary);
            font-style: normal;
        }
        .chat-hero__sub {
            margin: 0;
            color: var(--ink-muted);
            font-size: 13px;
        }
        .chat-examples {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin: 0 0 18px;
        }
        @media (max-width: 980px) {
            .chat-examples { grid-template-columns: 1fr; }
            .chat-hero { align-items: flex-start; }
        }
        .chat-example {
            display: flex;
            align-items: center;
            gap: 9px;
            padding: 10px 12px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: var(--ink-body);
            font-size: 13px;
            line-height: 1.45;
        }
        .chat-example__icon {
            width: 22px;
            height: 22px;
            display: grid;
            place-items: center;
            flex: 0 0 auto;
            background: var(--primary-tint);
            color: var(--primary-dark);
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 700;
        }
        </style>
        <div class="cmp-sub-head">
          <div class="cmp-sub-head__left">
            <span class="cmp-sub-head__bar" aria-hidden="true"></span>
            <h3 class="cmp-sub-head__title">데이터 소스 · 분기 규칙</h3>
          </div>
          <span class="cmp-sub-head__meta">기본 MES UPH / ITAS 키워드 시 ITAS UPH 자동 분기</span>
        </div>
        <div class="chat-hint">
          <div class="chat-hint__title"><strong>DATA SOURCE</strong> · 기본 / 분기 규칙</div>
          <div class="chat-hint__body">
            기본 조회는 <code>uph_input_runtime_daily_model</code> (MES UPH),
            질문에 <code>ITAS</code> 키워드 감지 시 <code>itas_uph_result</code> (ITAS UPH)로 자동 분기합니다.
          </div>
        </div>
        <div class="chat-hero">
          <div class="chat-hero__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div>
            <h2 class="chat-hero__title">생산지표를 <em>자연어</em>로 물어보세요</h2>
            <p class="chat-hero__sub">모델 / 라인 / 기간 / 지표를 한 문장에 담아 입력하세요.</p>
          </div>
        </div>
        <div class="cmp-sub-head" style="margin-top:1.25rem;">
          <div class="cmp-sub-head__left">
            <span class="cmp-sub-head__bar" aria-hidden="true"></span>
            <h3 class="cmp-sub-head__title">지원 예시</h3>
          </div>
          <span class="cmp-sub-head__meta">예시를 참고해 질문을 입력하세요</span>
        </div>
        <div class="chat-examples">
          <div class="chat-example"><span class="chat-example__icon">Q1</span>최근 3일 APS Test 공정의 UPH는 얼마인가?</div>
          <div class="chat-example"><span class="chat-example__icon">Q2</span>오늘 APS Test 호기별 UPH 보여줘</div>
          <div class="chat-example"><span class="chat-example__icon">Q3</span>최근 7일 APS Test 3호기 UPH 추이 보여줘</div>
          <div class="chat-example"><span class="chat-example__icon">Q4</span>오늘 APS Test best worst 호기는?</div>
          <div class="chat-example"><span class="chat-example__icon">Q5</span>최근 7일 APS Test 공정의 R53A 모델 UPH는?</div>
          <div class="chat-example"><span class="chat-example__icon">Q6</span>ITAS UPH 기준 최근 3일 APS Test의 UPH는 얼마인가?</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_session_state():
    if "llm_plan" not in st.session_state:
        st.session_state["llm_plan"] = None
    if "llm_result" not in st.session_state:
        st.session_state["llm_result"] = None
    if "llm_question" not in st.session_state:
        st.session_state["llm_question"] = ""
    if "llm_source_hint" not in st.session_state:
        st.session_state["llm_source_hint"] = "MES UPH"


def render_chat_shell_css():
    st.markdown(
        """
        <style>
        .max-chat-layout {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 320px;
            gap: 14px;
            align-items: start;
        }
        .max-chat-panel,
        .max-chat-side {
            border: 1px solid var(--border);
            background: var(--card-bg);
        }
        .max-chat-panel {
            min-height: 560px;
            display: flex;
            flex-direction: column;
        }
        .max-chat-thread {
            min-height: 320px;
            padding: 18px 18px 8px;
            border-bottom: 1px solid var(--border);
            background:
                linear-gradient(180deg, rgba(165,0,52,.035), rgba(255,255,255,0) 160px),
                var(--card-bg);
        }
        .max-chat-bubble-row {
            display: flex;
            margin: 0 0 12px;
        }
        .max-chat-bubble-row.is-user {
            justify-content: flex-end;
        }
        .max-chat-bubble {
            max-width: 76%;
            padding: 12px 14px;
            border: 1px solid var(--border);
            background: #FFFFFF;
            color: var(--ink-body);
            font-size: 13px;
            line-height: 1.55;
        }
        .max-chat-bubble.is-user {
            background: var(--primary);
            border-color: var(--primary);
            color: #FFFFFF;
            font-weight: 700;
        }
        .max-chat-bubble__meta {
            display: block;
            margin-bottom: 5px;
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 800;
            letter-spacing: .08em;
            color: var(--ink-subtle);
        }
        .max-chat-bubble.is-user .max-chat-bubble__meta {
            color: rgba(255,255,255,.72);
        }
        .max-chat-composer {
            padding: 14px 16px 16px;
            background: var(--soft);
        }
        .max-chat-composer div[data-testid="stTextArea"] textarea {
            min-height: 112px !important;
            border-radius: 0 !important;
            font-size: 14px !important;
            line-height: 1.55 !important;
            background: #FFFFFF !important;
        }
        .max-chat-side {
            padding: 12px;
        }
        .max-chat-source {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin: 8px 0 12px;
        }
        .max-chat-source .stButton > button {
            min-height: 30px !important;
            padding: 0 10px !important;
            font-family: var(--font-mono) !important;
            font-size: 11px !important;
        }
        .max-chat-example-list .stButton > button {
            justify-content: flex-start !important;
            min-height: 42px !important;
            padding: 8px 10px !important;
            white-space: normal !important;
            text-align: left !important;
            font-size: 12px !important;
            line-height: 1.35 !important;
        }
        .max-chat-data-note {
            margin: 0 0 12px;
            padding: 10px 12px;
            border: 1px solid var(--border);
            background: var(--soft);
            color: var(--ink-muted);
            font-size: 12px;
            line-height: 1.55;
        }
        .max-chat-data-note code {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--primary-dark);
            background: var(--primary-tint);
            padding: 1px 5px;
        }
        @media (max-width: 1100px) {
            .max-chat-layout { grid-template-columns: 1fr; }
            .max-chat-panel { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_chat_export_df() -> pd.DataFrame:
    rows = []
    question = st.session_state.get("llm_question", "")
    if question:
        rows.append({"type": "question", "content": question})

    plan = st.session_state.get("llm_plan")
    if plan:
        rows.append({
            "type": "plan",
            "content": plan.get("message") or plan.get("status") or "",
        })

    result = st.session_state.get("llm_result")
    if result:
        rows.append({
            "type": "result",
            "content": result.get("natural_response") or result.get("message") or result.get("status") or "",
        })
    return pd.DataFrame(rows or [{"type": "empty", "content": "No conversation yet"}])


def set_question_from_example(example: str):
    st.session_state["llm_question"] = example
    st.session_state["llm_plan"] = None
    st.session_state["llm_result"] = None
    st.rerun()


def render_chat_workspace():
    render_chat_shell_css()

    st.markdown(
        """
        <div class="max-chat-data-note">
            <strong>DATA SOURCE</strong>
            기본 조회는 <code>uph_input_runtime_daily_model</code>을 사용하고,
            질문에 <code>ITAS</code>가 포함되면 <code>itas_uph_result</code>로 자동 분기합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.74, 0.26], gap="medium")

    with right:
        st.markdown('<div class="max-chat-side">', unsafe_allow_html=True)
        render_sub_head("지원 예시", "클릭하면 입력창에 반영")
        st.markdown('<div class="max-chat-example-list">', unsafe_allow_html=True)
        for idx, example in enumerate(CHAT_EXAMPLES, start=1):
            if st.button(f"Q{idx}. {example}", key=f"chat_example_{idx}", use_container_width=True):
                set_question_from_example(example)
        st.markdown('</div>', unsafe_allow_html=True)

        render_sub_head("데이터 모드", st.session_state.get("llm_source_hint", "MES UPH"))
        st.markdown('<div class="max-chat-source">', unsafe_allow_html=True)
        src_cols = st.columns(3)
        if src_cols[0].button("MES UPH", key="chat_src_mes", use_container_width=True):
            st.session_state["llm_source_hint"] = "MES UPH"
            st.rerun()
        if src_cols[1].button("ITAS UPH", key="chat_src_itas", use_container_width=True):
            st.session_state["llm_source_hint"] = "ITAS UPH"
            st.rerun()
        if src_cols[2].button("AUTO", key="chat_src_auto", use_container_width=True):
            st.session_state["llm_source_hint"] = "AUTO"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        render_csv_export(
            build_chat_export_df(),
            label="CSV 내보내기",
            filename="maxcapa_chat.csv",
            key="chat_csv_export",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with left:
        st.markdown('<div class="max-chat-panel"><div class="max-chat-thread">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="max-chat-bubble-row">
              <div class="max-chat-bubble">
                <span class="max-chat-bubble__meta">MAXCAPA</span>
                생산지표를 자연어로 물어보세요. 모델, 공정, 기간, 데이터 소스가 부족하면 제가 후보를 제시합니다.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        question = st.session_state.get("llm_question", "").strip()
        if question:
            from html import escape as _escape_html
            st.markdown(
                f"""
                <div class="max-chat-bubble-row is-user">
                  <div class="max-chat-bubble is-user">
                    <span class="max-chat-bubble__meta">YOU</span>
                    {_escape_html(question)}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        plan = st.session_state.get("llm_plan")
        result = st.session_state.get("llm_result")
        if not plan and not result:
            st.markdown(
                """
                <div class="max-chat-bubble-row">
                  <div class="max-chat-bubble">
                    <span class="max-chat-bubble__meta">READY</span>
                    예시를 누르거나 아래 입력창에 질문을 작성한 뒤 실행하세요.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div><div class="max-chat-composer">', unsafe_allow_html=True)
        render_question_input()
        action_cols = st.columns([1.4, 1, 1, 4], gap="small")
        if action_cols[0].button("질문 분석 및 실행", key="analyze_execute_btn", type="primary", use_container_width=True):
            analyze_and_maybe_execute()
            st.rerun()
        if action_cols[1].button("초기화", key="chat_reset_btn", use_container_width=True):
            st.session_state["llm_question"] = ""
            st.session_state["llm_plan"] = None
            st.session_state["llm_result"] = None
            st.rerun()
        if action_cols[2].button("예시 채우기", key="chat_fill_example_btn", use_container_width=True):
            set_question_from_example(CHAT_EXAMPLES[0])
        st.markdown('</div></div>', unsafe_allow_html=True)

        render_plan()
        render_result()


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

    # Vitals 톤 — 분석 결과 섹션 헤딩 (좌 4px 와인 bar + LG EI Headline)
    st.markdown(
        """
        <style>
        .vit-chat-section {
            display:flex; align-items:center; gap:10px;
            margin: 22px 0 12px;
            padding-left: 4px;
        }
        .vit-chat-section__bar {
            width:4px; height:20px; background: var(--primary); border-radius:0;
        }
        .vit-chat-section__title {
            margin:0; font-family: var(--font-display, var(--font-body));
            font-size:18px; font-weight:700; letter-spacing:-0.01em;
            color: var(--ink-body);
        }
        .vit-chat-section__sub {
            font-family: var(--font-mono);
            font-size:11px; font-weight:600; color: var(--ink-subtle);
            letter-spacing:.08em; text-transform: uppercase;
        }
        </style>
        <div class="vit-chat-section">
          <span class="vit-chat-section__bar"></span>
          <h2 class="vit-chat-section__title">분석 결과<span class="vit-chat-section__sub" style="margin-left:10px;">PARSE · ROUTE · BUILD SQL</span></h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    # Vitals 톤 — 실행 결과 섹션 헤딩 (좌 4px 와인 bar)
    st.markdown(
        """
        <div class="vit-chat-section">
          <span class="vit-chat-section__bar"></span>
          <h2 class="vit-chat-section__title">실행 결과<span class="vit-chat-section__sub" style="margin-left:10px;">EXECUTE · DATA</span></h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    render_chat_workspace()


if __name__ == "__main__":
    main()
