# LESSONS_LEARNED.md — LGIT-MPAP / Simon-YHKim 작업 분석

> 본 문서는 Claude Code 세션을 거치며 누적된 **사용자(Simon-YHKim) 의 작업 경향 · 의사결정 패턴 · 시행착오 · 토큰 낭비 방지 룰** 의 오답노트.
> 새 세션 시작 시 이 파일과 `~/.claude/instincts/project-patterns.md` 의 LGIT-MPAP 섹션을 먼저 읽으면 동일 실수 반복 없이 곧장 작업에 진입할 수 있다.
>
> SimonK-Stack (`Simon-YHKim/SimonK-stack`) 에 직접 push 권한이 없어 본 repo 의 `docs/` 에 보관. SimonK-Stack 에 동기화하려면 수동 git remote add 후 push.

---

## 1. 사용자 정체 (누구인가)

| 항목 | 값 |
|---|---|
| 소속 | LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa TDR |
| 역할 | 1인 엔지니어 + PM (이전 엔지니어가 떠난 후 인수자) |
| 모국어 | 한국어 (영문 fallback 가능, 코드 식별자는 영문) |
| 작업 환경 | 폐쇄망 사내 PC + Streamlit 1.55 + PostgreSQL 4 DB |
| 도메인 | 설비 생산성 분석 (CMP / UPH / MTBA 등 제조업 KPI) |
| 핵심 원칙 | "이전 엔지니어가 정한 것은 한 줄도 건드리지 않는다" |

### 1.1 작업 의도 (대원칙)
1. **회사 방식 보존이 정확성보다 우선** — 비효율적으로 보이는 패턴도 폐쇄망/운영성 이유가 있음
2. **다른 사람·다른 AI 가 이어받을 수 있어야 한다** — 모든 산출물을 self-contained 문서로
3. **검증 게이트 자동화 신봉** — 사람이 매번 확인하지 않도록 4 게이트 + pre-commit hook
4. **표현 layer 만 개선** — HTML/CSS/시각 정렬은 자유, 백엔드는 freeze

---

## 2. 작업 경향 · 문제 인식 방법

### 2.1 패턴
- **STAGE 단위 진행**: STAGE 1 (분석) → STAGE 2 (백엔드 보존 + 디자인 정착) → STAGE 3 (사용자 피드백 반영)
- **commit 메시지 양식**:
  - `feat(stage3): ...`, `fix(stage3): ...`, `docs(stage3): ...`, `chore(stage3): ...`
  - 본문에 1~2 문장으로 WHY 만 설명
  - `https://claude.ai/code/session_xxx` 트레일러
- **baseline JSON 으로 변경 추적**: 576 함수 / 223 SQL / 87 session_state 키
- **다른 AI 도구로의 핸드오프 prompt** 작성을 즐김:
  - `docs/cowork...` (다른 Claude 세션 인수)
  - `docs/CODEX_PAGE_REFERENCE.md` (OpenAI Codex CLI 컨텍스트)
  - `docs/STAGE2_RELEASE_NOTES.md` (사람용 인수서)

### 2.2 문제 인식 방법
- **"사용자 명시 task N종"** 같이 task list 형태로 항상 명시 — 모호하지 않음
- **사용자 피드백 6종 / 4가지** 형태로 즉시 numerable 하게 정리
- **모든 산출물에 검증 점수 부여**: design score 95+/100, 4 게이트 PASS

### 2.3 개선 방향 (지금까지 사용자 본인이 정착시킨 것)
- ✅ pre-commit hook 자동 설치 (commit `8c55700`)
- ✅ root CLAUDE.md 에 codify (commit `9e7c122`)
- ✅ Vitals 토큰 33개 화이트리스트 (`measure_design_integration.py`)
- ✅ 폐쇄망 외부 URL 검출 게이트 (`verify_no_external.py`)
- ✅ zip 인수 자동화 (`make_handoff_zip.sh`)

---

## 3. 주로 놓치는 것 (Claude 가 자주 실수하는 부분)

