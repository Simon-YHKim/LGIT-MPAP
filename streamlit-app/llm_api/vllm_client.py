import json
import re
import requests


VLLM_BASE_URL = "http://150.150.83.26:8000/v1"
VLLM_MODEL_NAME = "/home/rgkorea/models/Qwen2.5-3B-Instruct"


def extract_json_block(text: str) -> dict:
    text = (text or "").strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"JSON 파싱 실패: {text}")


class VLLMClient:
    def __init__(self, base_url: str = VLLM_BASE_URL, model_name: str = VLLM_MODEL_NAME):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 500) -> str:
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        raw = self.chat(system_prompt, user_prompt)
        return extract_json_block(raw)


def build_process_rewrite_prompts(raw_process_name: str) -> tuple[str, str]:
    system_prompt = """
당신은 제조 공정명 정규화 보조기입니다.
입력된 한글/혼합 공정 표현을 영어/약어형 공정 표현 후보로 바꿔주세요.
반드시 JSON만 출력하세요.

규칙:
1. 실제 DB 후보와 매칭하기 위한 짧은 공정명 후보를 만든다.
2. 설명 문장은 쓰지 않는다.
3. 후보는 최대 5개까지 제시한다.
4. 확실하지 않으면 가장 가능성 높은 후보만 제시한다.

반환 JSON 형식:
{
  "rewrites": ["APS Test", "APS Final Test"]
}
"""

    user_prompt = f"""
입력 공정 표현:
{raw_process_name}

JSON만 반환하세요.
"""
    return system_prompt, user_prompt


def suggest_process_rewrites(raw_process_name: str) -> list[str]:
    raw_process_name = (raw_process_name or "").strip()
    if not raw_process_name:
        return []

    client = VLLMClient()
    system_prompt, user_prompt = build_process_rewrite_prompts(raw_process_name)

    try:
        result = client.chat_json(system_prompt, user_prompt)
        rewrites = result.get("rewrites") or []
        rewrites = [str(x).strip() for x in rewrites if str(x).strip()]
        return rewrites[:5]
    except Exception as e:
        print("=== suggest_process_rewrites ERROR ===")
        print(repr(e))
        return []