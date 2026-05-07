# STAGE 2 Release Notes — LG Innotek Vitals

> 다음 사람이 이 코드베이스를 인수받을 때, 또는 처음 deploy 할 때
> 1장으로 보는 변경 요약. **개발자 입장의 호출 방식 / SQL / session
> state 는 0% 변경**, 시각만 정렬됐다.

본 문서: `docs/STAGE2_RELEASE_NOTES.md`
관련 문서:
- `streamlit-app/docs/HANDOFF.md` — 백엔드 인수 인계
- `docs/design/preview-streamlit-clone.html` + `streamlit-clone.css` — 시각 시안
- `streamlit-app/scripts/preflight.sh` — deploy 전 1-shot 점검

---

## 0. TL;DR — 무엇이 바뀌었나

| 영역 | 변경 |
|---|---|
| **SQL 쿼리 / 함수 시그니처 / session_state 키** | **0개 변경** (AST diff 검증) |
| **개발자 코드 작성 방식** | 변경 없음 — 새 페이지 추가 / SQL 수정 / 디버깅 모두 동일 |
| **DB 연결 방법** | `tracking.py` 만 내부 pooling 으로 (API 동일) |
| **DB 패스워드 literal fallback** | 코드에서 제거 — `secrets.toml` 또는 env 필요 |
| **시각 (모든 페이지 상단)** | 와인 6px identity strip + 좌측 wine 4px sub-head bar |
| **버튼·카드·입력** | 직사각형으로 통일 (border-radius 0) |
| **YouTube iframe / CDN 폰트** | 제거 (폐쇄망 compliance) |
| **XSS 1건** | 8_Patch_Note 의 stored 공격 차단 (html.escape) |

---

## 1. STAGE 1 — 안전성 + 인프라 (8 commits, `19f47e3` ~ `bf7a4a6`)

### 1.1 보안 fix (P0)
- **`19f47e3`** — `8_Patch_Note.py` 의 DB 값 (tag/title/created_by) 4개 사이트에 `html.escape()` 적용. 이전엔 `st.markdown(unsafe_allow_html=True)` 에 raw 흘러들어가 stored XSS 가능.
- **`85b1572`** — 7개 파일에서 하드코딩 DB 패스워드 `!Q2w3e4r5t` literal fallback 제거. `secrets.toml` 또는 env 필수. **deploy 머신에서 secrets.toml 또는 env 가 미설정이면 RuntimeError 로 즉시 실패** (조용히 hardcoded value 로 작동하는 위험 제거).

### 1.2 Preview HTML 하드버그 fix (P1)
- **`3d4ec6e`** — preview HTML 의 3가지 표면적 버그:
  - `lines 2635-2670` orphan modal body — `alarm-detail-modal` backdrop 밖의 중복 `vit-modal__body+foot` 가 모든 페이지 본문에 렌더링되던 버그. 삭제.
  - `line 113` YouTube iframe — 폐쇄망 차단 위험. 삭제.
  - `team-procs-modal` HTML 자체 부재 (button + JS 만 존재했음) → 누락 HTML 추가.

### 1.3 STAGE 2 인프라 (P1)
- **`3e5afb6`** — 4개 검증 스크립트 + AST baseline JSON:
  - `verify_backend_freeze.py` — 함수 시그니처 / SQL / session keys / imports 의 AST snapshot diff. STAGE 2 가 backend 를 건드리지 못하도록 enforcement gate.
  - `verify_no_external.py` — 외부 CDN URL 검출 (YouTube/Google Fonts/jsdelivr/cdnjs/openai/anthropic).
  - `smoke_compile.sh` — `python -m py_compile` 49 파일 sweep.
  - `backend_freeze_baseline.json` — 37 파일 / 578 fns / 223 SQL / 87 session keys 스냅샷.
  - `0_Home.py` 의 inject_css 안 Pretendard / Google Fonts CDN @import 제거.

### 1.4 성능 (P1)
- **`f85fe71`** — `tracking.py` 의 `psycopg2.connect()` 직접 호출 → SQLAlchemy `QueuePool` (size=5, max_overflow=10) 경유로 변경. **`get_conn()` API 동일하므로 호출자 코드 변경 없음**. 이전에 매 analytics call 마다 새 connection → 폐쇄망 PG `max_connections` 고갈 위험 해소.

### 1.5 디자인 토큰 정렬 (P2)
- **`b2d7ecd`** — `theme.py` (`--radius:8/12`) vs `streamlit-clone.css` (`--sc-radius:8/12/999`) 의 충돌을 모두 0 으로 통일 (직사각형 원칙). dark mode 토큰 (`--card-bg / --soft / --border / --ink-*`) hex drift 8건도 `theme.py` 를 source of truth 로 일치.

