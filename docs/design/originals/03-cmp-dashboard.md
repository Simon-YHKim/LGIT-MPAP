# CMP Dashboard

> Variant tag: **S3** · Original file: `CMP Dashboard.html`

## Page title

`Streamlit`

## Sidebar navigation (모든 페이지 공통)

```
login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat
```

## Visible labels (Korean, 원본 그대로)

- CMP 달성률 Dashboard
- 영역
- Gumi Campus 1 Area
- Gumi Campus 3 Area
- Gumi Campus 4 Area
- 모델
- R50
- R53A
- R53B
- 기간
- Press the down arrow key to interact with the calendar and select a date. Press the escape button to close the calendar.
- Selected date range is from 2026/01/28 to 2026/04/28.
- ('26.4월 4W 기준)
- 아래 드롭다운에서 공정을 선택하면 동일 기간 CMP / UPH / Efficiency 상세가 아래에 표시됩니다.
- 상세 조회 공정 선택
- 공정
- 6side AVI Cap(Inline)
- APS Test
- Baffle Attach
- Bracket Attach
- Bracket Fill
- Cosmetic AVI Cap(Inline)
- DCR Test
- Driver IC Filling
- Dust Trap
- Enclosure Attach
- FPC Bonding
- FPCB bonding - Stiffener attach
- Flip Chip Bonding
- Glue Locking
- Gopher test
- IRCF Attach
- Iguana
- Jet soldering &amp; Terminal sealing 1st
- Jet soldering &amp; Terminal sealing 2nd
- Laser Marking
- Lens AA
- Lens AA_VR
- Module AA
- Module Sealing
- Neck Reinforcement
- Particle Remove
- Pismo Flex bending
- Pismo interconnection
- Pre Focus
- Sensor Stiffener Attach
- Sensor underfill
- Shield Can Reinforcement
- Shield can attach
- Single AA
- Stiffener SF
- Tape attach
- Tape detach
- Terminal Connection
- Top &amp; Bottom Neck
- Up Down Dark
- VCM Sealing
- VCM attach
- Z sensor Calibration
- From
- Selected date is 2026/04/07. Select the second date.
- To
- Selected date is 2026/04/28. Select the second date.
- 조회 시작
- 2026-04-07
- 조회 종료
- 2026-04-28
- 테이블 CSV 다운로드


## Existing custom CSS (user-authored, 발견된 경우만)

```css
@font-face {
    font-family: 'LGLocal';
    src: local('LG Smart_H'), local('LGSmHaTR'), local('LG Smart');
    font-display: swap;
}
@font-face {
    font-family: 'ArialLocal';
    src: local('Arial Narrow'), local('Arial'), local('ARIALN');
    font-display: swap;
}

:root {
    --bg: #fcfdff;
    --surface: #ffffff;
    --surface-soft: #f8f9fb;
    --surface-muted: #eff2f6;
    --line: #d7dbe2;
    --line-strong: #b8bec8;
    --ink: #1f2430;
    --muted: #6b7280;
    --accent-rose: #d98aa2;
    --accent-blue: #6f8fbd;
    --accent-violet: #8c84b8;
    --accent-navy: #384455;
    --good: #dfe8f6;
    --mid: #efe5cc;
    --bad: #f2d7df;
    --shadow: 0 8px 24px rgba(31, 36, 48, 0.05);
    --radius: 14px;
}

/* 전체 UI 글꼴
   - 영문/숫자: ArialLocal 우선
   - 한글: Arial에 glyph가 없으므로 LGLocal로 fallback */
html, body, [class*='css'], .stApp, .stMarkdown, .stText, .stSelectbox,
.stMultiSelect, .stDateInput, .stButton, .stDataFrame, .stMetric,
label, input, textarea, select, button, table, th, td, div, span, p, li {
    font-family: 'ArialLocal', 'LGLocal', 'Malgun Gothic', sans-serif !important;
}

.stApp {
    background: linear-gradient(180deg, #fcfdff 0%, #f7f9fc 100%);
    color: var(--ink);
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2.2rem;
    max-width: 1880px;
}
h1, h2, h3, h4, h5, h6, body, p, label, div, span {
    color: var(--ink);
}
.stApp h1 {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.4rem;
    letter-spacing: -0.02em;
}
.stApp h2 {
    font-size: 1.25rem;
    font-weight: 800;
    margin-top: 0.2rem;
    margin-bottom: 0.8rem;
    letter-spacing: -0.01em;
}
.page-shell {
    background: var(--surface);
    border: 1px solid var(--line);
    border-top: 3px solid var(--accent-navy);
    border-radius: 16px;
    box-shadow: var(--shadow);
    padding: 18px 22px 16px 22px;
    margin-bottom: 18px;
}
.page-eyebrow {
    font-size: 12px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}
.page-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
}
.section-wrap {
    margin-top: 14px;
    margin-bottom: 18px;
}
.section-heading {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}
.section-heading .bar {
    width: 6px;
    height: 18px;
    border-radius: 4px;
    background: linear-gradient(180deg, var(--accent-rose), var(--accent-violet));
    box-shadow: 0 0 0 1px rgba(217,138,162,0.12);
}
.section-heading .title {
    font-size: 22px;
    font-weight: 800;
    color: var(--ink);
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.section-heading .desc {
    color: var(--muted);
    font-size: 12px;
    margin-left: 4px;
}

.filter-box, .filter-panel {
    padding: 14px 16px 10px 16px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.92);
    margin-bottom: 14px;
}
.filter-panel h3, .filter-box h3 { margin: 0 0 8px 0 !important; }

.stMultiSelect [data-baseweb='tag'],
div[data-baseweb='tag'],
span[data-baseweb='tag'] {
    background: linear-gradient(180deg, #ffffff 0%, #f8f9fb 100%) !important;
    border: 1px solid var(--line) !important;
    color: var(--ink) !important;
    border-radius: 999px !important;
    box-shadow: 0 1px 3px rgba(31, 36, 48, 0.04) !important;
    padding-left: 2px !important;
    padding-right: 2px !important;
}
.stSelectbox [data-baseweb='select'] > div,
.stMultiSelect [data-baseweb='select'] > div,
.stDateInput > div > div,
.stTextInput > div > div > input {
    background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    min-height: 42px !important;
    box-shadow: 0 2px 8px rgba(31, 36, 48, 0.04) !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.stSelectbox [data-baseweb='select'] > div:hover,
.stMultiSelect [data-baseweb='select'] > div:hover,
.stDateInput > div > div:hover {
    border-color: var(--line-strong) !important;
    background: #ffffff !important;
}
.stSelectbox [data-baseweb='select']:focus-within > div,
.stMultiSelect [data-baseweb='select']:focus-within > div,
.stDateInput > div:focus-within > div {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(111, 143, 189, 0.12) !important;
    background: #ffffff !important;
}
.stSelectbox label p,
.stMultiSelect label p,
.stDateInput label p {
    font-weight: 700 !important;
    color: var(--ink) !important;
    letter-spacing: -0.01em;
}
div[data-baseweb='popover'] {
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid var(--line) !important;
    box-shadow: 0 14px 32px rgba(31, 36, 48, 0.10) !important;
    background: #ffffff !important;
}
div[role='listbox'] {
    padding: 6px !important;
    background: #ffffff !important;
}
div[role='option'] {
    border-radius: 10px !important;
    margin: 2px 4px !important;
    padding-top: 8px !important;
    padding-bottom: 8px !important;
}
div[role='option'][aria-selected='true'] {
    background: #edf3fb !important;
    color: var(--ink) !important;
    font-weight: 700 !important;
}
div[role='option']:hover {
    background: #f5f7fb !important;
}

.block-wrap {
    background: var(--surface);
    border: 1px solid var(--line);
    border-top: 3px solid var(--accent-navy);
    border-radius: 16px;
    box-shadow: var(--shadow);
    padding: 16px 16px 14px 16px;
    margin-top: 10px;
    margin-bottom: 22px;
}
.model-box {
    background: linear-gradient(180deg, #f9fafc 0%, #eef2f7 100%);
    border: 1px solid var(--line);
    border-radius: 14px;
    min-height: 850px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font-weight: 800;
    font-size: 19px;
    color: var(--ink);
    padding: 20px 14px;
    white-space: pre-line;
    letter-spacing: -0.01em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.95);
}

.summary-table, .worst-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
    table-layout: fixed;
    overflow: hidden;
    border-radius: 12px;
    border: 1px solid var(--line);
}
.summary-table th, .summary-table td,
.worst-table th, .worst-table td {
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    text-align: center;
    padding: 7px 4px;
    vertical-align: middle;
    word-wrap: break-word;
    background: #fff;
}
.summary-table th:last-child, .summary-table td:last-child,
.worst-table th:last-child, .worst-table td:last-child {
    border-right: 0;
}
.summary-table tr:last-child td,
.worst-table tr:last-child td {
    border-bottom: 0;
}
.summary-table thead th,
.worst-table thead th {
    background: linear-gradient(180deg, #f8f9fb 0%, #eef2f6 100%);
    font-weight: 800;
    color: var(--ink);
}
.table-title {
    font-weight: 800;
    margin: 0 0 8px 0;
    font-size: 15px;
    color: var(--ink);
    letter-spacing: -0.01em;
}
.section-space { height: 10px; }
.small-note { color: var(--muted); font-size: 11px; }
div[data-testid='stCaptionContainer'] p { color: var(--muted); }

div[data-testid='stMetric'] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 10px 12px;
    box-shadow: var(--shadow);
}

.stDownloadButton button,
.stButton button {
    border-radius: 10px !important;
    border: 1px solid var(--line) !important;
    background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%) !important;
    color: var(--ink) !important;
    font-weight: 700 !important;
}

.st-frozen-wrap {
    max-height: 700px;
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: #ffffff;
}
table.sticky-cmp {
    border-collapse: separate;
    border-spacing: 0;
    width: max-content;
    min-width: 100%;
    font-size: 13px;
}
table.sticky-cmp th,
table.sticky-cmp td {
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    padding: 6px 10px;
    white-space: nowrap;
    text-align: center;
}
table.sticky-cmp thead th {
    position: sticky;
    top: 0;
    z-index: 20;
    background: linear-gradient(180deg, #f8f9fb 0%, #eef2f6 100%);
    font-weight: 800;
}
table.sticky-cmp th:first-child,
table.sticky-cmp td:first-child {
    border-left: 1px solid var(--line);
}
table.sticky-cmp thead tr:first-child th {
    border-top: 1px solid var(--line);
}
.sticky-col-1 { position: sticky; left: 0px; z-index: 12; background: #ffffff; }
.sticky-col-2 { position: sticky; left: 90px; z-index: 12; background: #ffffff; }
.sticky-col-3 { position: sticky; left: 210px; z-index: 12; background: #ffffff; }
table.sticky-cmp thead .sticky-col-1,
table.sticky-cmp thead .sticky-col-2,
table.sticky-cmp thead .sticky-col-3 {
    z-index: 25;
    background: linear-gradient(180deg, #f8f9fb 0%, #eef2f6 100%);
}
.col-model { min-width: 90px; max-width: 90px; width: 90px; }
.col-factory { min-width: 120px; max-width: 120px; }
.col-process { min-width: 220px; max-width: 220px; text-align: left !important; }
.col-date { min-width: 90px; max-width: 90px; }
.left-text { text-align: left !important; }
```


## Notes for Claude Design

- 위 visible labels 의 한국어 문자열을 **그대로** 시안에 사용할 것 (의역·번역 금지)

- 사이드바 네비게이션 7개 항목과 순서·라벨 유지

- 기존 custom CSS 가 있어도 디자인 토큰은 `DESIGN.md` 기준을 따를 것 (참고만)
