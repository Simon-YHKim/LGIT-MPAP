# LESSONS_LEARNED.md — Vitals 프로젝트 메타 분석

> 이 파일은 LG Innotek Vitals (LGIT-MPAP) 프로젝트의 협업 회고록입니다.
> 향후 새 세션에서 이 파일을 먼저 읽으면 같은 실수를 반복하지 않고
> 빠르게 사용자 컨텍스트와 작업 방식에 동기화할 수 있습니다.
>
> 위치: `/home/user/LGIT-MPAP/docs/LESSONS_LEARNED.md`
> 첫 작성: 2026-05-07
> 브랜치: `claude/streamlit-vitals-Sry57` @ commit `11294e7` 시점

---

## 1. 사용자 프로파일

### 누구인가
- **소속**: LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa 팀
- **역할**: 생산 데이터 분석 플랫폼 (Vitals, 이전명 MPAP) 책임 엔지니어
- **도메인 깊이**: CMP / UPH / MTBA / 알람 분석에 대한 깊은 현장 지식
  (광학모듈 라인의 FOL/MOL/EOL/Tele/Wide/Actuator 공정군 모두 익숙)
- **언어**: 한국어 (전문용어는 영어 혼용)
- **국제 컨텍스트**: 한국·베트남·폴란드·인도네시아·멕시코·중국 6개국 공장
- **목표**: 사내 엔지니어들이 데이터를 쉽게 찾고 분석하도록 하는 플랫폼

### 작업 환경
- **네트워크**: 폐쇄망 (외부 SaaS 사용 불가 — GA, MS Clarity, Supabase 등 ❌)
- **DB**: PostgreSQL (MTBA / MES_UPH / itas_uph_result 등 다중 DB)
- **앱**: Streamlit + sqlalchemy + bcrypt + win32com (Outlook)
- **AI**: 사내 vLLM (Qwen2.5-3B-Instruct) — intent_parser + planner
- **디바이스**: 자주 모바일/태블릿에서 작업 (PC 없을 때 많음)
- **검증 채널**: 모바일 브라우저로 raw.githack URL 열어 스크린샷 캡처

---

## 2. 사용자의 일하는 방식 / 경향

### A. 원칙을 먼저 못 박는 사람
- 작업 시작 전 **"대원칙"** 을 명확히 함
  - Vitals 의 대원칙: **"백엔드를 사용할때 문제없이 불러올수 있게 로직을 유지"**
  - 매번 강조함: "지켜지고 있어?", "재확인 꼭 하고", "항상 기억해"
- 폐쇠망, 보안, 회사 규약은 처음에 한 번에 정함 ("어짜피 폐쇠 환경")
- 원칙이 흔들리면 즉시 멈춤 — 반드시 다시 확인 후 진행

### B. 이터레이션 + 체크포인트 선호
- 한 번에 큰 작업을 시키되, 매 라운드마다 결과 확인
- "ㄱㄱ", "다음 라운드 가자", "전부 진행해줘" — 진행 신호
- "이거 맞아?", "정말 다한거 맞아?" — 검증 신호
- 라운드 사이에 검증 / 수정 / 다시 진행 패턴

### C. 시각 우선 학습자
- 코드 설명보다 **mockup HTML / 스크린샷** 선호
- 디자인 시안을 먼저 만들고 → 코드 적용 순서
- 모바일에서 스크린샷으로 검증 (긴 페이지 캡처)
- 정답지는 **landing.html / home.html / mockup-S*-B.html**

### D. 직설적이지만 한국식 정중
- 잘못됐을 때: "엥?", "이거 맞아?", "다시 해봐"
- 답답할 때: "후...", "마음이 아프네"
- 만족할 때: "좋아", "ㄱㄱ", "다음 라운드"
- 칭찬은 짧고 다음 작업으로 빨리 넘어감

### E. 컨텍스트 관리에 능숙
- 세션이 너무 길어지면 **핸드오프 받겠다고 함**
- "혹시 새 세션에서 열어야해?"
- 새 세션 prompt 를 직접 요청하기도 함
- 이전 세션 작업물 (zip 파일, 디자인 시안) 을 명확히 참조

---

## 3. 사용자가 주로 놓치는 것

