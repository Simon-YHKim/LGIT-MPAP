---
type: project
tags: [lgit, vitals, streamlit, closed-network, lg-innotek, max-capa-tdr]
last_updated: 2026-05-08
related:
  - "[[entities/LG-Innotek]]"
  - "[[concepts/closed-network-deployment]]"
  - "[[concepts/backend-preservation-principle]]"
  - "[[concepts/zip-handoff]]"
  - "[[concepts/vitals-design-system]]"
---

# LGIT-MPAP (LG Innotek Vitals)

> 광학솔루션 사업부 · 생산혁신센터 **Max Capa TDR** 의 설비 생산성 분석 플랫폼.
> 이전: MPAP / Stethos. 캐치프레이즈: "공정의 호흡을 데이터로 듣다."

---

## 1. Overview

| 항목 | 값 |
|---|---|
| 회사 | LG Innotek 광학솔루션 사업부 |
| 팀 | 생산혁신센터 Max Capa TDR (이전: Max Capa 팀) |
| 환경 | **폐쇄망** 사내 PC + Streamlit + PostgreSQL (4 DB) + vLLM |
| 스택 | Python 3.11 / Streamlit 1.55.0 / SQLAlchemy 2.0 / psycopg2 |
| 프론트 | Streamlit native widgets + custom HTML/CSS injection |
| 레포 | `Simon-YHKim/LGIT-MPAP` |
| 페이지 | 9 + login (login / 0_Home / 1_CMP / 2_UPH / 3_MTBA / 4_Detail / 5_Alarm / 6_Chat / 8_Patch / 9_Admin) |
| 인수 방식 | **zip 파일** (이전 엔지니어 방식 유지) |

---

## 2. Timeline

### 2026-05-07 ~ 05-08 — STAGE 1+2 (visual integration)

이전 엔지니어로부터 zip 파일로 인수 받음 ([[concepts/zip-handoff]]).
[[entities/Claude-Code]] 세션에서 [[concepts/streamlit-vitals-redesign]] 진행.

#### Phase 1 — STAGE 1 (안전성 + 인프라, 8 commits)
- `19f47e3` — `8_Patch_Note.py` Stored XSS 4 사이트 `html.escape`
- `85b1572` → **revert `717732f`** — DB 패스워드 fallback 제거 시도 → 사용자 지적으로 복구
- `3d4ec6e` — preview HTML orphan modal + YouTube iframe 제거 + team-procs-modal 추가
- `3e5afb6` — 4 검증 스크립트 + AST baseline ([[concepts/backend-freeze-gate]])
- `f85fe71` → **revert `89b2d95`** — tracking.py connection pool 변경 시도 → 복구
- `b2d7ecd` — radius / dark-mode 토큰 reconciliation
- `0522f75` — `ui/vitals/components.py` 8 STAGE 2 primitives + emoji 제거
- `bf7a4a6` — preview HTML 21 broken interactions fix

#### Phase 2 — STAGE 2 (페이지 시각 정렬, 12 commits)
- 9 페이지 모두 `render_top_strip()` + 일부 `render_sub_head()` 적용
- `ui/login_ui/` 의 7 사이트 border-radius 제거
- 1_CMP_Dashboard 86.5 → 100.0 (off-token 26 종류 / 45회 교체)
- 4_MTBA_Detail_View 81.1 → 96.1 (off-token 8건)
- 8 페이지 일괄 ~100개 inline border-radius → 0
- `9983dc4` — login `[바로가기]` 의 `8_Board.py` → `8_Patch_Note.py` rename fix

#### Phase 3 — Pre-deploy + 마무리 (8 commits)
- `a082080` — `preflight.sh` 1-shot 점검 (10 카테고리)
- `aaaa7a1` — `STAGE2_RELEASE_NOTES.md`
- `fcad67b` — chat panel dead JS 제거 + CSS `:has()` 대체
- `c670b36` — `make_handoff_zip.sh` (이전 엔지니어 zip 방식 재현)
- `9acaf89` — `RELEASE_v1_DRAFT.md` (GitHub Release UI 복붙용)

#### Phase 4 — 대원칙 codify + 추가 개선 (5 commits)
- `9e7c122` — `CLAUDE.md` (repo root) — 회사방식 보존 + Vitals 디자인 룰
- `8c55700` — `requirements.txt` + `install_git_hooks.sh`
- `0c98b23` — 차트 hex 27회 토큰화 (평균 96.6 → 97.8)
- `f58778d` — render_csv_export + render_toast 통합
- `4756b57` + `955a2be` — 8_Patch_Note `sc-sec-head` 패턴

