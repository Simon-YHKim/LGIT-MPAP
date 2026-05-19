# LESSONS_LEARNED.md

LG Innotek Vitals 프로젝트 — 사용자 / Claude(나) 의 협업 패턴, 오답노트, 다음 세션 최적화 가이드.

이 파일은 **다른 세션의 Claude 가 진입 즉시 읽고 토큰 낭비 없이 작업할 수 있도록** 작성됨. SimonK Stack 의 wiki 패턴 (raw / wiki / log) 을 단일 파일에 압축한 형태.

---

## 0. 프로젝트 컨텍스트 (TL;DR)

- 회사: **LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa 팀**
- 플랫폼: **Vitals** (이전명 MPAP / Stethos) — 설비 생산성 분석
- 캐치프레이즈: **"공정의 호흡을 데이터로 듣다"**
- 환경: **폐쇄망 사내 PC** · Streamlit + PostgreSQL + vLLM
- 레포: `Simon-YHKim/LGIT-MPAP`
- 작업 브랜치: `claude/streamlit-vitals-Sry57`
- 백업 브랜치: `streamlit-source` (절대 수정 금지)
- 마지막 commit (이 LESSONS 작성 시점): `57c4c7f`

---

## 1. 사용자 페르소나 (Simon)

### 1-1. 어떤 작업을 하는가
- **B2B 사내 분석 플랫폼 UI/UX 리드** — 디자인 시안 검토 → 피드백 → 반복 개선.
- **백엔드 보존이 절대 원칙**: 이미 작동하는 .py 함수 / SQL / session_state 를 손상시키지 않으면서 UI 만 교체.
- **시안 비교 좋아함** — "zip 이전 vs 이후", "S3-B vs 현재" 같은 1:1 매핑 요청 자주.

### 1-2. 의사소통 패턴
- **번호 매겨서 묶음 요구** — 한 메시지에 5~10 개 요구사항 (1./2./3./...).
- **시각 비교가 1차 언어** — 캡쳐 첨부 후 "1번 캡쳐 봐줘" 식. 텍스트 묘사보다 이미지 우선.
- **직설적·감정적 표현 사용** — "엉망이야", "한 척 해 한 거 맞아?", "빨리 진행시켜". → **이건 비난이 아니라 효율 신호**. 화 났다고 위축되지 말고 즉시 fix.
- **순서를 자주 바꿈** — MTBA Dashboard 의 §요약/§비교 순서를 두 번 swap 함. 첫 결정이 최종 아닐 수 있음을 전제로 작업.
- **요구사항이 fine-grained** — "Target 점선 가려져", "빨간선 위치가 다르네" 같은 px 단위 디테일.

### 1-3. 문제 인식 방법
- **결과물을 시각적으로 본 다음, 시각으로 비교** — 코드보다 화면 우선.
- **재발 시 화남** — 같은 문제가 두 번 나오면 "또 안 됐어?". → 첫 fix 가 진짜 해결인지 확인 필수.
- **한꺼번에 많이 요청하지만 일일이 확인** — 누락 시 즉시 캐치.

### 1-4. 개선 방향 (사용자가 원하는 작업 스타일)
- ✅ 짧고 명확한 답변
- ✅ 매 commit 후 commit-hash URL (`https://raw.githack.com/Simon-YHKim/LGIT-MPAP/<7char>/...`)
- ✅ "처리됨" 보다 "구체적으로 무엇이 어떻게 바뀜" 요약
- ❌ "이미 했다" 거짓 보고 → 실제 grep 으로 검증 후 답변
- ❌ 긴 설명 + 의문문 + 양해 구함 — 사용자는 결과만 원함

---

## 2. 작업 대원칙 (절대 깨지 말 것)

### 2-1. 백엔드 보존 (가장 신성한 원칙)
- `streamlit-app/**/*.py` — **함수 시그니처 / SQL 쿼리 / st.session_state 키 / import 문 0 byte 변경**.
- 새 함수/파일/CSS 클래스는 OK. 기존 것 rename / 삭제 / 인자 변경 X.
- `streamlit-source` 브랜치는 **수정 금지** (원본 zip).
- 검증: `git show streamlit-source:streamlit-app/login.py | diff - streamlit-app/login.py` 로 AST diff.

### 2-2. Vitals 아이덴티티
- 와인색 (`#A50034`) 가로/세로 선이 핵심 시각 요소.
  - `.vit-top-strip` / `::before` — 페이지 상단 6px 가로
  - `.cmp-sub-head__bar` — sub-head 좌측 4px 세로
  - `.sc-nav-card::before` — nav 카드 좌측 3px 세로
