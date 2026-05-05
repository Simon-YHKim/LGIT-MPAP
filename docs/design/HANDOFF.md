# LG Innotek VITALS — 인수인계 문서 (HANDOFF)

> **대상**: 백엔드 엔지니어 + 시안을 Streamlit 또는 다른 프레임워크로 통합할 AI 에이전트
> **작성**: 2026-05-05
> **레포**: `Simon-YHKim/LGIT-MPAP`
> **상태**: 8 페이지 디자인 시안 완료 · 백엔드 wire-up 대기

---

## 1. 프로젝트 컨텍스트

| 항목 | 값 |
|---|---|
| 제품명 | **VITALS** (Equipment Productivity Analytics Platform) |
| 한 줄 피치 | LG Innotek 광학솔루션 사업부의 설비 생산성을 CMP · UPH · MTBA 세 축으로 통합 분석·조회하는 사내 엔지니어링 플랫폼 |
| 캐치프레이즈 | **공정의 호흡을 데이터로 듣다** |
| 제작 | 광학솔루션 사업부 · 생산혁신센터 · Max Capa 팀 |
| 디자인 톤 | **Calm Engineering** — Linear · Stripe · Toss 영향 / 도구형 톤 (장식 < 정보 밀도) |
| 사용자 | 광학 사업부 사내 엔지니어 (한국어 모국어, 사내 인트라넷, 데스크톱 1280–1880px) |
| 스택 (예정) | Streamlit (Python) · PostgreSQL · Plotly · st-aggrid |
| 스택 (현재 시안) | Pure HTML / CSS / Vanilla JS (프레임워크 무의존) |

---

## 2. 디자인 토큰

`docs/design/_app-shell.css` `:root` 에서 모두 노출. CSS 변수로 사용.

### 컬러
```css
--primary:        #A50034   /* LG corporate wine red */
--primary-dark:   #7E0027
--primary-tint:   #F8E5EC
--page-bg:        #F7F8FA
--card-bg:        #FFFFFF
--soft:           #F1F3F5
--border:         #E5E7EB
--border-strong:  #CBD0D6
--ink-body:       #1F2430   /* tinted neutral, never pure black */
--ink-muted:      #6B7280
--ink-subtle:     #9CA3AF
--status-good:    #1F8B4C
--status-warn:    #B57F1B
--status-bad:     #B23A48
```

**3색 정책**: 본문 무채 + 와인레드 강조 1점 + Status 3색만. 4색 이상 multi-color 차트 금지. pure black/gray 금지 (반드시 violet/blue tint).

### 폰트
```css
--font-body:    'LG EI Text', 'Pretendard Variable', Pretendard, 'Malgun Gothic', system-ui, sans-serif
--font-display: 'LG EI Headline', 'LG EI Text', Pretendard, sans-serif
--font-mono:    'IBM Plex Mono', ui-monospace, Menlo, monospace
```

자체 호스팅: `docs/design/fonts/` 9 woff2 파일 (LG EI Text 4 weight + LG EI Headline 5 weight). 라이선스: LG 그룹 코퍼레이트 폰트, 사내 사용 허가.

### 간격 / 레이아웃
```css
--topbar-h:           56px
--sidebar-w:          240px
--sidebar-w-collapsed: 56px
--chat-w-default:     360px
--chat-w-min:         280px
--chat-w-max:         720px
--chat-w-collapsed:   48px
--ease: cubic-bezier(0.2, 0.6, 0.3, 1)   /* bounce/elastic 금지 */
```

---

## 3. 공통 Shell — `_app-shell.css` + `_app-shell.js`

모든 인증 후 페이지 (home, cmp, uph, mtba×2, maxcapa-chat) 가 공유.

### Shell 레이아웃

```
┌─ topbar (56px) ─────────────────────────────────────────────────────┐
│ [☰] [LG logo] | VITALS · 생산혁신센터 ........ [lang ▾] [로그아웃] │
├─ shell ────────────────────────────────────────────────────────────┤
│ ┌─ sidebar ──┬─ main ─────────────────────────────┬─ chat-panel ─┐ │
│ │ 240px      │  콘텐츠 (페이지별)                  │ 360px        │ │
│ │ collapse   │                                    │ collapse +   │ │
│ │ to 56px    │                                    │ resize       │ │
│ └────────────┴────────────────────────────────────┴──────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 사이드바 nav 구조 (모든 페이지 동일)

```
Home
CMP 현황판
UPH 현황판
MTBA ▾                                ← 트리 부모
  ├ MTBA 현황판       (mtba-detail.html)
  └ 공정별 MTBA       (mtba-dashboard.html)