### 1.6 신규 7+1 STAGE 2 primitives (P2)
- **`0522f75`** — `streamlit-app/ui/vitals/components.py` 에 추가:
  - `render_top_strip()` — 6px wine identity bar
  - `render_sub_head(title, meta)` — 좌 4px wine + h3 + meta
  - `render_nav_card_grid(cards)` — 3-col nav 카드 grid
  - `render_modal_static(...)` — 정적 모달 (인터랙티브 모달은 `st.dialog` 권장)
  - `render_toast(msg, kind=)` — `st.toast` wrap
  - `render_csv_export(df, ...)` — `st.download_button` wrap (UTF-8 BOM 포함)
  - `render_sidebar_tree(groups, active_key)` — Home/MTBA tree
  - `render_filter_block(on_apply, on_reset)` — apply/reset row
  - 모두 `_inject_components_css_once()` sentinel 로 페이지당 1회만 CSS 주입 (이전 매 rerun 마다 80KB+ 중복 주입 버그 해소).
  - 동일 commit 에서 emoji 위반 (🌐 / ●) 4사이트 → SVG 로 교체. `theme.py` 의 `has-vit-chat` body class 가 chat 페이지를 떠난 후에도 phantom right-pad 남기는 버그 해소.

### 1.7 Preview HTML 인터랙션 21건 fix (P3)
- **`bf7a4a6`** — `preview-streamlit-clone.html` 의 broken 인터랙션 정리:
  - 로그인 form validation (빈 필드 → 에러 슬롯 노출)
  - 회원가입 step1 → step2 transition + 5:00 timer + 재발송/이메일수정
  - chat send (Enter + 버튼) + chat history container + clear
  - alarm timeline row 클릭 → alarm-detail-modal 열기
  - patch body / edit / delete UI
  - dead `#sc-theme-toggle` 참조 제거 + `prefers-color-scheme` 첫로드 적용
  - 글로벌 modal focus trap (Tab cycling)

> 단, 위 21건은 **preview HTML 의 인터랙션** 수정. Streamlit 페이지 자체의 인터랙션은 처음부터 native 위젯 기반으로 정상 작동 중.

---

## 2. STAGE 2 — 9 페이지 시각 정렬 (10 commits, `8e74e6d` ~ `9983dc4`)

각 페이지가 `render_top_strip()` + (해당 시) `render_sub_head()` 를 채택하고, 인라인 `border-radius` 를 제거해 `preview-streamlit-clone.html` 의 sec-* 섹션과 시각 정렬.

| Commit | 페이지 | 변경 핵심 |
|---|---|---|
| `8e74e6d` | `8_Patch_Note.py` | top_strip + 2× sub_head + sc-mono detail meta (date·author·tag-pill 한 줄) |
| `175fdbf` | `5_Alarm_Action_List.py` | top_strip + 3× sub_head + gradient `.main-title` 제거 |
| `1aae4e0` | `1_CMP_Dashboard.py` | top_strip + section-heading bar 직각 + eyebrow dot 직각 |
| `29807fa` | `2_UPH_Dashboard.py` | top_strip + page-head eyebrow + 6× sub_head |
| `b44a69b` | `0_Home.py` | top_strip × 2 (Case0 default, Case1 Best/Worst) |
| `ddbad3d` | `3_MTBA_Dashboard.py` + `4_MTBA_Detail_View.py` | top_strip × 2 |
| `e845dcc` | `6_MaxCapa_Chat.py` | top_strip + 5사이트 radius 제거 |
| `98307eb` | `9_Admin_Analytics.py` | top_strip + 4× sub_head + page-head shadow/radius 제거 + metric/dataframe radius 제거 |
| `2aebd9b` | `ui/login_ui/styles.py` + `layout.py` | login 패널 7사이트 radius 제거 (status dot 만 유지 — 기능적 원형) |
| `9983dc4` | `ui/login_ui/layout.py` | `[바로가기]` 버튼의 `st.switch_page` 타겟 `8_Board.py` → `8_Patch_Note.py` rename 누락 fix |

### 2.1 누적 효과
- 모든 9 페이지 + login 모듈에 와인 6px identity strip 일관 적용
- 모든 카드 / 입력 / 버튼 / 패널 직사각형 (status dot 만 원형 유지)
- 페이지간 visual rhythm: 와인 6px → flat 페이지 헤딩 → 좌측 wine bar sub-head → 직사각형 콘텐츠 — 9 페이지 전부 동일

### 2.2 STAGE 2 가 NOT 한 것 (의식적 deferred)
| 항목 | 이유 |
|---|---|
| 페이지 레이아웃 전체 재구성 (KPI 타일 / 차트 / 테이블의 preview 와 1:1 일치) | preview 의 sc-soft-card / sc-board-row / sc-pill / vit-kpi-grid 등 클래스 구조를 페이지에 1:1 매핑하면 Streamlit native 위젯 (st.metric / st.dataframe / st.columns) 와 충돌. 더 큰 작업이 필요. |
| 차트 SVG 의 하드코딩 hex (~20 사이트) → CSS var 토큰화 | dark mode 차트 색이 안 바뀌는 한계. 페이지별 chart 코드 재구조화 필요. |
| Modal 4-layer hide → `.is-open` only 일원화 | 현재 함께 작동 중, 위험 없음. `render_modal_static` primitive 가 이미 `.is-open` only — 자연 마이그레이션 시 자동 정리. |
| `secrets.toml` / `setting.ini` 의 plain DB 패스워드 | 사용자 명시 정책 (폐쇄망 의식적 commit). 정책 결정 사항. |

