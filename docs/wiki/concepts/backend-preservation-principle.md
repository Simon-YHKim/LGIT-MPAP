---
type: concept
tags: [principle, refactor-safety, handoff, deployment]
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
  - "[[concepts/zip-handoff]]"
  - "[[concepts/backend-freeze-gate]]"
---

# Backend Preservation Principle

> **데이터 호출 앞단 (DB·인증·SQL·session·연결방식·CDN fallback) 은 한 줄도 변경 금지.
> 변경 가능한 것은 표현 layer 만 (HTML 구조 / CSS / 시각 정렬).**

LGIT-MPAP 에서 사용자 (Simon) 가 명시한 대원칙. 이전 엔지니어가 의식적으로
잡은 패턴은 회사 운영 환경에 최적화된 결정 — Claude 가 "best practice"
명목으로 변경하면 운영성 손실 + 회사 방식 위반.

---

## 무엇이 "앞단" 인가

| 영역 | 보존 패턴 |
|---|---|
| DB 연결 방법 | `get_conn()` 매 호출 fresh `psycopg2.connect(...)` |
| DB 패스워드 fallback | `os.getenv('X', '!Q2w3e4r5t')` literal |
| 인증 흐름 | `auth_guard.require_login()` + `st.session_state` |
| SQL dialect | `NOW()` (Postgres-only) |
| CDN @import | `Pretendard` / `IBM Plex Mono` from cdn.jsdelivr/googleapis |
| session_state 키 | 87개 기존 키 |
| 함수 시그니처 | 576개 함수 이름·인자 |
| SQL 쿼리 문자열 | 223개 |
| `secrets.toml` + `setting.ini` git 추적 | 폐쇄망 정책 |

## 무엇이 "표현 layer" 인가

- `st.markdown(unsafe_allow_html=True)` 의 HTML 구조
- 페이지별 inline `<style>` 블록
- `ui/vitals/components.py` primitive 추가/사용
- `ui/vitals/theme.py` CSS 토큰
- preview HTML/CSS

---

## 검증 ([[concepts/backend-freeze-gate]])

`verify_backend_freeze.py` AST diff:
- 함수 정의 (이름 + signature) 추출
- SQL 문자열 (>= 30 chars, SELECT/INSERT/...) 추출
- `st.session_state` 키 (subscript + attribute)
- top-level imports

baseline JSON 과 diff. **삭제·시그니처 변경**만 fail (추가는 OK).

---

## 위반 사례 (실제로 일어났던)

### 1. DB 패스워드 fallback 제거 시도
- 보안 best practice 명목으로 literal `!Q2w3e4r5t` 제거
- 실제 보안 이득: 0 (같은 비번이 secrets.toml + setting.ini 에도 평문)
- 운영성 손실: 새 PC 에서 env 누락 시 RuntimeError
- 결과: revert (`717732f`)

### 2. tracking.py 매 호출 fresh connection → SQLAlchemy QueuePool
- "PG max_connections 고갈" 가설로 변경
- API 호환은 유지했지만 내부 동작 방식 변경 = 회사 방식 변경
- 결과: revert (`89b2d95`)

### 3. SQL `NOW()` → `CURRENT_TIMESTAMP`
- "SQLite 호환" 명목으로 변경
- 회사는 PG 만 씀 — SQLite 호환 불필요
- 결과: revert

### 4. CDN @import 제거
- "폐쇄망에선 dead load" 명목으로 제거
- 실제는 외부망 fallback 의도
- 결과: revert + verify_no_external 의 ALLOW_SUBSTRINGS 에 명시

---

## Lesson

**회사방식 변경 전 질문 필수**: "왜 그렇게 짰을까?"

dead-looking / suboptimal-looking 코드도 의도가 있을 수 있음.
"보안 / 성능 / dialect 호환" 같은 추상적 best practice 는 운영 환경의
구체적 결정을 이길 수 없음.

---

## 적용 ([[projects/lgit-mpap]])

repo `CLAUDE.md` 에 codify:
- 절대 변경 금지 9 영역 (DB 연결, 패스워드, 인증, SQL dialect, CDN, session keys, function sigs, SQL strings, secrets.toml)
- 변경 가능 5 영역 (HTML, inline style, primitive, theme, preview)

`pre-commit hook` 으로 매 commit 마다 enforcement.
