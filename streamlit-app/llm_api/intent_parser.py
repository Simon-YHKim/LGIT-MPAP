from __future__ import annotations

import re
from llm_api.vllm_client import VLLMClient


def detect_source_system(question: str) -> str:
    q = (question or "").lower()

    itas_keywords = [
        "itas",
        "i-tas",
        "itas uph",
        "아이타스",
    ]

    if any(keyword in q for keyword in itas_keywords):
        return "ITAS"

    return "MES"


def normalize_process_name(name: str | None) -> str | None:
    if not name:
        return name

    name = str(name).strip()
    quote_chars = ['"', "'", '“', '”', '‘', '’']

    while len(name) >= 2 and name[0] in quote_chars and name[-1] in quote_chars:
        name = name[1:-1].strip()

    if name and name[0] in quote_chars:
        name = name[1:].strip()
    if name and name[-1] in quote_chars:
        name = name[:-1].strip()

    name = name.replace("공정", "").strip()
    name = " ".join(name.split())

    return name or None


def normalize_customer_model(name: str | None) -> str | None:
    if not name:
        return name

    name = str(name).strip()
    quote_chars = ['"', "'", '“', '”', '‘', '’']

    while len(name) >= 2 and name[0] in quote_chars and name[-1] in quote_chars:
        name = name[1:-1].strip()

    if name and name[0] in quote_chars:
        name = name[1:].strip()
    if name and name[-1] in quote_chars:
        name = name[:-1].strip()

    name = name.replace("모델", "").strip()
    name = " ".join(name.split())

    return name or None


def normalize_machine_no(machine_no: str | None) -> str | None:
    if machine_no is None:
        return None

    value = str(machine_no).strip()

    quote_chars = ['"', "'", '“', '”', '‘', '’']
    while len(value) >= 2 and value[0] in quote_chars and value[-1] in quote_chars:
        value = value[1:-1].strip()

    if value.endswith("호기"):
        value = value[:-2].strip()

    value = " ".join(value.split())

    return value or None


def normalize_rank_direction(rank_direction: str | None) -> str | None:
    if not rank_direction:
        return None

    text = str(rank_direction).strip().lower()

    best_aliases = {"best", "top", "상위", "베스트", "최상위", "최고"}
    worst_aliases = {"worst", "bottom", "하위", "워스트", "최하위", "최저"}

    if text in best_aliases:
        return "best"

    if text in worst_aliases:
        return "worst"

    return text


def normalize_top_n(top_n) -> int | None:
    if top_n is None or top_n == "":
        return None

    try:
        n = int(top_n)
        return n if n > 0 else None
    except Exception:
        pass

    text = str(top_n).strip()
    mapping = {
        "한": 1,
        "하나": 1,
        "두": 2,
        "둘": 2,
        "세": 3,
        "셋": 3,
        "네": 4,
        "넷": 4,
        "다섯": 5,
    }
    return mapping.get(text)


def normalize_selected_date(selected_date: str | None) -> str | None:
    if not selected_date:
        return selected_date

    text = str(selected_date).strip().lower()

    if text in ["오늘", "today"]:
        return "today"

    if text in ["어제", "yesterday"]:
        return "yesterday"

    return selected_date