---

## 3. Deploy 절차

### 3.1 사전 점검
```bash
cd /path/to/LGIT-MPAP
bash streamlit-app/scripts/preflight.sh
```

PASS 만 있고 FAIL 0 이면 ✓ deploy OK.

### 3.2 환경 변수 설정 (선택 — secrets.toml 이 있으면 생략 가능)
```bash
export DB_URL="postgresql+psycopg2://postgres:<pwd>@localhost:5432/MTBA"
export ITAS_DB_PASSWORD="<pwd>"
export CMP_DB_PASSWORD="<pwd>"
```

또는 `streamlit-app/.streamlit/secrets.toml` 에 저장:
```toml
DB_URL = "postgresql+psycopg2://postgres:<pwd>@localhost:5432/MTBA"
[db]
host = "localhost"
name = "auth"
user = "postgres"
password = "<pwd>"
port = 5432
[cookie]
password = "<random_secret>"
```

### 3.3 실행
```bash
cd streamlit-app
streamlit run login.py --server.port 8501 --server.address 0.0.0.0
```

### 3.4 페이지별 시각 확인 포인트

| 페이지 | 확인 |
|---|---|
| login.py | 와인 6px strip 의식적 미적용. `[바로가기]` 클릭 → Patch Note 진입 (rename fix 적용됨) |
| 0_Home | 와인 6px strip + KPI / Best/Worst 카드 |
| 1_CMP | 와인 6px strip + section-heading wine bar |
| 2_UPH | 와인 6px strip + 6 섹션 모두 좌측 wine bar |
| 3_MTBA / 4_Detail | 와인 6px strip + page-banner / page-hero |
| 5_Alarm | 와인 6px strip + flat title (gradient 제거) + 3 sub-head |
| 6_Chat | 와인 6px strip + 모든 카드 직사각형 |
| 8_Patch_Note | 와인 6px strip + 목록/상세 sub-head + sc-mono meta |
| 9_Admin | 와인 6px strip + 4 sub-head + 메트릭/테이블 직사각형 |

---

## 4. 다음 세션 / 다음 사람을 위한 가이드

### 4.1 새 페이지 추가
```python
import streamlit as st
from ui.vitals import apply_vitals_theme
from ui.analytics import inject_tracker

st.set_page_config(page_title="My Page", layout="wide")
apply_vitals_theme()
inject_tracker(page_name="my_page", page_path="pages/N_My_Page.py")

# 시각 정렬:
from ui.vitals.components import render_top_strip, render_sub_head
render_top_strip()
st.markdown('<h1 class="vit-page-head">My Page · 한글 부제</h1>', unsafe_allow_html=True)
render_sub_head("섹션 1", "메타 텍스트")
# ... 콘텐츠 ...
```

### 4.2 새 SQL / session key / 함수 추가
- 추가는 자유 — `verify_backend_freeze.py` 는 **삭제·시그니처 변경**만 detect.
- 추가 후 baseline 갱신: `python streamlit-app/scripts/verify_backend_freeze.py --emit-baseline`.

### 4.3 외부 URL 사용이 정말 필요한 경우
`scripts/verify_no_external.py` 의 `ALLOW_SUBSTRINGS` 에 명시 추가. PR review 시 폐쇄망 정책 검토 권장.

### 4.4 Streamlit 버전 업그레이드 시
`streamlit-clone.css` 의 32개 `data-testid` selector 가 새 버전 DOM 과 일치하는지 확인. 깨지면 `theme.py` 의 selector 도 같이 업데이트.

---

## 5. Known issues (현재 진행 상태)

| 이슈 | 위치 | 상태 |
|---|---|---|
| 차트 SVG 하드코딩 hex → dark mode 차트 색 미적용 | `pages/3_MTBA_Dashboard.py`, `pages/2_UPH_Dashboard.py` 등 | deferred |
| `render_chat_panel` 의 inline `<script>` 가 `st.markdown` 에 의해 stripped — JS resize 핸들러 dead code | `streamlit-app/ui/vitals/components.py:366-413` | deferred (chat 패널은 컴포넌트 자체 native 위젯으로 재작성 권장) |
| `4_MTBA_Detail_View` design score 81.1 — 다른 페이지 평균 대비 낮음 | tokens(30) 14.1 = 20개 hex literal 잔존 | deferred |
| `fonts.py` 가 1.7MB woff2 base64 를 모듈 메모리 상주 + 매 페이지 inject | `streamlit-app/ui/vitals/fonts.py:29` | deferred (폐쇄망 / 자체 호스팅 환경에선 OK) |

---

_Generated as part of STAGE 2 closure.
Branch `claude/streamlit-vitals-Sry57`, base `streamlit-source`._