MaxCapa Chat
```

활성 항목만 페이지별로 다름. **순서·라벨 절대 변경 금지** — Intent Contract.

### 주요 인터랙션 (`_app-shell.js`)

| 동작 | hook | localStorage 키 |
|---|---|---|
| 사이드바 collapse 토글 | `#sidebar-toggle` 또는 `#topbar-menu` 클릭 | `app.sidebar.collapsed` |
| MTBA 트리 펼치기/접기 | `.nav__group__head` 클릭 | `app.nav-mtba.open` (active 자식 있으면 자동 펼침) |
| 챗봇 패널 collapse | `#chat-toggle` 클릭 | `app.chat.collapsed` |
| 챗봇 패널 리사이즈 | `#chat-handle` 좌측 edge drag | `app.chat.width` (clamped 280–720) |
| 언어 전환 | `.lang__item[data-lang]` 클릭 | `mpap.lang` |
| 로그아웃 | `[data-action="logout"]` 클릭 | session clear → `./landing.html` 로 redirect |

### i18n 구조

- `_app-shell.js` 가 `window.__I18N_BASE__` 로 chrome 공통 키 (nav, topbar, chat, foot) 정의
- 각 페이지가 `window.__I18N_PAGE__` 로 페이지 고유 키 정의
- 7 언어: `ko` · `en` · `vi` · `pl` · `id` · `es` · `zh`
- 미정의 키는 자동 ko fallback
- DOM 마킹: `data-i18n="key.path"` (텍스트), `data-i18n-ph="..."` (placeholder), `data-i18n-aria="..."` (aria-label)

---

## 4. 페이지 인벤토리

| # | 파일 | 라벨 (ko) | 의도 | 상태 |
|---|---|---|---|---|
| L | `landing.html` | 랜딩 | 영상 hero + 2-step 인증 (로그인 / 회원가입 + 인증코드) | 정식 v5 |
| H | `home.html` | 분석 도구 | 3 카테고리 (생산 / 설비 성능 / 설비 효율) × 16:9 카드 게이트웨이 | draft |
| 1 | `cmp-dashboard.html` | CMP 현황판 | 강조 KPI 4 + 모델별 박스 + 공정 요약 표(30일 추이) + 드릴다운 탭 | draft |
| 2 | `uph-dashboard.html` | UPH 현황판 | Wild 비대칭 + Bold 와인 accent · KPI strip + Hero trend + AI 사이드 + Best/Worst + 편차/추세 | draft |
| 3 | `mtba-dashboard.html` | 공정별 MTBA | 다중 패널 · 6구간 비교 차트 (모든 기간 숫자) · 메모/이미지 첨부 | draft |
| 4 | `mtba-detail.html` | MTBA 현황판 | 공장 매트릭스 (호기 × 12 공정) · MTBA 셀 클릭 → 알람 모달 (TOP5 비중 + 최근 7일) · 디버그 패널 | draft |
| 5 | `maxcapa-chat.html` | MaxCapa Chat | 풀 페이지 챗봇 thread (분석 trace · SQL · KPI · 차트 · 표 · 의견 · 후속 질문) | draft |
| I | `index.html` | (시안 인덱스) | 모든 페이지 썸네일 그리드 — 외부 시연용 | utility |

### 페이지 진입 흐름
```
landing.html  → [로그인]  → home.html
home.html     → 카드 클릭 → cmp / uph / mtba × 2 / maxcapa-chat
모든 페이지   → 좌 사이드바 → 모든 페이지로 라우팅
모든 페이지   → 우 상단 [로그아웃] → landing.html (mpap.session 삭제)
```

랜딩 → 홈 redirect 는 `window.AUTH_REDIRECT_URL` 로 백엔드에서 override 가능 (default: `./home.html`).

---

## 5. Intent Contract (각 페이지가 백엔드 wire-up 후 반드시 보존)

### S1 Login (landing.html)
- **자동 도메인 suffix**: 사내 ID + `@lginnotek.com` 자동 적용
- **2-step 회원가입**: ① 이메일 입력 → ② 6자리 인증코드 검증
- 인증코드 유효시간 5:00, 재발송 버튼
- **field-level inline error** (input 바로 아래 빨간 11px 텍스트, 공간 항상 reserve)
- **버튼 위치 고정** (.actions{margin-top:auto})
- 사이드바·헤더 노출 X