**총 38 commits, branch `claude/streamlit-vitals-Sry57`, base `streamlit-source`.**

### 2026-05-08+ — STAGE 3 (UI/UX 본격 개선)

다음 브랜치에서 진행 — 사용자 피드백 6 항목:
1. 16:9 모니터 비율 최적화 + 일관 여백
2. 대시보드 좌우 여백 = patch note, 상부 여백 최소화
3. 스크롤 최소화 (S3-B 기준)
4. 사이드바 user profile 항상 최하단 + 설정 버튼 기능
5. user profile 하단으로 "문의 메일" 옮기기
6. 텍스트 정리 (LG Innotek / Max Capa 팀 → Max Capa TDR / streamlit clone / 제작 — 랜딩만 유지)

추가:
- 로그인 좌우 분리 (4:3 → 16:9)
- 언어 선택 실 기능 구현
- Home 흰색 panel 제거

---

## 3. Decisions

### D1 — 백엔드 보존이 최우선 ([[concepts/backend-preservation-principle]])
> "데이터 호출 앞단 (DB·인증·SQL·session·연결방식·CDN fallback) 은 한 줄도 변경 금지. 변경 가능한 것은 표현 layer 만."

이유: 이전 엔지니어가 회사 운영 환경에 최적화된 의식적 결정.
검증: `verify_backend_freeze.py` (AST diff) — 매 commit pre-commit hook 으로 강제.

### D2 — 폐쇄망 compliance ([[concepts/closed-network-deployment]])
- 모든 폰트 woff2 자체 호스팅 (LG EI 5 weight)
- 비디오 mp4 자체 호스팅 (`bgi.mp4` 10MB)
- DB 패스워드 fallback `!Q2w3e4r5t` literal 유지 (코드 + secrets.toml 양쪽)
- 외부 CDN 검출 게이트 — Pretendard / Plex CDN 만 ALLOW (외부망 fallback 의도)

### D3 — Vitals 디자인 시스템 ([[concepts/vitals-design-system]])
- Rectangles only (border-radius:0, status dot 50% 만 예외)
- Wine identity #A50034 — 모든 페이지 상단 6px strip
- No emoji UI — 🌐 / ● / ▸ → SVG
- No multi-color — UI 색상 3개 이내
- Vitals 토큰 33개만

### D4 — 인수 방식 = zip 파일
이전 엔지니어 패턴 유지. `make_handoff_zip.sh` 가 `dist/LGIT-MPAP-vitals-<hash>-<date>.zip` 자동 생성. runtime 디렉토리 (access_log, logs, uploads) 제외.

---

## 4. Mistakes & Lessons

### M1 — DB 패스워드 fallback 제거 (commit `85b1572`)
- **실수**: "보안 best practice" 명목으로 7 파일에서 `os.getenv('X', '!Q2w3e4r5t')` 의 literal fallback 제거.
- **사용자 지적**: "하드코딩한거면 이유가 있지 않았을까?"
- **근본 원인**: 폐쇄망 환경 + 같은 비번이 secrets.toml + setting.ini 에도 평문으로 git 에 commit 되어 있는 사실 무시. fallback 제거의 보안 이득 = 0, 운영성 손실 = 큼.
- **해결**: `717732f` revert.
- **예방**: 회사방식 변경 전 "왜 그렇게 짰을까?" 질문 필수.

### M2 — tracking.py connection pool 변경 (commit `f85fe71`)
- **실수**: "PG max_connections 고갈" 가설로 `psycopg2.connect` → SQLAlchemy QueuePool 변경.
- **사용자 지적**: 회사 방식 보존 원칙 위반.
- **근본 원인**: 가설을 사실로 착각. 실 운영 데이터 없이 "더 좋은 패턴" 강제.
- **해결**: `89b2d95` revert.
- **예방**: API 호환 유지여도 **내부 동작 방식 변경은 회사 방식 변경**.

### M3 — `NOW()` → `CURRENT_TIMESTAMP` 변경 (`0522f75` 일부)
- **실수**: "SQLite 호환" 명목으로 SQL dialect 변경.
- **사용자 지적**: 회사는 PG 만 씀 — SQLite 호환 불필요.
- **해결**: `89b2d95` 에서 NOW() 로 복원.
- **예방**: 가정한 호환성이 실제 필요한지 먼저 확인.