### A. 어시스턴트의 컨텍스트 한계 인지 부족
- 어시스턴트가 모든 이전 세션 정보를 기억한다고 가정
- **개선 방향**: 어시스턴트가 매 세션 시작 시 핵심 컨텍스트를 명시적으로 요약하고 사용자에게 확인 받기

### B. 환경 차이 명시 안 함
- 사내 PC 가 있는지 / 모바일인지 / 태블릿인지 처음에 안 알려줌
- 브라우저 (Samsung Internet vs Chrome) 차이로 인한 렌더링 이슈 사후 발견
- **개선 방향**: 어시스턴트가 첫 검증 단계에서 "어떤 환경에서 보고 계세요?" 물어보기

### C. "이전에 만든 것" 의 정확한 위치 / 이름 헷갈림
- "홈 화면 버전 3개" 가 "3-mode selector" 인지 "mockup-S2-A/B/C 3 시안" 인지 모호
- 어시스턴트가 잘못 해석할 위험
- **개선 방향**: 어시스턴트가 모호한 표현 들으면 즉시 명확화 질문

---

## 4. 시행착오 + 결론 + 개선 방법

### 시행착오 #1 — "다 했다" 라고 했는데 실제로 깨져있던 상황

**상황**:
- 어시스턴트가 9개 페이지 재작성 완료 보고 + commit/push
- 사용자가 스크린샷 보내고 "이거 맞아? 다 망가졌는데?" 라고 함
- 모바일에서 사이드바가 viewport 마다 반복 (긴 스크린샷 캡처 시)

**원인**:
- 글로벌 CSS selector specificity 충돌 fix 했지만 **media query 는 fix 안 함**
- HTML 파서 검증 (`0 errors`) 만 보고 시각 검증 안 함
- 모바일/태블릿에서의 실제 렌더링 미고려

**결론**:
1. **HTML 검증 ≠ 시각 검증**. 파서가 통과해도 깨질 수 있음.
2. **CSS specificity 는 media query 까지 확인**해야 함.
3. **사용자가 모바일에서 본다는 점** 항상 염두에.

**개선 방법**:
- 매 commit 후 `python3 streamlit-app/scripts/measure_design_integration.py` 외에
  CSS specificity 검사 추가 필요
- 모바일 viewport (320px / 768px) 에서의 layout 시뮬레이션 코드 추가
- 사용자에게 "어느 디바이스에서 보고 계세요?" 물어보기

### 시행착오 #2 — "mockup" vs "current state" 혼동

**상황**:
- 어시스턴트가 preview-streamlit-clone.html 만들고 사용자에게 보여줌
- 사용자: "여기 페이지들 모두 zip 파일 올리기 이전 디자인만 있는데?"

**원인**:
- mockup-S*-B.html 들은 zip 업로드 **이전** 디자인 시안 (target)
- 그 시안을 zip 코드에 통합한 **결과 (current state)** 와 다름
- 어시스턴트가 mockup 파일들을 "current state" 로 잘못 보여줌

**결론**:
1. **타깃 (시안)** 과 **결과 (현재 상태)** 를 명확히 구분
2. 사용자는 후자를 보고싶어함 — 코드가 실제로 어떻게 보일지

**개선 방법**:
- 두 종류 파일을 분리: `mockup-*` (zip 이전 타깃) vs `preview-current` / `preview-streamlit-clone` (zip 이후 결과)
- 매 preview HTML 상단에 명시: "이건 [타깃 시안 | 통합 후 결과] 입니다"

### 시행착오 #3 — 로그인 페이지 사이드바 누락 인지 못 함

**상황**:
- 사용자: "좌측 네비게이션 바는 로그인 화면에선 안보여야 하는거 아냐?"
- 어시스턴트가 보였음

**원인**:
- 실제 `streamlit-app/ui/login_ui/styles.py` 가 사이드바 hide 함:
  ```css
  [data-testid="stSidebar"] { display: none !important; }
  ```
- preview HTML 은 모든 섹션이 한 페이지에 있어서 외부 sticky sidebar 가 보임
- 어시스턴트가 .py 파일을 정독하지 않고 일반적인 sidebar 표시 가정

**결론**:
1. **기존 코드를 정답지로 삼는다** — login 의 실제 동작이 정답
2. preview HTML 은 실제 동작을 모사해야 — 단순한 generic preview 가 아님

