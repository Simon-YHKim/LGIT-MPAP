# 핸드오프 프롬프트 — home.html v2 재작성 작업 이어가기

> **사용법**: 새 Claude Code 세션에서 이 파일 통째로 붙여넣어 컨텍스트 복원.
> 작성 시각: 2026-04-29
> 이전 세션 마지막 커밋: `efcc53e` (feat(design): add home.html S2 v1)

---

## 컨텍스트 (이미 푸시된 상태)

레포: `Simon-YHKim/LGIT-MPAP`
브랜치: `claude/setup-simonk-stack-Sry57`
프로젝트: **LG Innotek VITALS** — 광학솔루션 사업부 설비 생산성 분석 플랫폼
캐치프레이즈: "공정의 호흡을 데이터로 듣다"
제작: 생산혁신센터 Max Capa 팀

### 디자인 토큰 (DESIGN.md / Calm Engineering 방향)
- Primary Wine Red: `#A50034`, dark `#7E0027`, tint `#F8E5EC`
- Page bg `#F7F8FA`, Card `#FFFFFF`, Soft `#F1F3F5`
- Border `#E5E7EB`, Strong `#CBD0D6`
- Ink `#1F2430` / muted `#6B7280` / subtle `#9CA3AF`
- Status: Good `#1F8B4C`, Warn `#B57F1B`, Bad `#B23A48`
- 폰트: **LG EI Text** (body) / **LG EI Headline** (display) / **IBM Plex Mono** (숫자)
- 자체 호스팅 woff2: `docs/design/fonts/lg-ei-text-{300,400,600,700}.woff2`, `lg-ei-headline-{100,300,400,600,700}.woff2`
- 로고: `docs/design/assets/lg-innotek-logo-en-{white,gray}.png` (원본 196×36)

### 기 완료 파일
- `docs/design/landing.html` (S1 Login, 다크 비디오 bg, 540px→480px 카드, "Vitals." 와인 점 hero, 2-step 회원가입, 7개 i18n)
- `docs/design/home.html` (S2 v1, 좌측 사이드바 + 5 카드 그리드 — **이번에 재작성 대상**)

---

## 작업: home.html 재작성 (v2)

### 사용자 피드백 5건 (반영 필수)

1. **LG Innotek 로고**: 원본 비율 (196×36, 약 5.44:1) **반드시** 유지. height 24~28px + width auto + display block.

2. **3 대분류로 카드 그룹화**:
   - **생산** (Production): CMP 달성률 → CMP Dashboard
   - **설비 성능** (Equipment Performance): UPH 관련 → UPH Dashboard
   - **설비 효율** (Equipment Efficiency): MTBA 관련 → MTBA Dashboard + MTBA Detail View

3. **상단 가로 네비게이션**: 좌측 사이드바 → **상단 가로 nav 바**. 7개 항목 동일 유지(login / Home active / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat) — Intent Contract.

4. **언어 적용 점검**: 모든 가시 한국어 텍스트가 `data-i18n` 속성을 가지고, 7개 언어(ko/en/vi/pl/id/es/zh) 사전에 키가 있는지 확인. 누락 시 ko fallback.

5. **우측 너비 조정 가능 채팅 패널**: MaxCapa Chat 을 우측 고정 패널로 이동.
   - 기본 width 360px, min 280px, max 720px
   - 좌측 edge 4px drag handle (cursor: col-resize)
   - localStorage 로 width 기억
   - collapse / expand 토글
   - 내부: 헤더 + 안내(MES UPH 기본 / ITAS 분기) + 지원 예시 + textarea + 전송 버튼
   - MaxCapa Chat 카드는 카테고리에서 빠짐 (패널이 대체)

### 권장 레이아웃

