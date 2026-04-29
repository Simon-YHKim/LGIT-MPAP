# `docs/design/` — LG Innotek MPAP 디자인 자료

> **이 폴더의 책임자**: claude/setup-simonk-stack-Sry57 브랜치
> **단계**: Calm Engineering 방향 1차 시안 14개 도착 → 사용자 피드백 → 2차 revision 대기
>
> **🚨 NON-REMOVAL CONTRACT (절대 룰)**
> 모든 후속 디자인 revision 에서 기존 페이지 기능은 **절대 제거 금지**.
> 추가는 허용. 시각적 단순화는 허용. **하지만 입력·필터·표 컬럼·분석 섹션·메타 데이터·인터랙션·디버그 패널 등 어떤 것도 사라지면 안 된다.**
> 원본 제작자(엔지니어 사용자)에게 그대로 전달 가능한 상태를 유지한다.

---

## 1. 페이지별 의도 (Intent Contract — 누락 금지 항목)

| # | Page | 의도 (반드시 보존되어야 하는 것) |
|---|---|---|
| **S1** | **Login** | LG 사내 ID(자동 `@lginnotek.com` suffix) + 비밀번호 인증 / 회원가입 탭(회사 이메일 + 인증코드 발송) / 사이드바·헤더 미노출 |
| **S2** | **Home** | 5개 분석 도구 진입 게이트 (CMP / UPH / MTBA Dashboard / MTBA Detail / MaxCapa Chat), 각 도구 오픈 상태(`정식` / `가오픈` / `오픈예정`) 표시, "제작: 광학 Max Capa TDR" 푸터 |
| **S3** | **CMP Dashboard** | 영역(multi) × 모델(multi: R50/R53A/R53B) × 기간(date range) 필터 → 모델별 박스 그리드(공정별 달성률) + 공정 요약 sticky 표 + 공정 선택 시 하단 CMP/UPH/Efficiency 상세, "('26.4월 4W 기준)" 메타 |
| **S4** | **UPH Dashboard** | 공장 × 공정 × 모델 × 날짜 + Trend 기간 segmented(30/90) + I-TAS 가능만 보기 toggle → 6 섹션 분석: ① UPH 요약(I-TAS) + MES 데이터로 보기 + AI 분석 의견 / ② Best Worst 동작차이 (자동선정 #1003 / #1116) / ③ UPH·편차율 Trend / ④ 주요 편차동작 / ⑤ 동작시간 증가 추세 / ⑥ 동작시간 하락 추세 |
| **S5** | **MTBA Dashboard** | **다중 패널** 구조 (패널 1개 시작, +패널추가/제거). 각 패널: 팀 + 모델 + 기간 필터 + 6구간 비교 차트(선택/1주전/2주전/지난달/2달전/지난해 막대) + 셀체크박스 연동 요약표 + 클릭 드릴다운 + 메모 입력 + 이미지 업로드(200MB, PNG/JPG/JPEG/BMP) + 메모/이미지 저장 + 이 패널 아래에 추가/이 패널 제거 |
| **S6** | **MTBA Detail View** | 패널 + 모델 선택(R50/R53A/R53B) + FOL In-line 토글 + **공정 × 설비 매트릭스** (12개 공정 컬럼: `p_*` / `pk_*` 그룹화) + 공정 셀 클릭 시 알람 상세 팝업(알람명/호기/모델명/설비세그먼트명/MTBA/생산수량 + 최근 알람 이력) + **디버그 정보 패널**(panel_id, grid_kind, streamlit_version, st_aggrid_version, response_keys, eventData, focusedCell, gridState, selected_rows, popup_key, click_marker, last_popup_marker_before, selected_row_summary, marker_rows, work_df_shape, work_df_columns_head — 전부 verbatim 표시) |
| **S7** | **MaxCapa Chat — 빈 상태** | 자연어 질문 입력 전 상태. "MaxCapa Chat(대화형 생산지표조회)" 헤더, 기본 조회=MES UPH(`uph_input_runtime_daily_model`) / "ITAS" 키워드 시 ITAS UPH(`itas_uph_result`) 분기 안내, 지원 예시 4종, 질문 입력 textarea, 질문 분석 및 실행 버튼 |
| **S8** | **MaxCapa Chat — 활성** | S7 + 질문/응답 thread (사용자 메시지 + AI 응답: 분석 추적 단계 + 실행 SQL + 결과 KPI + 차트 + 결과 표 + 분석 의견 + 후속 질문 chip), 데이터소스 자동 분기 표시 |

**고정 사이드바 7개 항목 (모든 페이지)**: login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat — 순서·라벨 절대 변경 금지.

---

## 2. 파일 인벤토리

### 디자인 시스템 / 사양

- `../DESIGN.md` (repo root) — Calm Engineering 방향 디자인 토큰
- `CLAUDE_PROJECT_INSTRUCTIONS.md` — claude.ai Project Custom Instructions
- `BATCH_PROMPT.md` — 24 시안 일괄 생성 마스터 프롬프트
- `stitch-prompts-2026-04-29.md` — 화면별 A/B/C 24 프롬프트
- `originals/01-08-*.md` — 8 페이지 원본 한국어 라벨 verbatim

### Mockup HTML (1차, Bold 컨벤션 일관)

- `_shared.css` · `_sidebar.html` — 클로드 디자인이 만든 공유 자산
- `mockup-S{1-8}-{A|B|C}.html` — 자체 완결 HTML (Pretendard + IBM Plex Mono CDN 만 외부)

### 1차 Mockup 커버리지 매트릭스

| 화면 | A (Safe) | B (Bold) | C (Wild) | Notes |
|---|---|---|---|---|
| S1 Login | ✅ | ✅ | ✅ | 3 변형 모두 있음 |
| S2 Home | ✅ | ✅ | ✅ | 3 변형 모두 있음 |
| S3 CMP Dashboard | ✅ | ✅ | ✅ | 3 변형 모두 있음 |
| S4 UPH Dashboard | ✅ | ✅ | ✅ | 3 변형 모두 있음 |
| S5 MTBA Dashboard | ✅ | ✅ | ❌ | C 변형 미생성 |
| S6 MTBA Detail View | ❌ | ✅ | ❌ | A·C 변형 미생성 |
| S7 MaxCapa Chat (빈) | ❌ | ✅ | ❌ | A·C 변형 미생성 |
| S8 MaxCapa Chat (활성) | ❌ | ✅ | ❌ | A·C 변형 미생성 |

총 14/24 생성, 10/24 미생성.

---

## 3. 화면 번호 정합성 메모 ⚠️

번들의 mockup 파일 번호는 **클로드 디자인 채팅 세션의 스킴**을 따른다 (이 README 의 표 = 캐노니컬). 초기 `stitch-prompts-2026-04-29.md` 에는 다른 매핑이 적혀있을 수 있으니, **이 README 의 매핑을 정답으로 본다**. 추후 prompts 파일 정리 필요.

---

## 4. 사용자 피드백 (1차 시안 검토 후)

### 디자인 톤
- **AI 슬롭 잔존** 지적. 다음 인스턴스 수정 필요 (S8-B 위주, 다른 시안에도 횡단 적용):
  1. 노란 `mark` 하이라이트(`#FFF6CF`) → 4번째 색상, 3색 룰 위반 → 와인 tint 또는 weight-only 강조
  2. 사각 아바타("YOU" / 메시지 SVG) → ChatGPT 클리셰 → 제거, 텍스트 라벨 + hairline 만
  3. "↳" followup glyph → 제거
  4. composer fade gradient → 단색 + 1px top border
  5. 가짜 trace_id (`7f3c…91a`) → 운영형 ID 또는 제거
  6. 4단계 분석 trace 펄러시 → 단계 압축 + 디폴트 collapsed
  7. 다중 카드 stack (trace + sql + result + answer + followup) → expander 구조

### S1 — Hybrid (B + C 합본)
- **레이아웃**: 페이지 최상단 8px 와인 strip (B) + 두 카드 24px gap (좌 폼 440px / 우 시스템 패널 360px, 둘 다 좌측 4px 와인 vertical bar)
- **우측 카드 콘텐츠**: SYSTEM STATUS 4행(BUILD / API · OK / DB · OK / 마지막 갱신) + hairline + RECENT UPDATES 4-5줄 변경 로그 + "문의: 광학 Max Capa TDR"

### S8 — 채팅 UX 재설계
- **Composer**: viewport 하단 `position: fixed`, 사이드바(240px) 위로는 안 깔림, max-width 920px
- **사이드바 트리**: MaxCapa Chat 활성 시 그 아래 인덴트 트리 자동 펼침
  - `+ 새 대화` 버튼
  - 시간 그룹 (오늘 / 어제 / 지난 7일 / 이전) — 11px uppercase eyebrow
  - 각 대화 항목 (제목 자동 생성), 활성 항목 좌측 2px 와인 마커
  - hover 시 우측에 ✕ 표시 (삭제)
  - 이모지·아이콘 X

---

## 5. 다음 단계 (대기)

1. **Revision 시안 받기** — 위 피드백을 클로드 디자인 또는 직접 작업으로 반영 (S1·hybrid 와 S8·redesign 우선, 다른 시안에 톤 횡단 적용)
2. **빈 변형 채우기** — S5-C, S6-A·C, S7-A·C, S8-A·C (10개) 또는 픽한 변형만 변종 생성
3. **화면별 픽 결정** — A/B/C 중 한 변형 픽 → 통합 디자인 토큰 CSS 1벌로 합성
4. **Streamlit `st.markdown('<style>...</style>')` 주입 패치** 작성 → 8개 페이지 일괄 적용
5. **원본 제작자 핸드오프** — 위 **Intent Contract** 충족 검증 후 전달