**개선 방법**:
- preview 만들기 전에 해당 .py 파일 + 그 import 모듈 정독
- 각 페이지의 실제 화면 동작 (hide/show, layout) 을 표 형태로 정리한 뒤 모사

### 시행착오 #4 — LG Innotek 로고 위치 누락

**상황**:
- 사용자: "LG Innotek. 마크는 어디간거야?"
- 로고는 docs/design/assets/ 에 있고, mockup 들엔 들어있는데 preview-streamlit-clone 일부 페이지에서 빠짐

**원인**:
- 9개 페이지 preview 작성 시 헤더 영역의 로고 누락
- 어시스턴트가 페이지 안 컨텐츠에 집중하다가 페이지 외 chrome (브랜드) 놓침

**결론**:
1. 브랜드 일관성은 **모든 페이지 chrome** 에 적용되어야 함
2. 자산 (assets/) 은 항상 활용 가능 — 누락하지 말 것

**개선 방법**:
- preview 작성 전 `docs/design/assets/` 자산 목록 확인
- 페이지 chrome (헤더 / 사이드바 / 푸터) checklist 만들기

### 시행착오 #5 — 긴 세션 + 누적 drift

**상황**:
- 세션이 30+ turns 넘어가면서 사용자 피드백 누적 실수 증가
- 사용자: "세션이 너무 길어져서 힘든거야? 핸드오프 줘봐"

**원인**:
- 컨텍스트 윈도우 압박 → 이전 결정 / 원칙 기억 흐려짐
- 새 작업 + 기존 검증 + 사용자 피드백 모두 한 컨텍스트에서 처리

**결론**:
1. **30 turns 가 임계점** — 이후 품질 하락 위험
2. 핸드오프는 빨리, 명확하게

**개선 방법**:
- 매 5-10 commit 후 자체 health check
- 사용자가 피드백 패턴 (예: "이거 맞아?" 가 반복) 보이면 즉시 handoff 제안
- 핸드오프 프롬프트 템플릿 항상 준비

---

## 5. 새 세션에서 즉시 활용할 체크리스트

### 세션 시작 시
- [ ] 이 LESSONS_LEARNED.md 읽기
- [ ] `git log --oneline streamlit-source..HEAD` 로 commit 히스토리 파악
- [ ] `docs/design/_shared.css` 의 Vitals 토큰 확인
- [ ] `streamlit-app/scripts/measure_design_integration.py` 실행 → 현재 점수
- [ ] 사용자 환경 (PC / 모바일) 확인

### 코드 변경 전
- [ ] 백엔드 대원칙: 함수 시그니처 / SQL / session_state 키 보존
- [ ] 해당 .py 파일 정독 + 의존 모듈 (ui/, utils.py, db.py) 확인
- [ ] 기존 mockup-S*-B.html 확인 (디자인 정답지)

### 코드 변경 후
- [ ] `python3 -c "import ast; ast.parse(open('CHANGED_FILE.py').read())"` 신택스
- [ ] AST diff: 함수 시그니처 streamlit-source 와 비교
- [ ] `measure_design_integration.py` 점수 회귀 없는지
- [ ] HTML 변경 시 파서 검증 + CSS brace 균형

### Preview HTML 변경 시
- [ ] login section: 외부 사이드바 hide 처리됨?
- [ ] 모든 페이지: LG Innotek 로고 위치 일관?
- [ ] CSS specificity: media query 포함 모두 한정 셀렉터?
- [ ] mockup-S*-B 와 비교: 시각 요소 (영상 / 글래스 / 그라데이션 / 폰트) 동일?

### Commit 전
- [ ] 백엔드 보존 verify (AST diff)
- [ ] 디자인 통합도 점수 회귀 X
- [ ] 한 commit = 한 논리 단위
- [ ] 커밋 메시지에 "왜" 설명

### Push 후
- [ ] raw.githack URL 사용자에게 제공
- [ ] 사용자 환경 (모바일) 에서 보이는지 확인 요청
- [ ] 5 turn 마다 진행 상황 요약

---

## 6. 절대 금지 사항

