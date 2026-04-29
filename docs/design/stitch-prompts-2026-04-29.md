# Stitch / Claude Design Prompts — 2026-04-29

> **Source**: `DESIGN.md` (Calm Engineering 방향)
> **Target**: Claude (claude.ai) 아티팩트 또는 Google Stitch
> **Output type**: 단일 HTML 파일 (inline CSS, Pretendard CDN)
> **사용법**: 한 번에 **하나의 프롬프트만** 붙여넣기. 8 화면 × A/B/C 3 변형 = 24 프롬프트.
>
> **A (Safe)** = Linear/Stripe 클론에 가장 가까움
> **B (Bold)** = Calm 톤 유지 + LG 와인레드 strip 1줄로 정체성 살림
> **C (Wild)** = 밀도 극대화 + 모든 숫자 IBM Plex Mono + 표 셀 안 미니 sparkline

공통 컨텍스트는 모든 프롬프트에 포함되어 있어 단일 프롬프트만으로 시안이 나옵니다.

---

## 공통 컨텍스트 (모든 프롬프트 머리)

```
Product: LG Innotek 설비 생산성 분석 플랫폼 (VITALS)
Pitch: 광학 사업부 설비 생산성을 CMP·UPH·MTBA 세 축으로 통합 분석하는 사내 엔지니어링 대시보드.
Audience: LG Innotek 광학 사업부 사내 엔지니어 (한국어, 데스크톱 1280-1880px, 매일 사용).
Tone: engineering, legible, dense, calm, tool-like — 도구 같은 인상.

Color palette (3색 정책):
- Primary Wine Red: #A50034 (악센트 1점만 — 활성 탭 밑줄 / Primary CTA / KPI delta / sticky 마커)
- Primary Dark: #7E0027 (hover/focus)
- Primary Tint: #F8E5EC (active row bg)
- Page bg: #F7F8FA   Card bg: #FFFFFF   Soft: #F1F3F5
- Border: #E5E7EB   Border Strong: #CBD0D6
- Ink Body: #1F2430   Ink Muted: #6B7280   Ink Subtle: #9CA3AF
- Status: Good #1F8B4C / Warn #B57F1B / Bad #B23A48

Typography:
- Pretendard Variable (CDN: https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css), weights 400/600/700
- IBM Plex Mono for KPI numbers and table number cells
- letter-spacing -0.01em on headings, word-break: keep-all on Korean

Layout:
- Desktop only, max-width 1880px, sidebar 240px
- Card radius 8px, padding 16px (small 12px), table row 32px (thead 36px), KPI card 88px
- Page bg #F7F8FA, no full-page gradient

Reference products to emulate: Linear, Stripe Dashboard, Toss
Avoid: 어드민 부트스트랩 룩, 4-5색 multi-color 차트, 큰 hero gradient, 22px 라운드 카드, 이모지 아이콘, 버건디 그라디언트 헤더

Constraints:
- WCAG AA, 한국어 1순위 + 영문 라벨 병기
- 라인 아이콘만 (Lucide/Phosphor 스타일 inline SVG), no emoji, no stock photo
- 폰트 weight 3개만 (400/600/700)
- bounce/elastic easing 금지 — cubic-bezier(0.2, 0.6, 0.3, 1)
- 단일 self-contained HTML, inline <style>, Pretendard CDN만 외부

Output: 1개 화면의 완성된 HTML 파일 (반응형 X, 1440px 기준).
```

---

## S1 — Login

### 🅐 S1·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 로그인 페이지

Variant strategy — Safe (Linear/Stripe 룩에 가장 가까움):
페이지 전체가 거의 무채색. 와인레드는 Primary CTA 버튼 1개에만 사용. 좌측 일러스트·비주얼 영역 없이 카드 1개만 중앙 정렬.