### M4 — CDN @import 제거 (`3e5afb6` 일부)
- **실수**: "폐쇄망에선 어차피 dead load" 라고 제거.
- **사용자 지적**: 이전 엔지니어가 외부망 fallback 의도로 둔 것.
- **해결**: `89b2d95` 에서 복원 + `verify_no_external.py` ALLOW_SUBSTRINGS 에 명시.
- **예방**: dead-looking 코드도 의도가 있을 수 있음.

### M5 — 8_Board.py rename 누락 (`9983dc4` 에서 발견)
- **실수**: 페이지 rename 시 `login_ui/layout.py:497` 의 `st.switch_page("pages/8_Board.py")` 갱신 누락.
- **근본 원인**: rename 시 cross-reference 검색 누락.
- **예방**: 파일명 변경 시 `grep -r '<old-name>' ` 전수.

### M6 — 미사용 primitive 5개 (`0522f75` 시점)
- **실수**: 8 primitive 만들고 통합 자리는 안 봤음. `render_top_strip / render_sub_head` 만 사용, 나머지 6은 dead infrastructure.
- **부분 해결**: `f58778d` 에서 `render_csv_export` + `render_toast` 통합 (총 14 사용처).
- **여전히 미사용**: `render_modal_static` (st.dialog 가 이미 인터랙티브 모달 차지), `render_nav_card_grid` (auth 우회 위험), `render_sidebar_tree` (Streamlit native 사이드바), `render_filter_block` (페이지별 filter UI 깊이 박혀 있어 refactor 위험).

---

## 5. Open items

### 즉시 (STAGE 3 — 사용자 명시 6 항목)
1. **16:9 모니터 비율 최적화** — 좌우 상하 여백 최소화, 배경 화면 꽉 채우기, 일관 여백
2. **대시보드 여백** — 좌우 = patch note 패턴, 상부 최소화
3. **스크롤 최소화** — S3-B 기준 1 화면에 담기
4. **사이드바 user profile** — 항상 최하단 sticky + 설정 버튼 기능 구현
5. **사용자 프로필 하단 = 문의 메일** — 위치 이전
6. **텍스트 정리** — `LG Innotek` / `Max Capa 팀` / `streamlit clone` / `제작` 은 랜딩 페이지만, 그 외 페이지 제거. `Max Capa 팀` → `Max Capa TDR`
7. **로그인 화면 좌우 분리** — 16:9 비율 최적화
8. **언어 선택 실 기능** — 모든 페이지 (현재는 장식)
9. **Home 흰색 panel 제거** — 일관 디자인

### 중기 (deferred)
- B 확장: 다른 8 페이지에 `sc-sec-head` 패턴 적용 (8_Patch 만 적용됨)
- Modal 4-layer hide → `.is-open` only 일원화
- `fonts.py` base64 메모리 → static file
- 페이지별 단위 테스트 (pytest + streamlit-testing-library)
- requirements.txt 의 Streamlit 버전 피닝 — `requirements.txt` 추가됨
- 차트 SVG 의 plotly/matplotlib 색상 — Vitals 토큰 사용 중 (literal 이지만 토큰값)

### 외부 공개 시
- `secrets.toml` + `setting.ini` 의 평문 password 제거
- 코드 fallback `!Q2w3e4r5t` 7 사이트 제거
- DB password 회전
- `streamlit-app/.gitignore` 의 secrets.toml 주석 해제

---

## 6. Cross-refs

**Entities**:
- [[entities/LG-Innotek]]
- [[entities/Max-Capa-TDR]]
- [[entities/Claude-Code]]

**Concepts**:
- [[concepts/closed-network-deployment]]
- [[concepts/backend-preservation-principle]]
- [[concepts/streamlit-vitals-redesign]]
- [[concepts/vitals-design-system]]
- [[concepts/zip-handoff]]
- [[concepts/backend-freeze-gate]]

**Sources**:
- [[2026-05-07-handoff-prompt]] — 이전 엔지니어 → Claude Code 인수 인계

**Files (in repo)**:
- `LGIT-MPAP/CLAUDE.md` — 레포 진입 시 자동 로드
- `LGIT-MPAP/docs/STAGE2_RELEASE_NOTES.md` — 1장 변경 내역
- `LGIT-MPAP/docs/RELEASE_v1_DRAFT.md` — release UI 복붙 draft
- `LGIT-MPAP/streamlit-app/scripts/verify_backend_freeze.py` — AST diff gate
- `LGIT-MPAP/streamlit-app/scripts/preflight.sh` — deploy 전 점검
- `LGIT-MPAP/streamlit-app/scripts/make_handoff_zip.sh` — zip 인수 빌드
- `LGIT-MPAP/streamlit-app/scripts/install_git_hooks.sh` — pre-commit 자동 설치