- ❌ "다 했다" 라고 했는데 실제 검증 안 한 상태
- ❌ 백엔드 함수 시그니처 / SQL 변경
- ❌ `streamlit-source` 브랜치 수정
- ❌ 기존 mockup 파일 덮어쓰기
- ❌ Inter 폰트 / pure black / 4색 이상 사용 (Vitals 디자인 원칙)
- ❌ login.py 의 사이드바 hide 로직 제거
- ❌ st.cache_resource 제거 (perf 회귀)
- ❌ 사용자가 "이게 맞아?" 라고 했는데 단순 "맞아요" 답변
- ❌ 한 세션에서 50+ commit (그 전에 handoff)

---

## 7. Vitals 디자인 시스템 핵심 (잊지 말것)

### 색상 (Vitals Palette)
```
--primary:      #A50034  (LG 와인 레드 — 유일한 액센트)
--primary-dark: #7E0027
--primary-tint: #F8E5EC
--page-bg:      #F7F8FA
--card-bg:      #FFFFFF
--soft:         #F1F3F5
--border:       #E5E7EB
--ink-body:     #1F2430
--ink-muted:    #6B7280
--ink-subtle:   #9CA3AF
--status-good:  #1F8B4C  (good-tint: #E6F4EA)
--status-warn:  #B57F1B  (warn-tint: #FAF1DD)
--status-bad:   #B23A48  (bad-tint:  #FDECEF)
```

### 다크 모드 토큰
```
--page-bg-dark: #0E1117
--card-bg-dark: #14171F or #161B22
--soft-dark:    #1B1F2A or #1A1F2A
--border-dark:  #2A3040 or #2A2F3A
--ink-body-dark:#E5E7EB or #E6E9EF
```

### 폰트
- Body: `'LG EI Text', 'Pretendard Variable', 'Malgun Gothic', sans-serif`
- Display: `'LG EI Headline', 'LG EI Text', sans-serif`
- Mono: `'IBM Plex Mono', ui-monospace, monospace`
- 임베드: base64 woff2 (`streamlit-app/ui/vitals/fonts.py`)

### 로고
- `docs/design/assets/lg-innotek-logo-en-white.png` (다크 배경)
- `docs/design/assets/lg-innotek-logo-en-gray.png` (라이트 배경)
- `docs/design/assets/lg-innotek-logo-ko-white.png`

### 캐치프레이즈
**"공정의 호흡을 데이터로 듣다"**

### 6 개국어
한국어 · English · Tiếng Việt · 中文 · Polski · Bahasa

---

## 8. 핵심 파일 위치 (Bookmarking)

### 백엔드
- 전 페이지 진입점: `streamlit-app/login.py`
- DB 엔진: `streamlit-app/db.py` (@st.cache_resource)
- 트래킹: `streamlit-app/tracking.py`
- 인증: `streamlit-app/auth_guard.py`
- MTBA 빌더: `streamlit-app/mtba_detail_view/builders.py`
- 댓글: `streamlit-app/mtba_detail_view/comments.py` (캐시 + 정규화)

### Vitals 디자인 시스템
- Theme: `streamlit-app/ui/vitals/theme.py`
- 폰트: `streamlit-app/ui/vitals/fonts.py`
- 사용자 선호: `streamlit-app/ui/vitals/preferences.py`
- Export: `streamlit-app/ui/vitals/__init__.py`

### 로그인 UI (사이드바 hide 등)
- `streamlit-app/ui/login_ui/styles.py`
- `streamlit-app/ui/login_ui/layout.py`

### Analytics (GA + Clarity 대체)
- 진입점: `streamlit-app/ui/analytics/__init__.py`
- JS: `streamlit-app/ui/analytics/tracker.js`
- 컴포넌트: `streamlit-app/ui/analytics/frontend/index.html`
- SQL: `streamlit-app/SQL/analytics_schema.sql`

### 디자인 시안 (zip 이전 — 정답지)
- `docs/design/landing.html`
- `docs/design/home.html`
- `docs/design/mockup-S1-B.html` (login)
- `docs/design/mockup-S2-A.html`, `S2-B.html`, `S2-C.html` (home 3 시안)
- `docs/design/mockup-S3-B.html` ~ `S9-B.html`
- `docs/design/_shared.css` (토큰 정의)
- `docs/design/fonts/` (LG EI woff2)
- `docs/design/assets/` (로고 PNG)