| # | 실수 패턴 | 방지 룰 |
|---|---|---|
| 1 | 백엔드 freeze 인식 늦음 — DB 연결·session_state·SQL 문자열 변경 시도 | 작업 시작 전 `python streamlit-app/scripts/verify_backend_freeze.py` 1회 실행으로 baseline 확인 |
| 2 | `unsafe_allow_html=True` 사용 시 DB 값 escape 누락 | DB 에서 가져온 값을 HTML 에 박을 때 **반드시** `html.escape()` |
| 3 | 새 hex 색상 도입 → Vitals 토큰 33개 외부 색 사용 | `measure_design_integration.py` 점수 하락 시 즉시 토큰 매핑 |
| 4 | Streamlit 1.55 호환성 무시 — clone.css 의 32 data-testid selector | `streamlit==1.55.x` 고정 (requirements.txt 명시) |
| 5 | `border-radius: 0` 위반 — 둥근 모서리 자동 도입 | status dot 50% / 의식적 pill 999px 만 예외 |
| 6 | 백그라운드 에이전트 결과를 그대로 prompt 문서에 인용 (3K+ tokens) | 에이전트 prompt 에 "최종 출력은 §N 구조 markdown / 5K tokens 이내" 명시 |
| 7 | 컨텍스트 컴팩션 후 사용자 의도 추측 | 직전 사용자 메시지부터 정확히 re-read, 추측 금지 |
| 8 | "내가 한 작업 리스트업" 요청에 추측 답변 | 항상 `git log --oneline -N` + `git status` 기반 |
| 9 | Plan 모드 건너뛰기 — 작업 즉시 진행 | 백그라운드 에이전트 자연 재개 같은 예외 케이스 외엔 plan 모드 기본 |
| 10 | 디자인 작업에 바로 코드 작성 | `simon-design-first` 진단 → 레퍼런스 → 폰트 → 방향 확정 → 그 다음 코드 |
| 11 | SimonK-stack 같은 외부 repo 에 무모한 push 시도 | 시스템 프롬프트의 GitHub MCP scope (`simon-yhkim/lgit-mpap` 만) 명시 시 즉시 fallback |
| 12 | 코드에서 확인 안 된 부분 추측 작성 | "(코드에서 확인 안 됨)" 정직 표기 — 본 repo `docs/CODEX_PAGE_REFERENCE.md` §16 사례 |

---

## 4. 시행착오 & 결론 (실제 사례 기반)

### 4.1 산출물 통합 vs 분리
- **시행착오**: cowork 핸드오프 prompt (`0168689`) + Codex 페이지 레퍼런스 (`259003f`) 가 별개 파일이 됨
- **결론**: 다음번엔 `docs/HANDOFF.md` 하나에 § Sections 로 합치는 것이 토큰 효율적 (LLM context window 절약)
- **개선**: 새 핸드오프 문서 만들기 전에 기존 `docs/` 안의 핸드오프 류 확인 → append 우선

### 4.2 Explore 에이전트 출력 길이 제어
- **시행착오**: 10개 페이지 13,865 줄 정독 결과가 3K+ tokens 로 돌아옴 → 본 세션 컨텍스트 큰 비중 차지
- **결론**: 에이전트 prompt 에 "최종 보고서는 페이지별 §1~§N 구조, 각 §은 위젯/SQL/세션키 표 형식, 전체 5K tokens 이내" 같은 출력 제약 필요
- **개선 사례**: §16 "코드에서 확인 안 된 부분" 정직 표기로 추측 방지에는 성공

### 4.3 push 권한 사전 확인
- **시행착오**: SimonK-stack 에 push 시도 → 인증 토큰 없어 fail
- **결론**: 시스템 프롬프트에 GitHub MCP scope 가 명시되어 있으면 그게 진실. `git ls-remote` (read) 와 `git push --dry-run` (write) 으로 1회만 확인하고 fallback
- **개선**: 본 LESSONS_LEARNED 처럼 LGIT-MPAP `docs/` 에 보관 + 사용자가 수동으로 SimonK-stack 에 sync

### 4.4 "내가 한 작업" 메타 질문 처리
- **시행착오**: 컨텍스트 컴팩션 후 사용자가 "내가 어떤 작업들을 했었는지" 라고 물음 → 이번 세션 vs 이전 세션 구분 필요
- **결론**: 항상 `git log --oneline -20 && git status` 로 시작 → 이번 세션 commit 만 강조 + "이전 세션은 무관, 필요 시 별도" 라고 명시
- **개선**: 본 답변 형식 정착 — commit hash 7자 + 한 줄 설명 + "이번 세션 vs 이전 세션" 명확 분리

### 4.5 백엔드 freeze 위반 자동 차단
- **시행착오**: STAGE 1 초기엔 매 commit 마다 사람이 확인 → 잊혀짐
- **결론**: pre-commit hook 으로 4 게이트 자동 실행 (`8c55700`)
- **개선**: 새 함수 추가 시만 `--emit-baseline`, 변경·삭제 시는 절대 X

---

## 5. 토큰 낭비 방지 — 다음 세션 최적화 룰

### 5.1 세션 시작 (첫 1~2 turn 안에)
```bash
git log --oneline -10          # 직전 commit 흐름 파악
git status                     # 현재 상태
git branch --show-current      # 작업 브랜치 (claude/* 패턴)
cat docs/STAGE2_RELEASE_NOTES.md | head -50  # 최근 인수 컨텍스트
```