### S2 Home (home.html)
- 5 분석 도구 진입 게이트 (CMP · UPH · MTBA 현황판 · 공정별 MTBA · MaxCapa Chat — 5번째는 우측 패널로 노출 + 7번째 nav 항목)
- 각 도구 오픈 상태 표시 (`정식` / `가오픈` / `오픈예정`)
- 3 카테고리 grouping: 생산 / 설비 성능 / 설비 효율
- 카드 비율 16:9
- 푸터: "제작 · 생산혁신센터 Max Capa 팀"

### S3 CMP 현황판 (cmp-dashboard.html)
- 필터: 영역(multi) × 모델(multi: R50 / R53A / R53B) × 기간(date range)
- KPI 4: 전체 / R50 / R53A / R53B 달성률 (강조 KPI Bold)
- 모델별 박스 그리드 (공정별 달성률 bar)
- 공정 요약 sticky 표 + **30일 추이 컬럼** (sparkline)
- 행 클릭 → CMP / UPH / Efficiency 드릴다운 탭
- 메타: `'26.4월 4W 기준`

### S4 UPH 현황판 (uph-dashboard.html)
- 필터: 공장 × 공정 × 모델 × 날짜 + Trend 기간 segmented(30/90) + I-TAS 가능만 토글
- **Wild 비대칭 + Bold 와인 accent** 레이아웃
- 6 분석 컴포넌트:
  ① UPH 요약 (KPI strip · 평균 / 편차율 / I-TAS 일치율 / 샘플 n)
  ② Hero Trend chart (UPH + 편차율 + 목표선)
  ③ AI 분석 의견 사이드 패널 (모델 / 학습 윈도우 / 신뢰도)
  ④ Best vs Worst (자동선정 #1003 / #1116, 좌측 3px good/bad accent)
  ⑤ 주요 편차 동작 (±편차 ≥ 1.5σ)
  ⑥ 동작시간 증가 추세(악화) / 하락 추세(개선) 페어

### S5 공정별 MTBA (mtba-dashboard.html)
- 다중 패널 구조 (패널 1개 시작, +패널추가 / 이 패널 제거)
- 각 패널: 팀 + 모델 + 기간 필터
- **6구간 비교 차트** (선택 / 1주전 / 2주전 / 지난달 / 2달전 / 지난해) — **모든 기간 MTBA 숫자 명시 표기**
- 셀 체크박스 연동 공정별 요약표
- 메모 입력 + 이미지 업로드 (200MB, PNG/JPG/JPEG/BMP)
- 메모/이미지 저장 액션
- 우상단 banner: "MTBA 현황판으로 →"

### S6 MTBA 현황판 (mtba-detail.html)
- 패널 + 모델 (R50/R53A/R53B) + FOL In-line 토글
- **공정 × 설비 매트릭스** (12 공정 컬럼: `p_*` / `pk_*` 그룹화)
- **MTBA 수치 셀 클릭 → 모달 팝업** (그 공정·그 날 알람 상세):
  - 알람명 / 호기 / 모델 / 설비 세그먼트 / MTBA / 생산수량
  - 최근 7일 알람 이력 (시간순)
  - **주간 TOP 5 알람** (횟수 + 비중 막대 + 비중 %)
- 디버그 정보 패널 (verbatim 보존):
  - panel_id / grid_kind / streamlit_version / st_aggrid_version /
    response_keys / eventData / focusedCell / gridState /
    selected_rows / popup_key / click_marker / last_popup_marker_before /
    selected_row_summary / marker_rows / work_df_shape / work_df_columns_head
- 모달 닫기: ESC / overlay 클릭 / X 버튼

### S7 MaxCapa Chat (maxcapa-chat.html)
- 풀 페이지 챗봇 (좌 사이드바 + 메인 thread + 우 챗봇 패널은 collapsed default)
- **데이터소스 자동 분기**: 기본 MES UPH (`uph_input_runtime_daily_model`), "ITAS" 키워드 시 ITAS UPH (`itas_uph_result`)
- 사용자 메시지 → AI 응답 (각 응답이 expander 묶음):
  - **분석 단계** (4 단계 trace, 자동 압축, 디폴트 collapsed)
  - **실행 SQL** (read-only, 압축 표시)
  - **결과 KPI strip** (4 KPI)
  - **결과 차트** (monotone 와인 / Status 3색)
  - **결과 표**
  - **AI 분석 의견** (좌 3px wine accent)
  - **후속 질문 chips** (glyph 없는 pill, 클릭 시 composer 에 텍스트 채움)
- Composer (sticky bottom): 데이터소스 chip + textarea + 질문 분석 및 실행 버튼

---

## 6. 백엔드 Wire-up 가이드

### 인증 (landing.html)
세 form 의 `data-action` attribute 가 백엔드 endpoint 마커:
- `data-action="auth/login"` → POST { username, password } → 200 OK 시 `window.AUTH_REDIRECT_URL || './home.html'` 로 redirect
- `data-action="auth/send-code"` → POST { email } → 200 OK 시 step 2 활성화
- `data-action="auth/verify"` → POST { email, code } → 200 OK 시 redirect

응답 status 매핑:
- `200 ok:true` → 다음 단계 / redirect
- `401` → "아이디 또는 비밀번호가 올바르지 않습니다."
- `422` → "입력값을 다시 확인하세요."
- `410` → "만료된 인증코드입니다. 재발송하세요."
- 기타 → "서버에 연결할 수 없습니다."

에러 표시 슬롯:
- `#login-error[data-error-slot]`
- `#signup-error[data-error-slot]`
- `#verify-error[data-error-slot]`

미리보기 모드 = `res.mock === true` 응답 시 redirect 그대로 진행 (현재 구현).

### 챗봇 (maxcapa-chat.html)

질문 분석 라우팅 (frontend hint):
- `composer.value.includes('ITAS')` → ITAS UPH 분기
- 그 외 → MES UPH 기본

백엔드 endpoint (제안):
```
POST /api/chat/query
body: { question: string, session_id: string }
response: {
  trace:    [{ step: 1..4, label: string, code?: string }],
  source:   "mes_uph" | "itas_uph",
  sql:      string,
  result: {
    kpi:      [{ label: string, value: number, unit: string }],
    chart:    { type: "bar"|"line", series: [...] },
    table:    { columns: string[], rows: any[][] },
    opinion:  { html: string, refs?: { url: string, label: string }[] },
    followups: string[]
  }
}
```

### MTBA 알람 모달 (mtba-detail.html)
72개 매트릭스 셀에 `data-modal-target="#alarm-modal"`. 클릭 시 모달 open. 백엔드 wire-up:

1. 셀에 `data-process="p_연마"` `data-equipment="#1116"` `data-date="2026-04-29"` 추가 권장
2. 모달 open hook 에서 fetch:
   ```
   GET /api/mtba/alarms?process=p_연마&equipment=%231116&date=2026-04-29
   response: {
     alarm: { name, equipment, model, segment, mtba, qty, severity },
     recent: [{ time, name, severity }],   // 7d
     top5:   [{ rank, name, count, share_pct }],   // weekly
   }
   ```
3. 모달 본문 DOM 업데이트

### 다국어 (i18n)
- 모든 가시 한국어가 `data-i18n` 마킹됨
- 새 라벨 추가 시 `_app-shell.js` 의 `__I18N_BASE__` (chrome) 또는 페이지 `__I18N_PAGE__` 에 키 추가
- `applyLang()` 호출은 lang switcher 가 자동 처리

---

## 7. AI 에이전트 활용 가이드

이 시안을 다른 프레임워크 (Streamlit / Next.js / Django) 로 통합할 때:

### 권장 마이그레이션 순서
1. **Shell 컴포넌트** 우선: topbar / sidebar / chat panel — 모든 페이지 공통이므로 한 번 만들면 끝
2. **landing**: 인증 폼 (가장 단순한 wire-up)
3. **home**: 정적 카드 게이트웨이
4. **cmp-dashboard**: 표 + KPI (가장 안정된 패턴)
5. **uph / mtba × 2**: 차트가 많아 데이터 binding 작업 큼
6. **maxcapa-chat**: 챗봇 backend (LLM + SQL routing) 가장 복잡

### CSS 토큰 보존
`_app-shell.css` 의 `:root` 변수와 `_app-shell.js` 의 i18n 키는 **그대로 이식** 권장. 색상 / 폰트 / 간격 / 트리 / 모달 모든 디자인 결정사항이 압축돼있음.

### Verbatim 보존 항목 (변경 금지)
- 사이드바 7 항목 순서·라벨 (트리 자식 포함)
- 페이지 라벨 (CMP 현황판 / UPH 현황판 / MTBA 현황판 / 공정별 MTBA / MaxCapa Chat)
- 캐치프레이즈 ("공정의 호흡을 데이터로 듣다")
- 푸터 ("제작 · 생산혁신센터 Max Capa 팀")
- MTBA 매트릭스 12 공정 그룹 (`p_*` / `pk_*`)
- 디버그 패널 키 이름 (panel_id, grid_kind, ...)
- 알람 TOP5 — 횟수 + 비중 둘 다 표시
- I-TAS / MES 데이터소스 자동 분기 안내문구

### Anti-rules (절대 위반 금지)
- pure black / pure gray (반드시 violet/blue tint)
- Inter 폰트 (LG EI Text + Pretendard 만)
- 4색 이상 multi-color 차트 (monotone 와인 또는 Status 3색)
- 22px round (8–12px 만)
- bounce / elastic easing (`cubic-bezier(0.2,0.6,0.3,1)` 만)
- 큰 hero gradient
- 이모지 아이콘 (Lucide / Phosphor / 자체 SVG 만)
- 사각 ChatGPT-style 아바타 (텍스트 라벨 + hairline)
- 노란 mark 하이라이트
- 가짜 trace_id (운영형 ID 또는 제거)

---

## 8. Approved Decisions Log (사용자 승인 기록)

> 이 섹션은 사용자가 명시적으로 승인한 디자인/구조 결정을 누적 기록. 향후 변경 시 참조.

| 일자 | 결정 | 커밋 |
|---|---|---|
| 2026-04-29 | 카드 16:9 비율 + 3 카테고리 가로 1행 + 단일 viewport | `99fa41f` |
| 2026-04-30 | 좌 사이드바 복귀 + 상단 LG/VITALS + 우 챗봇 (모든 페이지) | `bebb7d3` |
| 2026-04-30 | 사이드바·챗봇 collapse/expand 사용자 제어 + 페이지 라우팅 | `bebb7d3` |
| 2026-05-05 | UPH = Wild 비대칭 + Bold 와인 accent (STEP 카드 폐지) | `1e54f7b` |
| 2026-05-05 | 자체 호스팅 hero 영상 (123MB → 12MB H264 720p) | `e21f309` |
| 2026-05-05 | MTBA 의미 swap + 사이드바 트리 (MTBA 현황판 / 공정별 MTBA) | `ba0812e` |
| 2026-05-05 | MTBA 매트릭스 셀 클릭 → 알람 모달 (TOP5 비중) | `ba0812e` |
| 2026-05-05 | 로그인 에러 = field-level inline + 버튼 위치 고정 (visibility:hidden + min-height) | `3ed8900` |

---

## 9. 다음 단계

1. **Streamlit 통합 패치 작성** — `st.markdown('<style>...</style>')` 로 `_app-shell.css` 주입 + 각 페이지를 Streamlit 컴포넌트로 변환
2. **인증 백엔드 wire-up** — `data-action` endpoint 3개 구현
3. **챗봇 LLM + SQL 라우팅** — POST `/api/chat/query` 구현
4. **MTBA 알람 API** — GET `/api/mtba/alarms` 구현
5. **i18n 사전 완성** — vi/pl/id/es/zh 5개 언어 부분 채워진 키 보강
6. **사용성 테스트** — 광학 사업부 엔지니어 5명 시연 + 피드백

---

## 10. 핵심 파일 목록

```
docs/design/
├── _app-shell.css              # 공통 chrome (모든 페이지 link)
├── _app-shell.js               # 공통 동작 + i18n base
├── landing.html                # 랜딩 (인증)
├── home.html                   # 분석 도구 게이트웨이
├── cmp-dashboard.html          # CMP 현황판
├── uph-dashboard.html          # UPH 현황판
├── mtba-dashboard.html         # 공정별 MTBA
├── mtba-detail.html            # MTBA 현황판 (매트릭스 + 알람 모달)
├── maxcapa-chat.html           # MaxCapa Chat
├── index.html                  # 시안 썸네일 인덱스 (외부 시연용)
├── HANDOFF.md                  # 이 문서
├── DESIGN.md                   # Calm Engineering 톤·토큰 사양 (initial)
├── README.md                   # 디자인 폴더 가이드 + Intent Contract
├── assets/
│   ├── lg-innotek-logo-en-{white,gray}.png
│   ├── landing-bg.mp4          # 자체 호스팅 hero 영상 (12MB)
│   └── landing-bg-poster.jpg   # 90KB poster (5s 프레임)
├── fonts/                      # LG EI Text/Headline 9 woff2
└── originals/                  # 8 페이지 원본 한국어 라벨 verbatim
```

루트:
```
DESIGN.md          # 디자인 토큰 (Calm Engineering)
README.md          # 프로젝트 README + AI 에이전트용 핸드오프 프롬프트
```

---

## 11. 미리보기 링크 (raw.githack)

main 브랜치 머지 후:
```
https://raw.githack.com/Simon-YHKim/LGIT-MPAP/main/docs/design/landing.html
https://raw.githack.com/Simon-YHKim/LGIT-MPAP/main/docs/design/index.html
```

문의: 광학솔루션 사업부 · 생산혁신센터 · Max Capa 팀
