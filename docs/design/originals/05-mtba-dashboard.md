# MTBA Dashboard

> Variant tag: **(추가)** · Original file: `MTBA Dashboard.html`

## Page title

`MTBA Dashboard`

## Sidebar navigation (모든 페이지 공통)

```
login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat
```

## Visible labels (Korean, 원본 그대로)

- 선택한 기간 기준으로 기간별 MTBA / 공정 통계 / 클릭 Drill-down 기반 MTBA 현황 / Alarm 차이 분석
- MTBA 분석 Reporting #1
- 팀 선택 #1
- 모델 선택 #1
- 기간 선택 #1
- Press the down arrow key to interact with the calendar and select a date. Press the escape button to close the calendar.
- Selected date range is from 2026/04/27 to 2026/04/28.
- ※ 팀 = 전체 : 모든 공정을 대상으로 조회합니다.
- ※ 그래프 구간: 선택한 기간 / 1주전 / 2주전 / 지난달 전체 / 2달전 전체 / 지난해 전체
- ※ MTBA가 0이거나 없는 설비는 자동 제외 후, 유효 설비만 평균하여 MTBA를 계산합니다.
- ※ 그래프 가시성을 위해 막대 높이는 최대 120까지만 표시되며, 라벨은 실제 MTBA 값을 표시합니다.
- ※ 그래프는 다중 선택 가능, 요약표 체크박스와 연동됩니다. 최대 5개 공정까지 섹션 2에 표시됩니다.
- 1. R50 공정별 MTBA 기간 비교
- keyboard_arrow_right
- 그래프 데이터 보기
- 선택 초기화
- ※ Shift+클릭 / Box / Lasso로 여러 공정을 선택할 수 있습니다.
- 2026-04-27 ~ 2026-04-28 공정별 요약
- 공정명 축약
- 2. MTBA 현황(2026-04-27 ~ 2026-04-28)
- ※ 알람구분 셀을 더블클릭하면 메모/이미지 팝업이 열립니다.
- 4. 메모 / 이미지 업로드
- 메모 입력 #1
- 이미지 업로드 #1
- Drag and drop file here
- Limit 200MB per file • PNG, JPG, JPEG, BMP
- Browse files
- 메모/이미지 저장 #1
- 이 패널 아래에 추가 #1
- 이 패널 제거 #1


## Existing custom CSS (user-authored, 발견된 경우만)

(없음 — Streamlit 기본 스타일만 사용)


## Notes for Claude Design

- 위 visible labels 의 한국어 문자열을 **그대로** 시안에 사용할 것 (의역·번역 금지)

- 사이드바 네비게이션 7개 항목과 순서·라벨 유지

- 기존 custom CSS 가 있어도 디자인 토큰은 `DESIGN.md` 기준을 따를 것 (참고만)
