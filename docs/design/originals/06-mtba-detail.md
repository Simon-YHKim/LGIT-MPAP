# MTBA Detail View

> Variant tag: **S4** · Original file: `MTBA Detail View.html`

## Page title

`MTBA Detail View`

## Sidebar navigation (모든 페이지 공통)

```
login / Home / CMP Dashboard / UPH Dashboard / MTBA Dashboard / MTBA Detail View / MaxCapa Chat
```

## Visible labels (Korean, 원본 그대로)

- 실행 복구 안정판 · Comment 이력 포함
- 페이지 상태 초기화
- 패널 1개 추가
- 모델 선택 #1
- FOL In-line #1
- 조회 패널 #1
- 공정 셀 클릭 시 해당 공정/알람 상세 팝업이 열립니다.
- keyboard_arrow_right
- 디버그 정보 (패널 1)
- panel_id
- grid_kind
- "fol"
- streamlit_version
- "1.55.0"
- st_aggrid_version
- "unknown"
- response_keys
- event_data
- eventData
- focusedCell
- focused_cell
- gridState
- grid_state
- selected_rows
- popup_key
- click_marker
- last_popup_marker_before
- selected_row_summary
- 알람명
- 호기
- 모델명
- 설비세그먼트명
- marker_rows
- work_df_shape
- work_df_columns_head
- "모델명"
- "설비세그먼트명"
- "MTBA"
- "생산수량"
- "p_Dust Trap"
- "pk_Dust Trap"
- "p_Flip Chip Bonding"
- "pk_Flip Chip Bonding"
- "p_HFE Clean"
- "pk_HFE Clean"
- "p_HTCC Cleaning"
- "pk_HTCC Cleaning"
- "p_IRCF Attach"
- "pk_IRCF Attach"
- "p_IRCF Oven"
- "pk_IRCF Oven"
- "p_Image Test"
- "pk_Image Test"
- "p_Plasma Cleaning"
- "pk_Plasma Cleaning"
- "p_Pre Focus"
- "pk_Pre Focus"
- "p_Pre Focus Oven"
- "pk_Pre Focus Oven"
- "p_Sensor UF Oven"
- "pk_Sensor UF Oven"
- "p_Sensor underfill"
- "pk_Sensor underfill"
- "p_Single AA"
- "pk_Single AA"
- session_open_popup
- session_selected_row


## Existing custom CSS (user-authored, 발견된 경우만)

```css
:root { --primary:#6D1028; --primary2:#8B1E3F; --bg:#FAF6F8; --card:#FFFDFE; --rose:#F7E7EC; --mist:#F6F1F4; --border:#E8D8DE; --text:#3D2430; --sub:#7A5A67; }
.stApp { background: linear-gradient(180deg,#fffdfd 0%, var(--bg) 100%); color: var(--text); }
.block-container { padding-top: 1rem; padding-bottom: 1.2rem; }
.main-title { background:linear-gradient(135deg,var(--primary) 0%, var(--primary2) 100%); color:#fff; padding:18px 22px; border-radius:22px; box-shadow:0 10px 24px rgba(109,16,40,.16); margin-bottom:14px; }
.main-title h1 { margin:0; font-size:30px; line-height:1.1; }
.main-title p { margin:8px 0 0 0; font-size:13px; color:rgba(255,255,255,.92); }
.soft-card,.query-card { border:1px solid var(--border); border-radius:24px; padding:14px 16px; background:rgba(255,255,255,.95); box-shadow:0 8px 18px rgba(109,16,40,.05); margin-bottom:14px; }
.section-title { font-size:13px; font-weight:800; color:var(--primary); margin:0 0 8px 0; }
.query-subtitle { font-size:11px; font-weight:800; color:var(--sub); margin:0 0 4px 0; }
.tight-under-model { margin-top:-8px; margin-bottom:-4px; }
.toolbar-box { border:1px solid var(--border); border-radius:18px; padding:10px 12px; background:linear-gradient(180deg,#fff,var(--mist)); margin-top:8px; margin-bottom:12px; box-shadow:0 6px 16px rgba(109,16,40,.05); }
.small-muted { color:var(--sub); font-size:12px; }
.info-chip { display:inline-block; padding:6px 12px; border-radius:999px; background:var(--rose); color:var(--primary); font-size:12px; font-weight:800; margin-right:6px; margin-bottom:6px; border:1px solid var(--border); }
.history-card { border:1px solid var(--border); border-radius:18px; padding:10px 12px; background:#fff; margin-top:10px; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stDateInput > div > div { border-radius:16px !important; border:1px solid var(--border) !important; box-shadow:none !important; background:#fff !important; }
.stButton > button { border-radius:16px !important; border:1px solid var(--border) !important; min-height:2.6rem; }
button[kind="primary"] { background:linear-gradient(135deg,var(--primary) 0%, var(--primary2) 100%) !important; color:#fff !important; box-shadow:0 8px 16px rgba(109,16,40,.15) !important; }
.stButton > button:hover { border-color:var(--primary2) !important; color:var(--primary2) !important; }
```


## Notes for Claude Design

- 위 visible labels 의 한국어 문자열을 **그대로** 시안에 사용할 것 (의역·번역 금지)

- 사이드바 네비게이션 7개 항목과 순서·라벨 유지

- 기존 custom CSS 가 있어도 디자인 토큰은 `DESIGN.md` 기준을 따를 것 (참고만)