Key elements:
- 화면 정중앙에 폭 420px 카드 (radius 8px, border 1px #E5E7EB, shadow 없음 또는 매우 옅게)
- 카드 상단: LG Innotek 워드마크 (텍스트 "LG Innotek" 700 weight 14px, color #1F2430), 그 아래 11px uppercase eyebrow "PRODUCTIVITY ANALYTICS"
- 28px H1 "로그인" (한국어), 13px Ink Muted sub "사내 계정으로 로그인하세요"
- 탭: [로그인] [회원가입] — 활성 탭은 와인레드 2px 하단 밑줄
- 인풋 2개: "아이디" (placeholder "ex) maxcapa", suffix 라벨 `@lginnotek.com`을 인풋 우측에 회색 칩처럼) / "비밀번호"
- 회원가입 탭은 placeholder 상태로만 표시 (회사 이메일 입력 + "인증코드 발송" 버튼)
- Primary CTA "로그인" — 풀폭, 와인레드 #A50034 background, 흰 글자, radius 8px, height 44px
- 하단 13px Ink Muted: "문의: 광학 Max Capa TDR"
- 페이지 배경: #F7F8FA 단색

Sidebar/header: 노출 안 함 (auth 화면).
```

### 🅑 S1·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 로그인 페이지

Variant strategy — Bold (Calm 톤 유지 + LG 정체성 한 점):
Variant A 와 동일 구조. 단, 페이지 최상단에 8px 높이 와인레드 strip 1줄 추가 (그라디언트 X, 단색 #A50034). 카드 좌측에 좁은(폭 4px, 카드 높이 60%) 와인레드 vertical bar 추가.

Key elements:
- 페이지 최상단 8px 와인레드 strip (full width)
- 화면 정중앙 카드 폭 440px, radius 8px, 좌측 4px 와인레드 vertical bar
- 카드 상단 LG Innotek 워드마크 + 11px uppercase eyebrow "PRODUCTIVITY ANALYTICS"
- 나머지 (탭, 인풋, CTA) Variant A와 동일
- CTA 텍스트는 "로그인 →" (오른쪽 화살표 라인 아이콘)
- 카드 아래 작은 link "비밀번호 찾기" (13px Ink Muted, 와인레드 hover)

Bold 변형은 정체성 표시만 — 그래도 톤은 calm 유지. 그라디언트·큰 비주얼 영역 절대 추가하지 말 것.
```

### 🅒 S1·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 로그인 페이지

Variant strategy — Wild (밀도 + 정보형 변형):
Variant A 카드 옆에 시스템 상태 영역을 추가해 "엔지니어에게 친숙한 콘솔" 느낌. 화면 좌측은 폼 카드, 우측은 시스템 정보 패널 2열 배치. 와인레드는 활성 탭과 CTA에만.

Key elements:
- 좌측 (폭 460px) 로그인 카드 (Variant A와 동일 구조)
- 우측 (폭 360px) 시스템 패널 — radius 8px, border 1px, padding 16px, 다음 4 항목 표시:
  - "VITALS v0.4.2" (Plex Mono 13px, label "BUILD" uppercase 11px)
  - "API · OK" with 6px 그린 dot (#1F8B4C)
  - "DB · OK" with 6px 그린 dot
  - "마지막 데이터 갱신 · 2026-04-28 23:50" (Plex Mono 12px)
- 우측 패널 하단: 작은 회색 모노 텍스트 4줄 changelog ("· UPH dashboard v4 → 2026-04-22" 같은 식)
- 두 카드 사이 간격 24px, 함께 viewport 중앙 정렬
- 페이지 배경 #F7F8FA, 모든 라운드 8px

Wild 변형이지만 calm 톤 유지 — 다크모드 X, 강한 색 X. 정보가 늘어났을 뿐.
```

---

## S2 — Home (분석 항목 선택)

### 🅐 S2·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 홈 — 분석 도구 선택 페이지

Variant strategy — Safe:
Linear의 "프로젝트 카드 그리드" 톤. 좌측 240px 사이드바 + 콘텐츠. 사이드바는 흰 배경, 활성 메뉴만 와인레드 좌측 2px 마커.

App shell:
- 좌측 사이드바 240px, bg #FFFFFF, right border 1px #E5E7EB
  - 상단 LG Innotek 워드마크 (16px 700, 28px 높이 자리), 그 아래 11px uppercase "VITALS"
  - 메뉴: Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail / MaxCapa Chat / Logout (각 36px 높이, 14px 600, 좌측 16px padding)
  - 활성 항목 (Home): 좌측 2px 와인레드 마커 + 텍스트 색 #1F2430 (와인색 배경 X)
  - 비활성 항목: Ink Muted, hover 시 Soft bg

Page header:
- 11px uppercase eyebrow "PLATFORM" (Ink Subtle, letter-spacing 0.08em)
- 28px H1 "분석 도구"
- 13px Ink Muted "분석 항목을 선택하세요"

5개 분석 도구 카드 그리드 (3 col × 2 row, 마지막 빈 칸):
각 카드 padding 16px, radius 8px, border 1px, hover 시 border #CBD0D6:
1. CMP Dashboard — 라인 아이콘(grid 4칸) + 14px 700 타이틀 + 13px Ink Muted "공정별 CMP 달성률 추이" + 우상단 status badge "정식" (Good color)
2. UPH Dashboard — 라인 아이콘(trending up) + "UPH / 동작시간 분석" + "가오픈" (Warn color)
3. MTBA Dashboard — 라인 아이콘(activity) + "공정별 MTBA 통계" + "가오픈" (Warn)
4. MTBA Detail View — 라인 아이콘(layers) + "패널 기반 드릴다운 분석" + "가오픈" (Warn)
5. MaxCapa Chat — 라인 아이콘(message-square) + "대화형 생산지표 조회" + "오픈예정" (Subtle)

Status badge: padding 2px 8px, radius 4px, 11px 600 uppercase, 색은 Status 컬러 + 매우 옅은 같은 계열 bg.

Footer: 페이지 하단 13px Ink Muted "제작 · 광학 Max Capa TDR".
```

### 🅑 S2·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 홈 — 분석 도구 선택 페이지

Variant strategy — Bold (와인레드 strip + 카드 좌측 마커):
Variant A 구조 그대로. 다만:
- 페이지 콘텐츠 영역 최상단에 8px 와인레드 단색 strip 1줄
- 5개 카드 각각 좌측 3px 와인레드 vertical bar (카드 자체 hover 시 진해짐)
- 사이드바 활성 마커 4px (Variant A는 2px)
- 카드 타이틀을 16px 700으로 한 단계 키우고, 카드 padding 20px

남은 룰은 Variant A와 동일. 그라디언트·큰 비주얼·와인 카드 배경 X.
```

### 🅒 S2·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: 홈 — 분석 도구 선택 페이지

Variant strategy — Wild (정보 밀도 ↑, 카드에 미니 메타정보 추가):
카드 안에 추가 메타 정보 행을 넣어 엔지니어가 "어떤 도구가 활발한지"를 한눈에 본다.

각 카드 (Variant A 기준):
- 라인 아이콘 + 타이틀 + 1줄 설명 (동일)
- 그 아래 메타 행 (12px Ink Muted, IBM Plex Mono): 
  · "v4 · 2026-04-28" (마지막 갱신)
  · "12 panels" 또는 "30d trend" 같은 도구별 한 단어 메타
- 카드 우하단 작은 sparkline (폭 80px × 높이 16px, 와인레드 1px line, fill 없음) — 최근 30일 사용량 흐름. 
  단 "오픈예정" 카드는 sparkline 자리에 "—"

Card hover 시 sparkline이 약간 진해짐 (color 변경 없음, opacity 0.7 → 1).

App shell + 페이지 헤더는 Variant A와 동일. 다크모드 X, 강한 색 X. 밀도만 ↑.
```

---

## S3 — CMP Dashboard (대표 대시보드)

### 🅐 S3·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: CMP 달성률 Dashboard

Variant strategy — Safe (Stripe Dashboard 톤):
좌측 240px 사이드바 (S2 Variant A와 동일 구조, 활성은 "CMP Dashboard"). 콘텐츠는 4개 섹션 수직 스택.

Page header:
- 11px uppercase eyebrow "PRODUCTIVITY · CMP"
- 28px H1 "CMP 달성률 Dashboard"
- 13px Ink Muted "'26.4월 4W 기준 / 영역·모델·기간 필터로 조회"
- 우측 toolbar: [↻ 새로고침] [↓ Export] (라인 아이콘 + 12px 600 텍스트, 흰 카드 버튼)

Filter bar (1줄, padding 12px 16px, border 1px, radius 8px):
- 영역 (multi-select chips, 기본 선택: Gumi Campus 1/3/4 Area)
- 모델 (multi-select chips: R50, R53A, R53B)
- 기간 (date range, "2026-01-28 ~ 2026-04-28")
- 우측 끝 [Reset] (보더만) [Apply] (Primary 와인레드)

KPI row — 4개 카드 (각 폭 1fr, 88px 높이):
1. "전체 달성률" / 32px Plex Mono "94.2%" / +1.8% delta (Good color)
2. "R50 달성률" / "92.7%" / -0.4% (Bad)
3. "R53A 달성률" / "95.1%" / +2.1% (Good)
4. "R53B 달성률" / "94.8%" / +1.5% (Good)
각 카드: 11px uppercase 라벨 / 32px 숫자 / 작은 12px delta + 라인 화살표 아이콘.
KPI 카드 hover 효과 없음 (정적). border 1px, padding 16px.

Section heading 1: 좌측 4px 와인레드 vertical bar + 18px 700 "모델별 공정 달성률"
- 3 column 그리드, 각 column: 모델명 헤더 + 그 아래 공정 박스 12개 (3×4 grid)
- 공정 박스: 56px square, radius 6px, 안에 12px 공정명 줄임 + 14px Plex Mono 달성률
  - 95% 이상: bg #F1F3F5, text #1F8B4C
  - 90-95%: bg #F1F3F5, text #1F2430
  - <90%: bg #FBEBEC (옅은 Bad tint), text #B23A48

Section heading 2: "공정 요약 표"
- Sticky thead (bg #F1F3F5, 36px 높이, 14px 700)
- 컬럼: 모델 / 공장 / 공정명 / 기간 / CMP / UPH / Eff. / Δ
- 행 32px, 숫자 셀은 Plex Mono 13px 우측정렬, 텍스트 좌측정렬
- 행 hover bg #F7F8FA, active row 좌측 2px 와인레드 마커
- 표 컨테이너 max-height 480px, vertical scroll, sticky 좌측 1~2 컬럼 (모델, 공장)

Empty state: "선택된 조건에 데이터가 없습니다" (차분한 한국어, 느낌표 X).

샘플 데이터 8행 정도 채울 것 (예: R50 / Gumi Campus 1 / Lens AA / 2026-04-22 ~ 28 / 96.4% / 1247 / 94.2% / +1.1).
```

### 🅑 S3·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: CMP 달성률 Dashboard

Variant strategy — Bold:
Variant A 구조 그대로. 다음만 차이:
- 콘텐츠 영역 최상단 8px 와인레드 단색 strip
- KPI 카드 4개 좌측 3px 와인레드 vertical bar
- Section heading 가로선이 18px 700 + 우측에 13px Ink Muted "마지막 갱신 2026-04-28 23:50" 작게 표시
- Filter bar Apply 버튼이 와인레드 풀, Reset은 보더만 (Variant A와 동일)
- 표 thead 좌측 1px 와인레드 hairline

남은 룰은 Variant A와 동일. 카드 배경에 와인 X, 그라디언트 X.
```

### 🅒 S3·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: CMP 달성률 Dashboard

Variant strategy — Wild (밀도 극대화 + 표 셀에 미니 sparkline):
Variant A의 "모델별 박스 그리드" 섹션을 제거하고, 그 자리에 더 큰 "공정 요약 표" + 표 셀에 sparkline 컬럼 추가. 한 화면에 정보 ↑.

Page header + filter bar + KPI row: Variant A와 동일.

큰 표 (Variant A의 두 섹션을 1개로 통합):
- 컬럼: 모델 / 공장 / 공정명 / CMP / 30일 추이(sparkline) / UPH / Eff. / Δ / 최근 갱신
- 행 28px (Variant A보다 4px 컴팩트), 셀 padding 4px 8px
- 모든 숫자 셀 Plex Mono 12px
- Sparkline 컬럼: 폭 80px, height 18px, 와인레드 1px line + 마지막 점만 점 마커
- 표 max-height 720px, sticky thead, sticky 좌측 1~2 컬럼
- 행 hover bg #F7F8FA, 클릭 시 좌측 2px 와인레드 마커
- 30행 이상 채워서 밀도 보여줄 것

표 위 작은 메타 바: "표시 24/124 행 · 정렬 CMP↓" (12px Plex Mono Ink Muted)

다크모드 X, calm 톤 유지. 정보 밀도가 높아진 모습만.
```

---

## S4 — MTBA Detail View (드릴다운)

### 🅐 S4·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View — 드릴다운 분석 화면

Variant strategy — Safe:
Variant A의 사이드바 + 페이지 헤더 패턴 동일. 활성 메뉴 "MTBA Detail". 콘텐츠는 패널 카드 1개 + 우측 슬라이드인 디테일 패널 오픈 상태로 그릴 것.

Page header:
- 11px uppercase eyebrow "PRODUCTIVITY · MTBA · DETAIL"
- 28px H1 "MTBA Detail View"
- 13px Ink Muted "표 셀 클릭 시 우측에 알람 상세가 열립니다"
- 우측 toolbar: [페이지 상태 초기화] (보더 버튼) [+ 패널 추가] (Primary 와인레드)

상단 컨트롤 라인 (1줄, padding 8px 0):
- "모델 선택" 라벨 + select (R50 / R53A / R53B), 기본 R50
- 우측에 12px Ink Muted "패널 1개 · 마지막 갱신 2026-04-28 23:50"

패널 카드 (`soft-card`):
- padding 16px, radius 8px, border 1px, bg #FFFFFF
- 카드 헤더 행: 14px 700 "조회 패널 #1" + 우측 라인 아이콘 [collapse ▾] [remove ✕]
- 카드 안 info chip 행 (작은 회색 칩 4개, padding 2px 10px, radius 999px, border 1px, 12px Plex Mono):
  · "FOL In-line"   · "R50"   · "panels=1"   · "rows=312"
- chip 행 아래 표 (st-aggrid 스타일 흉내):
  · 컬럼: 알람명 / 호기 / 모델명 / 설비세그먼트명 / MTBA / 생산수량 / 알람구분
  · 행 32px, sticky thead, 숫자 우측정렬 Plex Mono
  · MTBA 컬럼 셀: 값 + 옆에 작은 status dot (값 < 임계값일 때 #B23A48)
  · 행 hover #F7F8FA, 한 행은 "선택됨" 상태로 좌측 2px 와인 마커 + bg #F8E5EC (Primary Tint)
  · 12행 정도 샘플
- 표 아래 "디버그 정보 (패널 1)" — collapsed expander (라인 아이콘 ▸ + 텍스트), 기본 접힘

우측 슬라이드인 디테일 패널 (오픈 상태):
- viewport 우측에서 폭 480px 슬라이드 인 (오버레이 없이 콘텐츠 우측에 fixed)
- 헤더: 18px 700 "Lens AA · 알람상세" + close ✕
- 탭: [요약] [상세] [메모/이미지] — 활성 "요약" 와인레드 2px 밑줄
- 요약 탭 내용:
  · KPI 미니 카드 3개 (가로 1열): "MTBA" 14.2 / "생산수량" 1247 / "알람횟수" 88 (각 라벨 + Plex Mono 22px 숫자)
  · 하단 작은 표 "최근 알람 5건" (시간 / 호기 / 알람명, 14px 행)
- 닫혀있을 때는 표시하지 말고 이번 시안에서는 열린 상태로 그릴 것

Empty/Loading state는 표 빈 행 자리에 차분한 카피로 1줄 처리.
```

### 🅑 S4·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View

Variant strategy — Bold:
Variant A 그대로. 다음만 차이:
- 콘텐츠 최상단 8px 와인레드 단색 strip
- 패널 카드 좌측 3px 와인레드 vertical bar (조회 패널 정체성 강조)
- 슬라이드인 디테일 패널 좌측 4px 와인레드 vertical bar
- 탭 활성 표시는 2px → 3px 밑줄
- "+ 패널 추가" 버튼 좌측에 라인 아이콘 [+] 같이 배치

남은 룰 모두 Variant A 동일.
```

### 🅒 S4·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View

Variant strategy — Wild (다중 패널 + sparkline):
Variant A의 "패널 카드 1개" 대신 패널 카드 2개를 위·아래로 배치 (둘 다 펼침). 각 패널 안 표에 30일 sparkline 컬럼 추가.

레이아웃:
- 페이지 헤더 + 상단 컨트롤 라인은 Variant A와 동일
- 패널 카드 #1: 모델 R50 / 표 12행 / sparkline 컬럼 포함
- 패널 카드 #2: 모델 R53A / 표 12행 / sparkline 컬럼 포함 (#1 아래 16px gap)
- 각 패널 헤더에 "panel #1 · R50" / "panel #2 · R53A" 작게 표시 (12px Plex Mono Ink Muted)

표 변경:
- 컬럼: 알람명 / 호기 / MTBA / 30일 추이(sparkline 80×18px) / 생산수량 / 알람구분 / 액션
- 행 28px (4px 컴팩트), padding 4px 8px
- 모든 숫자 Plex Mono 12px
- 액션 컬럼: 라인 아이콘 [chevron-right] hover 시 와인레드

우측 슬라이드인 디테일 패널은 Variant A와 동일하게 열린 상태로 그릴 것 (패널 #1의 한 행을 선택한 가정).

다크모드 X, 강한 색 X. 정보 밀도만 ↑ 한 콘솔형 룩.
```

---

## 사용 방법 (클로드 디자인 / Stitch)

1. 위 12개 프롬프트 중 **하나만** 선택하여 복사 (공통 컨텍스트 블록 + 해당 Variant 블록)
2. claude.ai 새 대화에 붙여넣기 → 아티팩트로 단일 HTML이 생성됨
   - 또는 https://stitch.withgoogle.com 에 붙여넣기 → 이미지 시안
3. 결과 파일 저장 위치 권장:
   ```
   docs/design/mockup-S{1-4}-{A|B|C}.html
   docs/design/mockup-S{1-4}-{A|B|C}.png
   ```
4. 같은 화면 A/B/C를 모두 받아 비교한 뒤 화면별로 1개를 픽
5. 픽 결과 → `/design-shotgun` 또는 `/design-html` 로 프로덕션 HTML/CSS 변환
6. 그 결과를 Streamlit `st.markdown('<style>…</style>', unsafe_allow_html=True)` 로 주입

---

## S5 — UPH Dashboard

> 원본 라벨: `docs/design/originals/04-uph-dashboard.md`
> 단일 패널 + 6개 분석 섹션 (UPH 요약 / Best·Worst / Trend / 편차동작 / 증가추세 / 하락추세).

### 🅐 S5·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: UPH / 동작시간 분석 Dashboard

Variant strategy — Safe (Stripe Dashboard 톤):
사이드바(활성 "UPH Dashboard") + 콘텐츠. 콘텐츠는 헤더 + 필터 + 6개 섹션 수직 스택.

Page header:
- eyebrow "PRODUCTIVITY · UPH"
- H1 "UPH / 동작시간 분석 Dashboard"
- sub "선택 날짜: 2026-04-28 · Gumi Campus 1 Area / APS Test / R53A"
- 우측 toolbar [↻ 새로고침] [↓ Export]

Filter bar (1줄):
- 공장 선택 (select, 기본 "Gumi Campus 1 Area")
- 공정 선택 (select, 기본 "APS Test")
- 모델 선택 (select, 기본 "R53A")
- 날짜 선택 (date)
- "Trend 분석 기간(일)" segmented control [30] [90] (활성 30 — 와인레드 2px 밑줄)
- 우측 끝 toggle "I-TAS 가능만 보기" (switch)

Section 1 — "1. UPH 요약 (I-TAS)":
- 가로 4 KPI 카드 (Plex Mono 32px 숫자): UPH / Cycle Time / 동작시간 합계 / 가동률
- 카드 우상단 작은 link "MES 데이터로 보기" (13px Ink Muted)
- 섹션 우측 회색 박스 "AI 분석 의견" 폭 320px, padding 12px, border 1px, 12px 본문 4-5줄 차분한 한국어 분석 멘트

Section 2 — "2. Best Worst 동작차이":
- 좌우 2단 (Best / Worst)
- 각 단: 헤더 "Best" 또는 "Worst" + 14px Ink Muted "자동선정 Best: #1003 / Worst: #1116"
- 그 아래 표 (8행, 컬럼: 동작명 / 동작시간 / 차이 / 빈도)

Section 3 — "3. UPH / 편차율 Trend":
- 가로 폭 100% 차트 카드, height 280px
- monotone 와인레드 line + Status warn dashed 보조선만 (2색)
- x축 30개 일자, y축 좌(UPH 막대) + y축 우(편차율 라인)

Section 4 — "4. 주요 편차동작":
- 표 12행 (동작명 / 평균 / 편차 / 빈도 / 추세 sparkline 작게)

Section 5 — "5. 동작시간이 증가 추세인 동작":
- 표 8행 (동작명 / 시작 / 현재 / 증가율 / 30일 sparkline)
- 증가율 셀 색은 Status Bad

Section 6 — "6. 동작시간이 하락 추세인 동작":
- 표 8행 (동작명 / 시작 / 현재 / 하락율 / 30일 sparkline)
- 하락율 셀 색은 Status Good

샘플 데이터는 R53A · APS Test 공정 가정으로 사실적인 한국어 동작명을 채울 것.
```

### 🅑 S5·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: UPH / 동작시간 분석 Dashboard

Variant strategy — Bold:
Variant A 그대로. 차이만:
- 콘텐츠 최상단 8px 와인레드 단색 strip
- 6개 섹션 헤딩 좌측 4px 와인레드 vertical bar (1번~6번)
- KPI 카드 4개 좌측 3px 와인레드 vertical bar
- "AI 분석 의견" 박스 좌측 3px 와인레드 bar 추가, 박스 헤더 "AI" 11px uppercase 와인레드

남은 룰 모두 Variant A 동일.
```

### 🅒 S5·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: UPH / 동작시간 분석 Dashboard

Variant strategy — Wild (한 화면 압축, 표 주도):
6개 섹션을 2단 그리드(좌 60% / 우 40%)로 압축.

좌측 (60%):
- KPI row 4개 (가로)
- 큰 Trend 차트 카드 (height 240px)
- "주요 편차동작" 표 20행 (sparkline 컬럼 포함, 행 28px)

우측 (40%):
- 상단 카드 "Best · Worst" — 좌우 2단 미니표 6행씩
- 중단 카드 "증가 추세 동작" 8행 (sparkline)
- 하단 카드 "하락 추세 동작" 8행 (sparkline)
- 우측 카드 모두 폭 동일, 16px gap

"AI 분석 의견" 은 KPI row 우측 인라인으로 좁게 폭 280px (Variant A의 320px → 280px).

다크모드 X. 정보 밀도만 ↑.
```

---

## S6 — MTBA Dashboard

> 원본 라벨: `docs/design/originals/05-mtba-dashboard.md`
> 다중 패널 구조 (패널 1개 시작, 추가/제거 가능). 패널 안: 필터 → 비교 차트 → 요약 표 → 메모/이미지 업로드.

### 🅐 S6·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Dashboard

Variant strategy — Safe:
사이드바 활성 "MTBA Dashboard". 콘텐츠는 페이지 헤더 + 패널 카드 1개(펼침 상태) + 빈 "+ 패널 추가" 버튼.

Page header:
- eyebrow "PRODUCTIVITY · MTBA"
- H1 "MTBA Dashboard"
- sub "선택한 기간 기준으로 기간별 MTBA / 공정 통계 / 클릭 Drill-down 기반 MTBA 현황 / Alarm 차이 분석"
- 우측 toolbar [↻ 새로고침] [↓ Export]

패널 카드 #1 (`soft-card`, padding 16px, radius 8px, border 1px):
- 카드 헤더: "MTBA 분석 Reporting #1" (14px 700) + 우측 [▾ 접기] [✕ 제거]

- 패널 안 1열: 필터 행 (3 입력)
  · "팀 선택 #1" (select, 기본 "전체")
  · "모델 선택 #1" (select, 기본 "R50")
  · "기간 선택 #1" (date range, "2026-04-27 ~ 2026-04-28")
- 그 아래 12px Ink Muted 안내문 4줄:
  · "※ 팀 = 전체 : 모든 공정을 대상으로 조회합니다."
  · "※ 그래프 구간: 선택한 기간 / 1주전 / 2주전 / 지난달 전체 / 2달전 전체 / 지난해 전체"
  · "※ MTBA가 0이거나 없는 설비는 자동 제외 후, 유효 설비만 평균하여 MTBA를 계산합니다."
  · "※ 그래프 가시성을 위해 막대 높이는 최대 120까지만 표시되며, 라벨은 실제 MTBA 값을 표시합니다."

- 섹션 1 — "1. R50 공정별 MTBA 기간 비교":
  · 좌측 4px 와인레드 vertical bar + 18px 700 헤딩
  · 6개 시리즈 그룹 막대 차트, height 320px
  · 막대는 monotone 와인레드 그라디언트 또는 Status 3색만 (선택한기간/1주전/2주전 등 6 구간)
  · 차트 우측 미니 컨트롤 [그래프 데이터 보기] [선택 초기화] (보더 버튼)
  · 차트 아래 12px Ink Muted "※ Shift+클릭 / Box / Lasso로 여러 공정을 선택할 수 있습니다."

- 섹션 2 — "2. MTBA 현황(2026-04-27 ~ 2026-04-28)":
  · 헤딩 + 우측 작은 toggle "공정명 축약" (switch)
  · 표 (sticky thead, 행 32px) — 컬럼: 공정명 / 호기 / 모델명 / 설비세그먼트명 / MTBA / 생산수량 / 알람구분 / Δ
  · 12행 샘플
  · 한 행 active 가정 (좌측 2px 와인 마커 + Primary Tint bg)
  · 안내문 12px Ink Muted "※ 알람구분 셀을 더블클릭하면 메모/이미지 팝업이 열립니다."

- 섹션 3 — "3. 공정별 요약" (작은 표 6행, 컬럼: 공정 / 평균 MTBA / 알람 / 생산수량)

- 섹션 4 — "4. 메모 / 이미지 업로드":
  · 좌측 (60%) "메모 입력 #1" — textarea height 120px, border 1px, radius 8px, placeholder "메모를 입력하세요"
  · 우측 (40%) "이미지 업로드 #1" — dropzone box border 1px dashed #CBD0D6, padding 24px, 가운데 정렬:
    - 라인 아이콘 (upload-cloud)
    - 14px "Drag and drop file here"
    - 12px Ink Muted "Limit 200MB per file • PNG, JPG, JPEG, BMP"
    - 작은 보더 버튼 [Browse files]
  · 카드 하단 우측 [메모/이미지 저장 #1] (Primary 와인레드)

- 패널 카드 풋 행 (보더 버튼 2개): [이 패널 아래에 추가 #1] [이 패널 제거 #1]

패널 카드 아래 16px gap → 빈 [+ 패널 추가] 점선 보더 버튼 (height 56px, 가운데 정렬, 12px Ink Muted "패널을 추가하면 새 분석 보고서가 생성됩니다")

샘플 공정명은 originals 의 실제 한국어 라벨 사용 (Lens AA / Flip Chip Bonding / IRCF Attach 등).
```

### 🅑 S6·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Dashboard

Variant strategy — Bold:
Variant A 그대로. 차이만:
- 콘텐츠 최상단 8px 와인레드 단색 strip
- 패널 카드 좌측 4px 와인레드 vertical bar (패널 정체성)
- 섹션 헤딩 좌측 vertical bar 두께 4px → 6px
- "메모/이미지 저장 #1" 버튼 좌측에 라인 아이콘 [save]
- "이미지 업로드" dropzone 활성/hover 시 border 색 와인레드로 변경
- "+ 패널 추가" 버튼 hover 시 와인레드 점선

남은 룰 모두 Variant A 동일.
```

### 🅒 S6·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Dashboard

Variant strategy — Wild (다중 패널 + 압축 레이아웃):
패널 카드를 1개가 아니라 **2개** 표시 (서로 다른 모델, R50 / R53A). 각 패널 안 안내문 4줄을 "?" 아이콘 hover 툴팁으로 압축. 표는 28px 행에 sparkline 컬럼 추가.

레이아웃:
- 페이지 헤더 동일
- 패널 #1 (R50): 펼침, 표 16행, sparkline 30일 컬럼 추가
- 패널 #2 (R53A): 펼침, 표 14행, sparkline 30일 컬럼 추가
- 두 패널 사이 16px gap
- "메모/이미지 업로드" 섹션은 각 패널 하단에 그대로 유지 (텍스트영역만, 이미지 업로드는 작게 1줄 inline 형태)

패널 카드 헤더에 작은 메타 행 (12px Plex Mono Ink Muted): "panel #1 · R50 · 12 procs · last sync 23:50"

다크모드 X. 정보 밀도만 ↑.
```

---

## S7 — MTBA Detail View · 빈 상태 (Empty / Initial)

> S4 의 데이터-있는 상태와 짝. 첫 진입·조회 전 상태로, "조회 시작" 안내가 핵심.

### 🅐 S7·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View — 빈 상태 (Empty / Initial)

Variant strategy — Safe:
S4 Variant A 와 동일한 사이드바·페이지 헤더·상단 컨트롤 라인. 단 패널 카드 안 표 자리가 "빈 상태"로 표시되며, 우측 슬라이드인 디테일 패널은 표시되지 않음.

Page header:
- eyebrow "PRODUCTIVITY · MTBA · DETAIL"
- H1 "MTBA Detail View"
- sub "실행 복구 안정판 · Comment 이력 포함"
- 우측 toolbar [페이지 상태 초기화] [+ 패널 추가] (Primary 와인레드)

상단 컨트롤 라인:
- "모델 선택 #1" (select, 비어있는 placeholder "모델을 선택하세요")
- 우측 12px Ink Muted "조회 전 · 모델을 선택하면 데이터가 로드됩니다"

패널 카드 #1 (`soft-card`):
- 카드 헤더: "조회 패널 #1" + 우측 [▾] [✕]
- 카드 안 info chip 행: 칩 placeholder 4개 (회색 dashed 보더, 텍스트 "—") · "—"
- 표 자리에 빈 상태 컴포넌트:
  · 가운데 정렬, padding 64px 0
  · 라인 아이콘 (database / search) 32×32, color #CBD0D6
  · 14px 600 "조회 전입니다" (Ink Body)
  · 13px Ink Muted "상단 모델 선택 후 [조회 실행] 버튼을 눌러 데이터를 불러옵니다."
  · 그 아래 [조회 실행] 버튼 (Primary 와인레드, height 36px) — 비활성 상태 (모델 미선택 시 disabled, opacity 0.5)
- "디버그 정보 (패널 1)" expander 접힘 상태로 표시 (라인 아이콘 ▸ + 텍스트만)

빈 상태 카피는 차분한 한국어, 느낌표 X.
```

### 🅑 S7·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View — 빈 상태

Variant strategy — Bold:
Variant A 그대로. 차이만:
- 콘텐츠 최상단 8px 와인레드 strip
- 패널 카드 좌측 4px 와인레드 vertical bar
- 빈 상태 안내 영역 좌측에 작은 와인레드 dot (6px)
- [조회 실행] 버튼 비활성 시도 와인레드 보더만 유지 (배경은 회색)

남은 룰 모두 Variant A 동일. 빈 상태에서도 정체성 표시.
```

### 🅒 S7·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MTBA Detail View — 빈 상태

Variant strategy — Wild (빈 상태에서 가이드 + 단축키 안내):
Variant A 의 빈 상태 영역을 더 정보형으로. 엔지니어에게 "다음에 무엇을 할 수 있는지" 미리 보여주는 콘솔 톤.

빈 상태 영역 (padding 48px, 가운데):
- 14px 600 "조회 전입니다"
- 13px Ink Muted 안내 4줄, 좌측 정렬, 가운데 정렬된 박스 안:
  · "1. 상단 모델을 선택"
  · "2. 패널이 비어있으면 [+ 패널 추가] 로 새 패널 생성"
  · "3. 표 셀 클릭 시 우측 디테일 패널 오픈"
  · "4. 단축키: Shift+클릭 다중 선택 / Esc 패널 닫기"
- 각 줄 좌측에 작은 IBM Plex Mono 12px 번호 (`01` / `02` / `03` / `04`)
- 마지막에 [조회 실행] (와인레드, disabled) + 옆에 보더 버튼 [+ 패널 추가]

남은 룰은 Variant A 동일. 다크모드 X.
```

---

## S8 — MaxCapa Chat (대화형 조회)

> 원본 라벨: `docs/design/originals/08-maxcapa-chat.md`
> 채팅형 인터페이스 — 입력창 + 응답 카드 + 분석 결과(표·차트).

### 🅐 S8·Variant A (Safe)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MaxCapa Chat (대화형 생산지표 조회)

Variant strategy — Safe:
사이드바 활성 "MaxCapa Chat". 콘텐츠는 페이지 헤더 + 안내 카드 + 채팅 히스토리 + 입력 바.

Page header:
- eyebrow "PLATFORM · CHAT"
- H1 "MaxCapa Chat"
- sub "MaxCapa Chat(대화형 생산지표조회)"

안내 카드 (radius 8px, border 1px, padding 16px, bg #FFFFFF):
- 14px 600 "지원 예시"
- 13px Ink Muted 본문 1줄: "기본 조회는 MES UPH(uph_input_runtime_daily_model), 질문에 ITAS를 명시하면 ITAS UPH(itas_uph_result)로 조회합니다."
- 그 아래 12px Plex Mono 예시 4개 (각 줄 좌측 작은 ▸ 아이콘):
  · `R53A · APS Test · 2026-04-28 UPH 추이`
  · `R50 Lens AA 공정 ITAS UPH 30일`
  · `Gumi Campus 1 Area 어제 MTBA Top 10`
  · `최근 7일 R53B Flip Chip Bonding 알람 추이`
- 각 예시 클릭 시 입력창에 자동 입력 (마우스오버 시 옅은 와인레드 underline)

채팅 히스토리 영역 (max-height 60vh, vertical scroll):
- 사용자 메시지 (우측 정렬, bg #F1F3F5, radius 8px, padding 10px 14px, max-width 60%):
  "R53A · APS Test · 2026-04-28 UPH 추이 알려줘"
- AI 응답 메시지 (좌측 정렬, bg #FFFFFF, border 1px, radius 8px, padding 16px, max-width 80%):
  - 헤더: 11px uppercase Plex Mono Ink Muted "MAXCAPA · MES UPH"
  - 본문 1줄: "최근 30일 UPH 추이입니다. 평균 247 UPH (전주 대비 +1.8%)."
  - 작은 차트 카드 (height 200px, monotone 와인레드 line)
  - 차트 아래 작은 표 5행 (날짜 / UPH / 동작시간 / Δ)
  - 카드 우하단 작은 액션 [↓ Export] [↗ 대시보드 열기] (text-only 13px Ink Muted)

입력 바 (페이지 하단 고정, 폭 100%, padding 12px 16px, border-top 1px):
- input field 1줄 (height 44px, radius 8px, border 1px, placeholder "질문을 입력하세요")
- 우측 [질문 분석 및 실행] (Primary 와인레드, height 44px, padding 0 20px)
- 입력창 좌측에 라인 아이콘 (search) 18×18

샘플 응답 1쌍 채워서 빈 채팅이 아닌 형태로 그릴 것.
```

### 🅑 S8·Variant B (Bold)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MaxCapa Chat

Variant strategy — Bold:
Variant A 그대로. 차이만:
- 콘텐츠 최상단 8px 와인레드 단색 strip
- AI 응답 카드 좌측 3px 와인레드 vertical bar (사용자 메시지에는 없음)
- 입력 바 [질문 분석 및 실행] 버튼 좌측에 작은 라인 아이콘 (send / arrow-up)
- "지원 예시" 카드 좌측 3px 와인레드 vertical bar

남은 룰 Variant A 동일.
```

### 🅒 S8·Variant C (Wild for engineers)

```
[공통 컨텍스트 위 블록 그대로 붙여넣기]

Screen: MaxCapa Chat

Variant strategy — Wild (2단 — 좌측 채팅 / 우측 SQL·디버그 패널):
엔지니어가 "AI 가 어떤 SQL 을 돌렸나"를 같이 볼 수 있는 콘솔형.

레이아웃:
- 좌측 (60%) 채팅 — Variant A 와 동일
- 우측 (40%) "쿼리 패널" 카드:
  · 헤더 11px uppercase Plex Mono "LAST QUERY · MES UPH"
  · 작은 메타 행: "rows=30 · 142 ms · 2026-04-28 23:51"
  · 본문 SQL 코드 블록 (bg #F1F3F5, padding 12px, radius 8px, IBM Plex Mono 12px, 시그니처 SELECT … FROM uph_input_runtime_daily_model WHERE … 8-12줄)
  · 카드 하단 작은 보더 버튼 [↓ Copy SQL] [↻ Re-run]

채팅 히스토리는 max-height 60vh 유지, 우측 패널은 viewport 따라 sticky.

입력 바는 좌측 채팅 컬럼 폭에만 (우측 패널 위에는 안 깔림).

다크모드 X. 정보 밀도만 ↑.
```

---

## 12 → 24 프롬프트 인벤토리

| 화면 | 원본 라벨 파일 | A | B | C |
|---|---|---|---|---|
| S1 Login | `originals/01-login.md` | ✅ | ✅ | ✅ |
| S2 Home | `originals/02-home.md` | ✅ | ✅ | ✅ |
| S3 CMP Dashboard | `originals/03-cmp-dashboard.md` | ✅ | ✅ | ✅ |
| S4 MTBA Detail (data) | `originals/06-mtba-detail.md` | ✅ | ✅ | ✅ |
| S5 UPH Dashboard | `originals/04-uph-dashboard.md` | ✅ | ✅ | ✅ |
| S6 MTBA Dashboard | `originals/05-mtba-dashboard.md` | ✅ | ✅ | ✅ |
| S7 MTBA Detail (empty) | `originals/07-mtba-detail-empty.md` | ✅ | ✅ | ✅ |
| S8 MaxCapa Chat | `originals/08-maxcapa-chat.md` | ✅ | ✅ | ✅ |

총 **24개 프롬프트**. 8개 화면 모두 커버.
