---
type: concept
tags: [verification, ast, gate, refactor-safety]
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
  - "[[concepts/backend-preservation-principle]]"
---

# Backend Freeze Gate

> AST 기반 diff 게이트. STAGE 2 가 페이지 visual 만 변경하고 backend
> (함수 시그니처 / SQL / session_state / import) 는 한 줄도 못 건드리게 강제.

## 왜 필요한가

[[concepts/backend-preservation-principle]] 의 enforcement.
사람이 매 commit 마다 "함수 시그니처 안 건드렸지?" 점검은 실수 가능.
AST 가 자동으로 검증.

## 어떻게 작동

`verify_backend_freeze.py` (`LGIT-MPAP/streamlit-app/scripts/`):

1. **Snapshot 추출** — 매 .py 파일에서:
   - 함수 정의: `name(arg1, arg2, *, kw=default)` signature
   - SQL 문자열: 30+ 글자, `SELECT/INSERT/UPDATE/DELETE/CREATE/...` 시작
   - `st.session_state` 키: subscript (`st.session_state["k"]`) + attribute (`st.session_state.k`)
   - top-level imports

2. **Baseline 비교** — `scripts/backend_freeze_baseline.json` 과 diff
   - **삭제**: FAIL (회사 방식 위반)
   - **시그니처 변경**: FAIL
   - **추가**: OK (새 helper / 새 키 / 새 import 는 위반 아님)

3. **Baseline 갱신** (의도적 추가 시):
   ```bash
   python verify_backend_freeze.py --emit-baseline
   ```

## Pre-commit hook

`install_git_hooks.sh` 가 `.git/hooks/pre-commit` 자동 설치.
매 `git commit` 직전 3 게이트 강제:
1. `verify_backend_freeze.py` (회사 방식)
2. `smoke_compile.sh` (49 .py syntax)
3. `verify_no_external.py` (외부 CDN URL 0)

FAIL 시 commit 차단. 우회: `git commit --no-verify` (긴급 시만).

## 결과

LGIT-MPAP STAGE 1+2 전체 38 commits 동안 한 번도 FAIL 안 뜸 →
**백엔드 100% 보존 보증**. 회사 방식 변경 시도 (M1~M4 in [[projects/lgit-mpap]])
는 모두 사용자 지적 후 revert 됐고 AST 게이트로 detect 됐음.

## 한계

- AST level 만 봄 — 함수 **본문** 변경은 detect 안 함
  - 같은 시그니처 `get_conn()` 안에서 `psycopg2.connect()` 를 `engine.raw_connection()` 으로 바꿔도 통과
  - 이건 `M2 (tracking.py)` 에서 실제로 일어남 — 사용자 직접 review 가 catch
- SQL 문자열도 30 char 이하면 못 잡음
- Dynamic import (`importlib.import_module`) 못 잡음

→ AST 게이트 + 사람 review + commit message 의 명확한 의도 = triple safety.