- **직사각형만** — `border-radius: 0 !important` 글로벌 override.
- 페이지 타이틀 = 검정 1px 하단선 (카드 X).
- 폰트: LG EI Headline (제목) / LG EI Text (본문) / IBM Plex Mono (숫자).
- 한국어 = Pretendard (fallback).

### 2-3. 폐쇄망 환경
- CDN 의존 최소화 (woff2 자체 호스팅).
- 외부 영상/이미지 인라인 base64 또는 self-hosted (e.g. `streamlit-app/img/bgi.mp4`).

---

## 3. 자주 한 실수 (오답노트) — Claude 자기성찰

| # | 실수 | 원인 | 개선 |
|---|---|---|---|
| 1 | **이미지 안 보고 추측 작업** | 시간 줄이려고 텍스트만으로 추정 | 사용자가 캡쳐 첨부 시 **즉시 Read 로 본 다음** 작업 시작. 단 1초도 추측 금지. |
| 2 | **이전 요청 정독 안 함** — MTBA S5-B 시안 콘텐츠 (막대차트/메모/패널 actions) 통째 누락 | 사용자 요청을 단순화해서 빠르게 끝내려 함 | 큰 시안 변경은 **참조 mockup 파일을 grep 으로 인벤토리 → 누락 항목 체크리스트** 후 작업 |
| 3 | **모달 leak fix 를 4번 시도** | 첫 시도부터 가장 robust 한 패턴 안 씀 | 모달은 **첫 시도부터 `.is-open` 클래스 패턴** — `:not(.is-open) { display:none !important }` |
| 4 | **CSS specificity 계산 안 함** — 자식 link active wine bar 가 dash 보다 specificity 낮아 가려짐 | spec 머릿속 계산 생략 | 새 selector 추가 전 항상 specificity 계산 + 기존 rule 와 비교 |
| 5 | **regex SVG element 잘못 위치** — Target line 이 첫 group 다음에 들어가 5 막대에 가려짐 | regex 매칭이 첫 hit 만 잡음 | SVG 안에 element 이동 시 **z-order 최종 위치 확인 (소스 순서가 곧 z-index)** |
| 6 | **"이미 했다" 거짓 보고** | git log 만 보고 답변 | 실제 grep / Read 로 **현재 파일 상태 검증 후** 답변. 사용자가 "또 안 됐어" 하면 **첫 반응으로 캐시 의심 X**, 코드 확인 먼저. |
| 7 | **fix 후 다른 페이지 regress 안 봄** | 단일 페이지에만 집중 | 큰 CSS 변경 후 모든 페이지 grep 으로 영향 받는 selector 확인 |
| 8 | **Edit tool 의 stale state 충돌** | 같은 파일을 Python script 후 Edit 시도 | Python 으로 대량 수정 후 Edit 사용 시 **재 Read 또는 Bash sed 로 전환** |
| 9 | **사용자 요구를 좁게 해석** — "팀별 공정 모달 실 구현" → 단순 close 만 함 | "구현"의 깊이를 underestimate | 사용자가 "실제로 구현" 강조 시 → DOM 갱신 + 다른 영역 동기화까지 모두 |
| 10 | **사이드바 자식 link 와인 bar 안 보임 디버깅 시간 낭비** | CSS 검사 안 하고 코드 수정 | 시각 문제 → **DevTools 사고방식**: selector / specificity / cascade 먼저 추적 |

---

## 4. 시행착오 + 결론

### 4-1. Modal leak (4 라운드 끝에 해결)
- **Round 1**: hidden attribute 만 — leak.
- **Round 2**: `[hidden] { display: none }` CSS — leak.
- **Round 3**: inline `style="display:none"` + `[hidden] !important` — leak.
- **Round 4 (해결)**: **`.is-open` 클래스 패턴** + script start force-close + 4중 안전장치.
- **교훈**: HTML `[hidden]` 만으로 부족. Streamlit DOM clone 환경에서는 글로벌 reset 이 leak. **첫 시도부터 클래스 기반 visibility 패턴** 채택.

### 4-2. SVG z-order (Target line 가려짐)
- **Round 1**: 위치 그대로 — 막대 위에 있음 추측, 실제는 grid 정의 직후라 막대가 위.
- **Round 2**: bar groups 다음으로 이동했다고 commit, 실제는 첫 group 닫는 `</g>` 직후 — Lens AA 막대만 통과, 나머지 5 공정 가려짐.
- **Round 3 (해결)**: `#mtba-bar-groups` 의 **닫는 `</g>` 바깥 + x-axis 전에** 정확히 배치.
- **교훈**: SVG 의 z-order = source order. regex 로 element 이동 시 **이동 후 정확한 위치를 grep 으로 확인**.

