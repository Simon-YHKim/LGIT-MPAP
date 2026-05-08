---
type: concept
tags: [design-system, vitals, lg-innotek, ui]
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
  - "[[entities/Max-Capa-TDR]]"
---

# Vitals Design System

> LG Innotek 광학솔루션 사업부 [[entities/Max-Capa-TDR]] 의
> 설비 생산성 분석 플랫폼 "Vitals" 의 디자인 시스템.
> 캐치프레이즈: **"공정의 호흡을 데이터로 듣다."**

## 핵심 원칙

| 원칙 | 구현 |
|---|---|
| **Rectangles only** | `border-radius: 0` 전역. 예외: status dot 50% (functional circle), 의식적 pill 999px |
| **Wine identity** | `--primary: #A50034` — 모든 페이지 상단 6px strip (`render_top_strip()`) |
| **Section rhythm** | `render_sub_head(title, meta)` — 좌 4px wine bar + h3 + 우 메타 |
| **No emoji UI** | 🌐 / ● / ▸ / ✕ 같은 emoji → SVG (Pretendard fallback OK) |
| **No multi-color** | UI 색상 3개 이내: `--primary`, `--ink-body`, `--page-bg` |
| **No bouncy easing** | `120ms ~ 180ms` linear / ease-out |
| **Vitals tokens only** | 33개 토큰 외 hex 사용 금지 |

## 토큰 33개

### Light theme
- Wine: `#A50034`, `#7E0027`, `#F8E5EC`
- Surface: `#F7F8FA`, `#FFFFFF`, `#F1F3F5`, `#E5E7EB`, `#FAFAFA`, `#CBD0D6`
- Ink: `#1F2430`, `#6B7280`, `#9CA3AF`
- Status: `#1F8B4C` / `#B57F1B` / `#B23A48` (good/warn/bad)
- Status tints: `#E6F4EA` / `#FAF1DD` / `#FDECEF`
- Neutral: `#111111`

### Dark theme
- Surface: `#0E1117`, `#161B22`, `#1A1F2A`, `#2A2F3A`, `#3A4051`
- Status base: `#2EA85C`, `#D69E2E`, `#E5495A`
- Status tints: `#0F2418`, `#2A2210`, `#2E1318`
- Primary tint: `#2A1218`

## 컴포넌트 (`ui/vitals/components.py`)

| Primitive | 사용처 |
|---|---|
| `render_top_strip()` | 9 페이지 + login_ui (11) |
| `render_sub_head(title, meta)` | 5 페이지 (15) |
| `render_csv_export(df, ...)` | 5_Alarm + 1_CMP + 9_Admin (3) |
| `render_toast(msg, kind=)` | 4 페이지 (11) |
| `render_modal_static` | 0 (future — 현재 모든 모달 `@st.dialog` 인터랙티브) |
| `render_nav_card_grid` | 0 (future — Streamlit `render_card_button` 가 auth 흐름 보호) |
| `render_sidebar_tree` | 0 (Streamlit native 사이드바 사용) |
| `render_filter_block` | 0 (페이지별 필터 UI 박혀 있음) |

## 점수 측정

`measure_design_integration.py` — 페이지별 100점 만점.
6 차원: tokens(30), font(20), theme(10), hero(10), components(15), status(15).

현재 9 페이지 평균: **97.8 / 100**.
