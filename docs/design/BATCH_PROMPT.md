# Claude Design — 일괄 지시 프롬프트 (Batch Prompt)

> **사용법**: 이 파일 안 "프롬프트 본문" 블록을 통째로 복사해 claude.ai Project 새 대화에 붙여넣는다.
> Claude 가 화면별로 응답을 8회 나눠서 24개 아티팩트를 생성한다.
>
> **권장 환경**: claude.ai Pro/Team + GitHub 커넥터 연결 (없을 시 수동 업로드).

---

## 프롬프트 본문 (전체 복사)

```
LG Innotek VITALS 디자인 시안 일괄 생성 작업.

## 연결된 레포 파일 (이 순서로 정독 후 작업 시작)
1. DESIGN.md — Calm Engineering 방향 디자인 시스템 (브랜드/컬러/타이포/레이아웃/9 컴포넌트/4 화면)
2. docs/design/CLAUDE_PROJECT_INSTRUCTIONS.md — 출력 규칙 / 안티패턴 / 한국어 룰
3. docs/design/originals/01-login.md ~ 08-maxcapa-chat.md — 화면별 한국어 라벨 verbatim
4. docs/design/stitch-prompts-2026-04-29.md — 화면 × 변형별 프롬프트 24종

## 작업 정의

8 화면 × A/B/C 3 변형 = 총 24 시안. 화면 매핑:
- S1 Login         ↔ originals/01-login.md
- S2 Home          ↔ originals/02-home.md
- S3 CMP Dashboard ↔ originals/03-cmp-dashboard.md
- S4 MTBA Detail (data state)  ↔ originals/06-mtba-detail.md
- S5 UPH Dashboard ↔ originals/04-uph-dashboard.md
- S6 MTBA Dashboard ↔ originals/05-mtba-dashboard.md
- S7 MTBA Detail (empty)       ↔ originals/07-mtba-detail-empty.md
- S8 MaxCapa Chat  ↔ originals/08-maxcapa-chat.md

## 실행 순서 (이 순서를 어기지 마)

응답 길이 한계 때문에 **화면별로 1회씩, 총 8회 응답 분할**해서 진행한다.
한 화면당 한 응답 안에서 A/B/C 3 아티팩트를 모두 만든다.

라운드 1: S1 (Login) — A, B, C 3 아티팩트
라운드 2: S2 (Home) — A, B, C
라운드 3: S3 (CMP Dashboard) — A, B, C
라운드 4: S4 (MTBA Detail data) — A, B, C
라운드 5: S5 (UPH Dashboard) — A, B, C
라운드 6: S6 (MTBA Dashboard) — A, B, C
라운드 7: S7 (MTBA Detail empty) — A, B, C
라운드 8: S8 (MaxCapa Chat) — A, B, C

각 라운드 끝에는 항상 "다음 라운드 준비 완료. 다음 ▶" 한 줄로 마무리.
사용자가 "다음" 또는 "continue" 라고 답하면 다음 라운드 시작.

## 각 아티팩트 출력 규칙 (24개 모두 공통)

- 단일 self-contained HTML 파일, inline `<style>`, 외부 리소스는 Pretendard CDN만:
  https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable.css
- 데스크톱 1440px 기준 (반응형 X)
- 아티팩트 제목 / 파일명 형식: `mockup-S{1-8}-{A|B|C}.html`
  예) `mockup-S3-B.html`
- 화면 안 모든 한국어 라벨은 해당 originals 파일에서 verbatim 사용
  (의역·번역·라벨 변경 절대 금지)
- 사이드바 네비게이션 7개 항목 동일하게 유지: login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat
- 각 변형(A/B/C)의 정의는 stitch-prompts-2026-04-29.md 의 해당 블록에 명시된 대로:
  · A (Safe) = Linear/Stripe 클론, 와인레드 강조 1점만
  · B (Bold) = A + 콘텐츠 최상단 8px 와인레드 strip + 카드 좌측 vertical bar
  · C (Wild) = 정보 밀도 ↑ + sparkline / 다중 패널 / 모노 숫자 (단 다크모드는 X)

## 절대 어기면 안 되는 룰

- 다크모드 X (라이트만)
- Inter 폰트 X (Pretendard + IBM Plex Mono만)
- pure black/gray X (DESIGN.md 의 ink 토큰 사용)
- 4색 이상 multi-color 차트 X (monotone 와인 그라디언트 또는 Status 3색만)
- 22px 라운드 카드 X (8px 통일)
- 큰 hero 그라디언트 X / 페이지 전체 그라디언트 X
- 이모지 아이콘 X (라인 아이콘 inline SVG만)
- 폰트 weight 4개 이상 X (400/600/700)
- 의역·번역된 한국어 X (originals 그대로)

## 라운드 간 사용자 인터랙션

각 라운드 응답 끝에서 너는 묻지 말고 그냥 "다음 라운드 준비 완료. 다음 ▶" 만 출력.
사용자가 한 라운드를 보고 변형 변경(예: "S1·B 의 strip 두께 12px로") 을 요청하면
그 화면만 즉시 수정한 뒤 "다음 라운드 준비 완료. 다음 ▶" 으로 복귀.

## 시작 신호

이제 라운드 1 (S1 Login · A/B/C 3 아티팩트) 부터 시작해.
```

---

## 사용법 정리

1. claude.ai Project (`LG Innotek VITALS — Design`) 새 대화 열기
2. 위 "프롬프트 본문" 코드블록 통째로 복사 → 붙여넣기 → 전송
3. 라운드 1 응답 (S1·A/B/C 3 아티팩트) 도착 → 각 아티팩트 다운로드
4. `docs/design/mockup-S1-A.html` … `mockup-S1-C.html` 로 저장 후 푸시
5. 채팅창에 `다음` 또는 `continue` 입력 → 라운드 2 (S2) 진행
6. … 라운드 8까지 반복

## 중간에 변경할 일이 있으면

라운드 N 응답을 보고 마음에 안 드는 부분이 있으면 그 라운드 안에서 즉시:

```
S3·B 의 strip 두께 8px → 12px 로 변경하고, 같은 변형의 KPI 카드 좌측 bar 도 4px 로 키워줘.
나머지 (S3·A, S3·C) 는 유지. 수정본만 다시 출력.
```

수정 끝나면 `다음` 으로 다음 라운드 진입.

## 24개 다 받은 후

레포에 push 후 알려주시면, 화면별 픽(예: S1=B, S2=A, S3=C, …)을 정해 통합 디자인 토큰 CSS 1벌로 정리해서 8개 Streamlit 페이지에 일괄 적용하는 단계로 넘어갑니다.