### 4-3. 사이드바 자식 link active wine bar
- 자식 link `::before` (dash) vs active wine bar `::before` 충돌. specificity 비교:
  - dash: `.sc-nav-group__list [data-testid="stSidebarNavLink"]::before` = (0,1,1,1)
  - active: `[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]::before` = (0,0,3,1)
- dash 의 (1 class) 가 active 의 (3 attr) 보다 specificity 높음 → dash 가 이김. wine bar 가려짐.
- **해결**: 자식 link active 전용 selector 명시:
  ```css
  .sc-nav-group__list [data-testid="stSidebarNavLink"][aria-current="page"]::before {
    left: 0; top: 6px; bottom: 6px; width: 4px;
    background: var(--primary);
  }
  ```
- **교훈**: `::before` 같은 pseudo 는 element 당 하나만 → 같은 element 에 두 selector 가 매칭되면 specificity 높은 게 이김.

### 4-4. MTBA Dashboard 콘텐츠 누락 (S5-B 충실 못 함)
- 1차 작업: 필터 + 4 KPI + 비교 표 + Heatmap — **S5-B 의 막대차트/메모/패널 actions 통째 빠짐**.
- 사용자 반응: "내가 참조하라 했던거랑 전혀 다르잖아? 엉망이야."
- **해결**: S5-B grep 으로 인벤토리 → 누락 항목 (chart-card, memo upload, panel actions, debug panel 등) 모두 복원 후 그리드만 heatmap 으로 교체.
- **교훈**: 큰 시안 참조 작업은 **반드시 원본을 line-by-line 읽고** 모든 요소 보존 → 사용자가 특정한 변경만 적용. **단순화 = 신뢰 손실**.

### 4-5. 페이지 visual rhythm 불일치
- 각 페이지의 sc-sec-head → 본문 사이에 다른 페이지는 모두 `.cmp-sub-head` 가 있는데 sec-chat 만 없음.
- 사용자: "빨간선 위치가 서로 다른 걸 모르겠냐?"
- **해결**: chat 에도 sub-head 추가 → 모든 페이지가 동일 패턴 (`::before` → `sc-sec-head` → `cmp-sub-head` → 본문).
- **교훈**: 페이지 일관성 = 동일한 visual layer 패턴. 한 페이지에만 layer 가 빠지면 정렬이 어긋나 보임.

---

## 5. 다음 세션에서 토큰 낭비 줄이는 방법

### 5-1. 진입 즉시 해야 할 것
1. `git log --oneline -20` — 최근 commit 컨텍스트 파악
2. `git branch --show-current` — 작업 브랜치 확인 (`claude/streamlit-vitals-Sry57`)
3. 이 LESSONS_LEARNED.md + HANDOFF.md (있으면) 읽기
4. **사용자 요청 정확히 인용** — 모호한 부분은 작업 시작 전 1번만 물어보기

### 5-2. 캡쳐 첨부 시 워크플로우
1. `Read` 로 모든 캡쳐 즉시 확인
2. 캡쳐에서 본 시각적 사실을 사용자 요구와 매핑 (예: "캡쳐 1 의 X 위치가 캡쳐 2 와 다름 → CSS spacing 통일")
3. 작업 시작

### 5-3. 큰 변경 워크플로우
1. **인벤토리** — 변경 대상 영역의 모든 element grep
2. **참조 mockup** 이 있으면 line-by-line 읽고 누락 체크리스트
3. **Python script** (큰 변경) or **Edit** (정밀 변경)
4. commit + `git push -u origin <branch>`
5. **commit-hash URL** 사용자에게 제공

### 5-4. CSS 작업 워크플로우
1. 새 selector 추가 전 **specificity 계산** + 기존 rule 와 비교
2. 글로벌 override 는 신중히 (`!important` 의 cascade 영향 추적)
3. SVG z-order = source order — element 이동 시 grep 으로 위치 확인
4. 모달 가시성 = **`.is-open` 클래스 패턴** 첫 시도부터

### 5-5. "이미 했다" 답변 금지
- 사용자가 "안 됐어" 하면 **첫 반응 = 코드 직접 grep 으로 검증**
- 캐시 의심은 두 번째. 코드가 맞는지 먼저.

---

## 6. 사용자 화날 때 대응

| 사용자 신호 | 해석 | 대응 |
|---|---|---|
| "엉망이야" | 큰 변경에서 누락 다수 | 즉시 원본 mockup 다시 grep + 누락 항목 모두 복원 |
| "한 척 해 한 거 맞아?" | 거짓 보고 의심 | 즉시 grep / Read 로 실제 파일 상태 보여줌 + 빠른 fix |
| "빨리 진행시켜" | 시간 끌지 말라 | 분석 짧게 + 즉시 commit + URL |
| "또 안 됐어" | 같은 문제 반복 | **캐시 X 코드 확인 먼저** + 더 robust 한 fix 패턴 |
| "캡쳐 봐봐" | 시각 확인 안 한 채 답변 | 캡쳐 첨부 즉시 Read |

