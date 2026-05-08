---
type: source
tags: [handoff, lgit-mpap, claude-code]
date: 2026-05-07
source_kind: chat-prompt
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
---

# 2026-05-07 — 이전 엔지니어 → Claude Code 인수 인계 프롬프트

## 출처
이전 [[entities/Claude-Code]] 세션에서 작성. 사용자 (Simon) 가 새 세션 시작 시 컨텍스트 전달용으로 붙여넣음.

## 요지

**프로젝트**: LG Innotek Vitals (이전 MPAP / Stethos)
**환경**: 폐쇄망 사내 PC + Streamlit + PostgreSQL + vLLM
**브랜치**: `claude/streamlit-vitals-Sry57` (작업), `streamlit-source` (백업)
**시작 시점 commit**: `8ee4ceb` (실제로는 `57c4c7f` 까지 있었음 — 핸드오프 작성 후 1 commit 추가)

## 진행 상태 (당시)

**STAGE 1 — preview HTML/CSS 시안 9 페이지 + 4 모달 완료**
- `docs/design/preview-streamlit-clone.html` (3412줄) + `streamlit-clone.css` (4357줄)
- 9 sec-* 섹션: login, home-1/2/3, cmp, uph, mtba, detail, alarm, chat, patch, admin
- 4 모달: cmp-proc-modal, alarm-detail-modal, team-procs-modal, settings-modal

## 핸드오프가 명시한 대원칙

> "이전 엔지니어가 정한 데이터 호출 앞단 (DB·인증·SQL·session·연결방식·CDN fallback) 은 한 줄도 변경 금지. 변경 가능한 것은 표현 layer 만 (HTML 구조 / CSS / 시각 정렬)."

→ [[concepts/backend-preservation-principle]] 으로 codify 됨.

## 핸드오프가 요청한 다음 작업

**STAGE 1**: SimonK 스택 다각도 점검 (review / codex / qa-only / design-review / security-checklist / cso / plan-eng-review / plan-design-review / investigate / benchmark)

**STAGE 2**: preview UI → streamlit-app 의 9 페이지에 덮어쓰기 (백엔드 0 byte 변경)
- sec-login → login.py
- sec-home-1/2/3 → 0_Home.py (3 모드)
- sec-cmp → 1_CMP_Dashboard.py
- ... (9 페이지 매핑 명시)

## 결과

본 핸드오프 기반으로 진행한 작업이 [[projects/lgit-mpap]] 의 **2026-05-07 ~ 05-08 STAGE 1+2** Timeline 으로 기록됨. 38 commits 누적.

## 핵심 사용자 지적

핸드오프 자체보다 **세션 도중 사용자 (Simon) 의 직접 지적**이 결정적:

1. **"하드코딩 fallback 이 뭐야? 이유가 있지 않았을까?"** → DB 패스워드 fallback 제거 revert
2. **"이전 엔지니어 방식 보존 하기 같은걸 대원칙으로 해서 작업"** → CLAUDE.md codify
3. **"기존에 내가 html 로 하던게 streamlit으로 이식이 완료 됐고, 파일을 덮어 씌우기만 하면 기존에 호출되던 데이터가 정상적으로 호출되어서 기능이 작동한다는 거야?"** → 솔직한 한계 인정 (덮어쓰기 + runtime 보존 분리)
4. **"Max Capa 팀'은 'Max Capa TDR'로 변경"** → 명칭 갱신 → STAGE 3 작업
