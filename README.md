# LG Innotek **VITALS**

> **공정의 호흡을 데이터로 듣다**
> 광학솔루션 사업부 · 생산혁신센터 · Max Capa 팀
> 설비 생산성 분석 플랫폼 (Equipment Productivity Analytics Platform)

---

## 한 줄 요약

LG Innotek 광학 사업부의 설비 생산성을 **CMP · UPH · MTBA** 세 축으로 통합 분석·조회하는 사내 엔지니어링 플랫폼. 현재는 **8 페이지 디자인 시안**이 완성됐고 백엔드 wire-up 단계 직전입니다.

---

## 빠른 시작

### 시안 한 링크로 체험 (raw.githack)

🔗 **랜딩부터 시작**: https://raw.githack.com/Simon-YHKim/LGIT-MPAP/main/docs/design/landing.html

랜딩에서 아무 ID/비밀번호로 [로그인] → home → 좌 사이드바로 모든 페이지 라우팅. 우상단 [로그아웃]으로 랜딩 복귀.

🔗 **시안 인덱스 (썸네일 그리드)**: https://raw.githack.com/Simon-YHKim/LGIT-MPAP/main/docs/design/index.html

---

## 페이지 인벤토리

| # | 파일 | 라벨 | 의도 |
|---|---|---|---|
| L | `docs/design/landing.html` | 랜딩 | 영상 hero + 2-step 인증 (로그인 / 회원가입 + 인증코드) |
| H | `docs/design/home.html` | 분석 도구 | 3 카테고리 (생산 / 설비 성능 / 설비 효율) × 16:9 카드 게이트웨이 |
| 1 | `docs/design/cmp-dashboard.html` | CMP 현황판 | 강조 KPI + 30일 추이 + 드릴다운 |
| 2 | `docs/design/uph-dashboard.html` | UPH 현황판 | Wild 비대칭 + Bold 와인 accent · 6 분석 컴포넌트 |
| 3 | `docs/design/mtba-dashboard.html` | 공정별 MTBA | 다중 패널 · 6구간 비교 (모든 기간 숫자) |
| 4 | `docs/design/mtba-detail.html` | MTBA 현황판 | 공장 매트릭스 · 셀 클릭 → 알람 모달 (TOP5 비중) |
| 5 | `docs/design/maxcapa-chat.html` | MaxCapa Chat | 풀 페이지 챗봇 (trace · SQL · KPI · 차트 · 표 · 의견 · 후속) |

---

## 인수인계 문서 (백엔드 + AI 에이전트용)

전체 사양 / 디자인 토큰 / 백엔드 wire-up / Intent Contract / Approved Decisions Log:

📄 **[`docs/design/HANDOFF.md`](./docs/design/HANDOFF.md)**

또는 raw 다운로드: https://raw.githubusercontent.com/Simon-YHKim/LGIT-MPAP/main/docs/design/HANDOFF.md

---

## 🤖 AI 에이전트 핸드오프 프롬프트

이 프로젝트를 다른 프레임워크 (Streamlit / Next.js / Django 등) 로 통합하거나 시안을 이어서 작업할 때, 새 Claude Code/Cursor/Copilot 세션 첫 메시지에 아래 프롬프트를 통째로 붙여넣으세요.

```
이 레포 (Simon-YHKim/LGIT-MPAP) 는 LG Innotek VITALS 라는
설비 생산성 분석 플랫폼의 디자인 시안입니다.

먼저 다음 두 파일을 반드시 읽고 작업을 시작하세요:
1. ./README.md            — 프로젝트 개요 + 페이지 인벤토리
2. ./docs/design/HANDOFF.md — 디자인 토큰, Intent Contract,
                              백엔드 wire-up 가이드,
                              Approved Decisions Log,
                              Anti-rules 모두 포함

핵심 원칙:
- 디자인 톤 = Calm Engineering (Linear · Stripe · Toss 영향)
- 3색 정책: 본문 무채 + 와인레드 #A50034 1점 + Status 3색
- 폰트: LG EI Text / LG EI Headline / IBM Plex Mono (Inter 금지)
- pure black / 4색 차트 / bounce easing / 큰 hero gradient 금지
- 사이드바 7 항목 순서·라벨 변경 금지 (Intent Contract)

작업 전 반드시 확인:
- 변경하려는 페이지의 의도 (HANDOFF.md §5)
- Verbatim 보존 항목 (HANDOFF.md §7 "Verbatim 보존 항목")
- 사용자 승인 결정사항 (HANDOFF.md §8 Approved Decisions Log)

답변 시 디자인 변경이 발생하면:
1. raw.githack 링크로 시안 미리보기를 함께 제공
2. 모든 페이지 일관성 유지
3. 변경 전 사용자 승인 여부 확인
```

---

## 디렉토리 구조

```
LGIT-MPAP/
├── README.md              # 이 파일
├── DESIGN.md              # Calm Engineering 톤·토큰 사양
└── docs/design/
    ├── HANDOFF.md         # 인수인계 문서 (외부 활용 진입점)
    ├── README.md          # 디자인 폴더 가이드 + Intent Contract
    ├── _app-shell.css     # 모든 인증 후 페이지 공통 chrome
    ├── _app-shell.js      # 공통 동작 + i18n base (7 언어)
    ├── landing.html       # 인증 페이지 (자체 호스팅 영상)
    ├── home.html          # 분석 도구 게이트웨이
    ├── cmp-dashboard.html # CMP 현황판
    ├── uph-dashboard.html # UPH 현황판
    ├── mtba-dashboard.html# 공정별 MTBA
    ├── mtba-detail.html   # MTBA 현황판 + 알람 모달
    ├── maxcapa-chat.html  # MaxCapa Chat
    ├── index.html         # 시안 썸네일 인덱스
    ├── assets/            # 로고 · hero 영상 · poster
    ├── fonts/             # LG EI Text/Headline (9 woff2)
    └── originals/         # 8 페이지 원본 한국어 라벨 verbatim
```

---

## 디자인 원칙 요약

자세한 내용은 [HANDOFF.md](./docs/design/HANDOFF.md) 참조.

| 영역 | 결정 |
|---|---|
| 톤 | Calm Engineering — 도구형, 장식 < 정보 밀도 |
| 컬러 | 본문 무채 + 와인레드 `#A50034` 1점 + Status 3색 (good/warn/bad) |
| 폰트 | LG EI Text (body) / LG EI Headline (display) / IBM Plex Mono (numbers) |
| 레이아웃 | 데스크톱 1280–1880px · 사이드바 240↔56px · 챗봇 360px (280–720 resize) |
| 모션 | `cubic-bezier(0.2, 0.6, 0.3, 1)` · bounce/elastic 금지 |
| i18n | 7 언어 (ko · en · vi · pl · id · es · zh) · ko fallback |
| 인증 | data-action endpoint 3개 (login / send-code / verify) · `mpap.session` localStorage |

---

## 라이선스 / 문의

LG Innotek 사내 자산. 외부 배포 금지.

문의: 광학솔루션 사업부 · 생산혁신센터 · Max Capa 팀