### Preview (zip 이후 — 현재 상태)
- `docs/design/preview-index.html` (허브)
- `docs/design/preview-current.html` (post-integration)
- `docs/design/preview-streamlit-clone.html` (Streamlit DOM 클론)
- `docs/design/streamlit-clone.css`

### 측정 / 검증 스크립트
- `streamlit-app/scripts/measure_design_integration.py`
- `streamlit-app/scripts/verify_dark_mode_tokens.py`

### 문서
- `streamlit-app/docs/INTEGRATION_REPORT.md`
- `streamlit-app/docs/PERF_AUDIT.md`
- `streamlit-app/docs/design_integration_score.json`
- `docs/LESSONS_LEARNED.md` ← 이 파일

### SQL
- `streamlit-app/SQL/perf_indexes.sql`
- `streamlit-app/SQL/analytics_schema.sql`

---

## 9. 미해결 이슈 (다음 세션에서 처리)

작성 시점: 2026-05-07 (commit `11294e7` 이후)

1. **`preview-streamlit-clone.html` 의 login section 사이드바 표시 문제**
   - 실제 login.py 는 사이드바 hide (login_ui/styles.py)
   - preview 는 외부 sticky sidebar 가 login 위로도 보임
   - Fix: login section visiting 시 sidebar 숨기는 JS scroll observer 또는 z-index 처리

2. **LG Innotek 로고 페이지별 누락**
   - 일부 페이지 (특히 dashboard 들) 에 로고 없음
   - 자산: `docs/design/assets/lg-innotek-logo-*.png` 활용
   - 사이드바 상단에도 LG 로고 표시 필요

3. **zip 이전 시안 수준에 못 미치는 페이지들**
   - mockup-S*-B 와 비교해서 정밀화 필요
   - 특히: 글래스 효과, 그라데이션, 타이포그래피 크기

---

## 10. 추천 작업 순서 (새 세션용)

1. **첫 5분**: 이 파일 + `streamlit-app/docs/INTEGRATION_REPORT.md` 읽기
2. **다음 5분**: `git log --oneline streamlit-source..HEAD` + `git diff HEAD~5..HEAD --stat`
3. **다음 5분**: `python3 streamlit-app/scripts/measure_design_integration.py` 실행
4. **첫 작업**: 사용자가 명시한 미해결 이슈 1개 처리 → 검증 → commit + push
5. **사용자 확인**: 매 commit 후 URL 제공 + 사용자 환경 확인
6. **반복**: 5 commit 단위로 LESSONS_LEARNED 에 새 교훈 추가

---

## 11. 어시스턴트 자가 점검 (매 응답마다)

- [ ] 백엔드 대원칙 위배 안 함?
- [ ] 사용자 가 모바일이면 모바일 viewport 고려?
- [ ] mockup-S*-B 와 비교 했나?
- [ ] "다 했다" 라고 하기 전에 시각 검증?
- [ ] 한국어 답변 (사용자가 한국어로 질문 시) ?
- [ ] 짧고 명확한가?
- [ ] 세션 turn 수 30+ 면 handoff 제안?

---

## 부록: 사용자 자주 쓰는 표현 사전

| 표현 | 의미 | 어시스턴트 반응 |
|---|---|---|
| "ㄱㄱ" | 계속 진행 | 다음 작업 진행 |
| "다음 라운드" | 새 작업 사이클 | 현재 commit + 새 작업 |
| "이거 맞아?" | 검증 요청 | 즉시 정직한 self-audit |
| "다시 해봐" | 실패 → 재시도 | 원인 분석 + 다른 접근 |
| "후..." | 답답함 표시 | 핵심 문제부터 다시 |
| "마음이 아프네" | 큰 실수 인지 | 사과 + 복구 plan |
| "핸드오프" | 새 세션 이동 | 종합 prompt 작성 |
| "ㅋㅋㅋ" | 만족 / 유머 | 짧은 ack 후 작업 계속 |
| "엥?" | 의외 / 잘못됨 | 즉시 확인 + 수정 |
| "대원칙" | 절대 규칙 | 다음 작업에서 반드시 |

---

_마지막 업데이트: 2026-05-07 (commit `11294e7` 이후) — 새 세션에서 이 파일을 발견하면 가장 먼저 읽어주세요._