---

## 7. 핵심 파일 인덱스

### 7-1. UI 시안 (이번 세션 결과)
- `docs/design/preview-streamlit-clone.html` (~3300 줄) — 9 페이지 + 4 모달 통합 preview
- `docs/design/streamlit-clone.css` (~4500 줄) — Vitals 디자인 시스템 + 모든 컴포넌트

### 7-2. 백엔드 (변경 금지)
- `streamlit-app/login.py` (1145 줄)
- `streamlit-app/pages/{0_Home,1_CMP_Dashboard,...,9_Admin_Analytics}.py`
- `streamlit-app/ui/` — UI 헬퍼 모듈

### 7-3. 원본 mockup (참조용)
- `docs/design/landing.html` — login 페이지 gold standard (영상 배경 + 글래스 카드 + 시스템 상태)
- `docs/design/home.html` — home 페이지 gold standard
- `docs/design/mockup-S{1..9}-B.html` — 각 페이지 Bold variant
- `docs/design/_shared.css` — Vitals 디자인 토큰

### 7-4. 자산
- `docs/design/assets/landing-bg.mp4` (11.6 MB)
- `docs/design/assets/landing-bg-poster.jpg`
- `docs/design/assets/lg-innotek-logo-en-{gray,white}.png`
- `docs/design/fonts/lg-ei-{text,headline}-{300,400,600,700}.woff2`
- `streamlit-app/img/bgi.mp4` (동일 영상, 백엔드용)

---

## 8. 매핑 — preview UI → streamlit-app 페이지

다음 세션에서 덮어쓰기 작업 시 매핑:

| Preview section | streamlit-app 파일 |
|---|---|
| `sec-login` | `login.py` |
| `sec-home-1/2/3` | `pages/0_Home.py` (3 모드 mode_selector) |
| `sec-cmp` | `pages/1_CMP_Dashboard.py` |
| `sec-uph` | `pages/2_UPH_Dashboard.py` |
| `sec-mtba` | `pages/3_MTBA_Dashboard.py` |
| `sec-detail` | `pages/4_MTBA_Detail_View.py` (이름은 'MTBA Heatmap' 으로 표시) |
| `sec-alarm` | `pages/5_Alarm_Action_List.py` |
| `sec-chat` | `pages/6_MaxCapa_Chat.py` |
| `sec-patch` | `pages/8_Patch_Note.py` |
| `sec-admin` | `pages/9_Admin_Analytics.py` |

---

## 9. 다음 세션 미션 (2 단계)

### STAGE 1 — SimonK 다각도 점검 (완벽해질 때까지)
- `/review`, `/codex review`, `/codex challenge`, `/qa-only`, `/design-review`, `/security-checklist`, `/cso`, `/plan-eng-review`, `/plan-design-review`, `/investigate`, `/benchmark`
- preview HTML/CSS 와 streamlit-app 양쪽 모두 점검 → 발견된 모든 이슈 fix → 재실행 → 모두 pass 까지

### STAGE 2 — preview UI → streamlit-app 덮어쓰기
- `streamlit-clone.css` 의 토큰을 `streamlit-app/ui/` CSS 에 병합
- 각 `pages/*.py` 의 `st.markdown` 호출에 preview HTML 의 구조 적용 — 단 함수 호출 / SQL 그대로
- JS 인터랙션 (모달, 탭, 라우팅, CSV) 은 `components.v1.html` iframe 또는 `streamlit_extras` 로 주입
- 검증:
  - [ ] `python -m py_compile pages/X.py` 모든 페이지 pass
  - [ ] `streamlit run app.py` 후 페이지 진입 시 시각 = preview 와 동일
  - [ ] 모든 백엔드 호출 (필터 → SQL → 표) 정상 작동
  - [ ] AST diff vs streamlit-source — 함수 시그니처 / SQL 0 변경

---

## 10. 한 줄 요약

> **사용자는 시각으로 의사소통하고 디테일에 민감하다. 백엔드 보존이 절대 원칙이며, 모든 fix 는 첫 시도부터 가장 robust 한 패턴 (`.is-open` 클래스 / specificity 계산 / source order z-index) 으로 가야 한다. "이미 했다" 보다 "방금 grep 으로 확인했다" 가 신뢰를 산다.**

---

*이 문서는 이번 세션 (commit `dc72dcd` → `57c4c7f`, 약 40+ commits) 의 self-audit. 다음 세션 진입 시 가장 먼저 읽을 것.*