def extract_top_n_from_question(question: str) -> int | None:
    """
    질문 원문에서 숫자 개수 추출
    예:
    - 3개
    - top 4
    - 상위 5개
    - 하위 2개
    """
    if not question:
        return None

    q = str(question)

    patterns = [
        r'(\d+)\s*개',
        r'top\s*(\d+)',
        r'상위\s*(\d+)',
        r'하위\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, q, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

    return None


def postprocess_ranking_intent(question: str, parsed: dict) -> dict:
    """
    LLM 랭킹 파싱 후 질문 원문 기준으로 보정
    """
    q = (question or "").lower()

    has_best = any(x in q for x in ["best", "베스트", "상위"])
    has_worst = any(x in q for x in ["worst", "워스트", "하위"])

    explicit_top_n = extract_top_n_from_question(question)
    if explicit_top_n is not None:
        parsed["top_n"] = explicit_top_n

    # 베스트만 있으면 -> ranked best
    if has_best and not has_worst:
        parsed["intent_name"] = "get_ranked_machines"
        parsed["rank_direction"] = "best"

    # 워스트만 있으면 -> ranked worst
    elif has_worst and not has_best:
        parsed["intent_name"] = "get_ranked_machines"
        parsed["rank_direction"] = "worst"

    # 둘 다 있으면
    elif has_best and has_worst:
        if parsed.get("top_n"):
            parsed["intent_name"] = "get_best_worst_ranked_machines"
        else:
            parsed["intent_name"] = "get_best_worst_machine"

    return parsed


def build_intent_prompts(question: str) -> tuple[str, str]:
    system_prompt = """
당신은 제조 데이터 질의 해석기입니다.
반드시 JSON 객체만 출력하세요.
설명 문장, 코드블록, 마크다운은 출력하지 마세요.

지원 가능한 intent:
- get_uph_recent_days
- get_uph_day_by_machine
- get_uph_machine_trend
- get_best_worst_machine
- get_ranked_machines
- get_best_worst_ranked_machines
- unsupported

판단 규칙:
1. "최근 N일", "지난 N일" + 공정 + "UPH" => get_uph_recent_days
2. "오늘", "어제", 특정 날짜 + 공정 + "호기별 UPH" => get_uph_day_by_machine
3. "최근 N일" + 공정 + 호기 + "UPH 추이" 또는 "UPH 트렌드" => get_uph_machine_trend
4. "오늘", "어제", 특정 날짜 + 공정 + "best/worst 호기" => get_best_worst_machine
5. "베스트 3개", "워스트 3개", "상위 3개 호기", "하위 3개 호기"처럼
   한 방향의 여러 개 호기 순위를 묻는 질문은 get_ranked_machines
6. "best worst 3개", "베스트 워스트 각각 3개", "상위 하위 3개"처럼
   best와 worst를 모두 여러 개 묻는 질문은 get_best_worst_ranked_machines
7. 질문이 모호하면 need_clarification=true
8. 모르는 값은 null
9. "3호기"는 machine_no = "3"
10. "오늘"이면 selected_date는 "today"
11. "어제"이면 selected_date는 "yesterday"
12. "최근 N일"이면 recent_days에 숫자를 넣는다
13. 지원 불가면 intent_name = "unsupported"
14. process_name은 핵심 이름만 추출한다
15. customer_model이 질문에 있으면 customer_model에 넣는다
16. "베스트", "상위", "top" => rank_direction = "best"
17. "워스트", "하위", "bottom" => rank_direction = "worst"
18. 순위 개수가 없으면 top_n은 null
19. "베스트 호기", "워스트 호기"처럼 1개만 묻는 질문은 get_best_worst_machine 우선
20. "베스트 3개", "워스트 5개", "상위 3개"처럼 개수가 명시되면 get_ranked_machines
21. "베스트 워스트 3개", "상위 하위 3개"처럼 best와 worst가 함께 있고 숫자가 있으면 get_best_worst_ranked_machines

예시:
- APS Test 공정 -> process_name = APS Test
- R53A 모델 -> customer_model = R53A
- 베스트 3개 호기 -> intent_name = get_ranked_machines, rank_direction = best, top_n = 3
- 오늘 APS Test best worst 호기 -> intent_name = get_best_worst_machine
- 오늘 APS Test best worst 3개 호기 -> intent_name = get_best_worst_ranked_machines, top_n = 3

중요:
- source_system은 추론하지 말 것
- source_system은 null이어도 됨
- process_name, customer_model, machine_no, 날짜 관련 필드 추출에 집중할 것
- "베스트 호기 4개"는 get_ranked_machines 이고 get_best_worst_ranked_machines가 아니다
- "워스트 호기 4개"도 get_ranked_machines 이다
- "best worst 4개"처럼 둘 다 명시된 경우에만 get_best_worst_ranked_machines 이다

반환 JSON 필드:
- intent_name
- source_system
- process_name
- customer_model
- machine_no
- date_type
- recent_days
- selected_date
- start_date
- end_date
- rank_direction
- top_n
- need_clarification
- missing_slots
"""

    user_prompt = f"""
사용자 질문:
{question}

JSON만 반환하세요.
"""
    return system_prompt, user_prompt


def parse_intent(question: str) -> dict:
    client = VLLMClient()
    system_prompt, user_prompt = build_intent_prompts(question)
    result = client.chat_json(system_prompt, user_prompt)

    forced_source = detect_source_system(question)
    normalized_process_name = normalize_process_name(result.get("process_name"))
    normalized_customer_model = normalize_customer_model(result.get("customer_model"))
    normalized_machine_no = normalize_machine_no(result.get("machine_no"))
    normalized_rank_direction = normalize_rank_direction(result.get("rank_direction"))
    normalized_top_n = normalize_top_n(result.get("top_n"))
    normalized_selected_date = normalize_selected_date(result.get("selected_date"))

    parsed = {
        "intent_name": result.get("intent_name"),
        "source_system": forced_source,
        "process_name": normalized_process_name,
        "customer_model": normalized_customer_model,
        "machine_no": normalized_machine_no,
        "date_type": result.get("date_type"),
        "recent_days": result.get("recent_days"),
        "selected_date": normalized_selected_date,
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "rank_direction": normalized_rank_direction,
        "top_n": normalized_top_n,
        "need_clarification": bool(result.get("need_clarification", False)),
        "missing_slots": result.get("missing_slots") or [],
    }

    parsed = postprocess_ranking_intent(question, parsed)
    return parsed