```
[Topbar Row 1: 56px]
  [LG Innotek logo · width auto height 24-28] [VITALS · 생산혁신센터 · Max Capa 팀] ............ [lang switcher]
[Topbar Row 2: 48px sticky, 1px bottom border]
  [login] [Home active] [CMP Dashboard] [UPH Dashboard] [MTBA Dashboard] [MTBA Detail View] [MaxCapa Chat]

[Body — flex row]
  [Main flex 1]
    [Page header: PLATFORM · VITALS / "분석 도구" h1 / sub]

    [Category 1 — 생산]
      h2 "생산"  ·  small "Production"
      [Card: CMP Dashboard · 정식 5/22E]

    [Category 2 — 설비 성능]
      h2 "설비 성능"  ·  small "Equipment Performance"
      [Card: UPH Dashboard · 가오픈 4/29~ · 정식 5/22E]

    [Category 3 — 설비 효율]
      h2 "설비 효율"  ·  small "Equipment Efficiency"
      [Card: MTBA Dashboard · 가오픈 4/29~ · 정식 5/15E]
      [Card: MTBA Detail View · 가오픈 4/29~ · 정식 5/15E]

    [Page foot: 제작 · 생산혁신센터 Max Capa 팀 / 변경 로그 보기]

  [Right Chat Panel — width 360px (resizable)]
    [drag handle 4px 좌 edge]
    [header: ◀ collapse | "MaxCapa Chat" | • LIVE]
    [hint card (좌 4px 와인): 데이터소스 자동 분기]
    [examples card: Q1~Q4 예시 chip]
    [thread (placeholder empty state)]
    [composer: textarea + 데이터소스 chip + 질문 분석 및 실행 버튼]
```

### 룰 (위반 금지)

- LG EI Text + LG EI Headline + Plex Mono 폰트만
- 와인레드 `#A50034` 강조 1점 정책 (3색 룰)
- 22px round X (8~12px)
- pure black X / Inter X / 이모지 아이콘 X / 4색 이상 차트 X / 큰 hero gradient X
- bounce/elastic easing X (`cubic-bezier(0.2,0.6,0.3,1)`)
- 데스크톱 1280~1880px, 1440px 기준
- 한국어 라벨 verbatim, 의역 금지
- AI 슬롭 방지: 노란 mark X / 사각 ChatGPT 아바타 X / fake trace_id X / "↳" glyph X
- 사이드바 7개 항목 순서·라벨 절대 변경 X (이제 상단 nav)

### Intent Contract (Home, 누락 금지)

5개 분석 도구 진입 게이트, 각 도구 오픈 상태 표시(`정식`/`가오픈`/`오픈예정`), "제작 · 생산혁신센터 Max Capa 팀" 푸터.

> MaxCapa Chat 이 카드에서 빠지지만 우측 패널에 항시 노출 + 상단 nav 7번째 항목으로 유지 → Intent 충족.

### 검증 명령

작업 후 다음 실행:

```bash
cd /home/user/LGIT-MPAP
python3 -c "
import re
src=open('docs/design/home.html').read()
from collections import Counter
opens=re.findall(r'<(div|main|aside|form|section|nav|header|footer|a|h[1-6])\b', src)
closes=re.findall(r'</(div|main|aside|form|section|nav|header|footer|a|h[1-6])\b', src)
print('opens=',Counter(opens))
print('closes=',Counter(closes))
print('lines=',src.count(chr(10)))
print('data-i18n count=', src.count('data-i18n'))
print('has lang switcher=', 'lang-current' in src)
print('has chat panel=', 'chat-panel' in src)
print('has 3 categories=', src.count('class=\"category\"'))
"
git add docs/design/home.html
git commit -m "feat(design): home.html v2 — top nav + 3 categories + resizable chat panel"
git push
```

배포 URL (검증):
```
https://raw.githack.com/Simon-YHKim/LGIT-MPAP/claude/setup-simonk-stack-Sry57/docs/design/home.html?v=N
```

### 시작 신호

위 사양으로 `/home/user/LGIT-MPAP/docs/design/home.html` 을 **단일 Write 호출**로 처음부터 다시 작성. 직전 v1 (사이드바 + 5 카드 그리드) 은 완전히 폐기. 한 번에 완성하고 커밋·푸시.