### 5.2 백그라운드 에이전트 사용 시
- prompt 끝에 항상: **"최종 보고서는 markdown § 구조 + 표, 전체 5K tokens 이내. 코드에서 확인 안 된 부분은 '(코드에서 확인 안 됨)' 정직 표기."**
- 결과 받으면 곧장 다른 작업 X — 결과 검토 → 사용자에게 status 보고 → 다음 액션 결정

### 5.3 산출물 작성 시 우선순위
1. 기존 `docs/` 안에 비슷한 핸드오프/레퍼런스 문서가 있는지 먼저 확인
2. 있으면 append (Section 추가) — 새 파일 만들기 전에
3. 없을 때만 새 파일 생성

### 5.4 검증 게이트
- 모든 commit 전에 **4 게이트** 자동 실행 (pre-commit hook 이 알아서 함)
- FAIL 시 commit 중단 → 회사 방식 위반 의심 → revert 검토

### 5.5 사용자 메타 질문 처리
- "리스트업 / 내가 한 작업 / 어디까지 했지" 류 → 항상 git log 기반 답변
- 이번 세션 commit 만 강조, 이전 세션은 "필요 시 별도" 라고 명시
- 답변 형식: commit hash + 한 줄 설명 → 카테고리별 그루핑 → end-of-turn 1-2 줄 요약

### 5.6 디자인 작업 (`simon-design-first` 가 mandatory)
사용자가 "디자인" / "UI" / "랜딩페이지" 류 키워드 → **절대 바로 코드 X**
순서: 진단 → 레퍼런스 3-5개 URL → 폰트 (Pretendard 기본) → 방향 확정 → 그제서야 코드

---

## 6. 사용자가 자주 쓰는 표현 → 의도 매핑

| 표현 | 진짜 의도 |
|---|---|
| "한 줄도 건드리지 마" | 백엔드 freeze — `verify_backend_freeze.py` PASS 필수 |
| "사용자 명시 task N종" | 모호하지 않게 정의된 task list, 1~N 번호 매겨서 처리 |
| "Cowork", "다른 세션이 이어받게" | self-contained handoff prompt 문서 작성 |
| "디자인 점수 N+" | `measure_design_integration.py` 점수 |
| "STAGE N" | 인수 인계 단계 (STAGE 2 완료, 현재 STAGE 3) |
| "회사 방식 보존" | 폐쇄망 운영성 우선, 비효율 패턴도 유지 |
| "Vitals 토큰" | 33개 CSS 토큰 화이트리스트 |
| "preview HTML/CSS" | `docs/design/` 의 정적 mockup (실제 Streamlit 과 mirror) |

---

## 7. 본 세션 (2026-05-19) 학습 요약

**한 일** (commit `259003f` 단일):
1. Explore 에이전트로 10개 페이지 13,865 줄 정독 (백그라운드)
2. 결과 토대로 `docs/CODEX_PAGE_REFERENCE.md` (840줄, 17 섹션) 작성
3. 4 게이트 PASS 확인 후 commit + push

**잘 한 점**:
- "(코드에서 확인 안 됨)" 정직 표기 — §16 으로 별도 섹션 정착
- Pre-commit hook 으로 4 게이트 자동 PASS
- 사용자 메타 질문 ("내가 한 작업 리스트업") 에 git log 기반 정확히 답변

**개선 가능했던 점**:
- Explore 에이전트 prompt 에 "5K tokens 이내" 같은 출력 제약 명시 누락
- cowork 핸드오프 prompt (`0168689`) 와 Codex 레퍼런스 (`259003f`) 가 별개 파일 — 통합 가능했음
- SimonK-stack push 시도 (실패 인증 토큰 부재) — 사전에 GitHub MCP scope 명시 보고 fallback 결정 가능했음

**다음 세션에 즉시 적용할 룰**:
1. 백그라운드 에이전트 prompt 에 출력 형식 + 길이 제약 명시
2. `docs/` 안 기존 핸드오프 문서 먼저 확인 → append 우선
3. push 권한은 dry-run 1회만 확인 → 즉시 fallback
4. 본 LESSONS_LEARNED 의 §3 (놓치는 것 12개) 를 작업 전 점검

---

_2026-05-19 작성. 새 세션마다 이 파일 + `~/.claude/instincts/project-patterns.md` 의 LGIT-MPAP 섹션 우선 read._
_SimonK-Stack 동기화는 사용자 권한으로 수동 (Claude 환경엔 push token 없음)._
