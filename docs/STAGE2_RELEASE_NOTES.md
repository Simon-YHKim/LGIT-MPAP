# STAGE 2 Release Notes — LG Innotek Vitals

> 다음 사람이 이 코드베이스를 인수받을 때, 또는 처음 deploy 할 때
> 1장으로 보는 변경 요약. **백엔드 (DB / 인증 / 함수 / SQL / session
> state / 연결 방식) 0% 변경**, 표현 layer 만 정렬됐다.

본 문서: `docs/STAGE2_RELEASE_NOTES.md`
관련 문서:
- `streamlit-app/docs/HANDOFF.md` — 백엔드 인수 인계
- `docs/design/preview-streamlit-clone.html` + `streamlit-clone.css` — 시각 시안
- `streamlit-app/scripts/preflight.sh` — deploy 전 1-shot 점검

---

## 0. TL;DR — 무엇이 바뀌었나

| 영역 | 변경 |
|---|---|
| **SQL 쿼리 / 함수 시그니처 / session_state 키 / import** | **0개 변경** (AST diff 검증) |
| **DB 연결 방법** (`get_conn` 매 호출 fresh psycopg2.connect) | **변경 없음** — 회사 방식 그대로 |
| **DB 패스워드 fallback** (`!Q2w3e4r5t`) | **변경 없음** — 폐쇄망 운영성 보존 |
| **인증 흐름** (`login.py`, `auth_guard.py`) | **0 변경** |
| **PG dialect** (`NOW()`) | **변경 없음** |
| **CDN @import** (`Pretendard / IBM Plex Mono`) | **변경 없음** — 외부망 fallback 보존 |
| **개발자 코드 작성 방식** | 변경 없음 — 새 페이지 추가 / SQL 수정 / 디버깅 모두 동일 |
| **시각 (모든 페이지 상단)** | 와인 6px identity strip + 좌측 wine 4px sub-head bar |
| **버튼·카드·입력** | 직사각형으로 통일 (border-radius 0) |
| **off-Vitals hex** | Vitals 토큰으로 매핑 (1_CMP, 4_Detail) |
| **preview HTML** | YouTube iframe 제거 / orphan modal 제거 / 21건 인터랙션 fix |
| **emoji** (🌐 / ●) | SVG 로 교체 |
| **XSS 1건** | 8_Patch_Note 의 stored 공격 차단 (html.escape) — 표현 layer |

이전 엔지니어가 의식적으로 잡은 "데이터 호출 앞단" (DB 연결, 인증, SQL
dialect, 패스워드 fallback, CDN fallback) 은 한 줄도 변경하지 않음.
변경은 모두 **렌더링 / 시각 / preview HTML 시안** 영역에 한정.

---

## 1. STAGE 1 — 안전성 + 인프라 (8 commits, `19f47e3` ~ `bf7a4a6`)

### 1.1 보안 fix (P0)
- **`19f47e3`** — `8_Patch_Note.py` 의 DB 값 (tag/title/created_by) 4개 사이트에 `html.escape()` 적용. 이전엔 `st.markdown(unsafe_allow_html=True)` 에 raw 흘러들어가 stored XSS 가능했음. **표현 layer 변경 (DB → HTML 렌더 직전 escape) — 회사 방식 그대로**.

### 1.2 Preview HTML 하드버그 fix (P1)
- **`3d4ec6e`** — preview HTML 의 3가지 표면적 버그:
  - lines 2635-2670 orphan modal body — `alarm-detail-modal` backdrop 밖의 중복 `vit-modal__body+foot` 가 모든 페이지 본문에 렌더링되던 버그. 삭제.
  - line 113 YouTube iframe — 폐쇄망 차단 위험. 삭제. (preview HTML 시안만; `login.py` 자체는 처음부터 자체 호스팅 mp4 사용)
  - `team-procs-modal` HTML 자체 부재 (button + JS 만 존재) → 누락 HTML 추가.

### 1.3 STAGE 2 인프라 (P1)
- **`3e5afb6`** — 4개 검증 스크립트 + AST baseline JSON:
  - `verify_backend_freeze.py` — 함수 시그니처 / SQL / session keys / imports 의 AST snapshot diff. STAGE 2 가 backend 를 건드리지 못하도록 enforcement gate.
  - `verify_no_external.py` — 외부 CDN URL 검출 (YouTube/Google Fonts/jsdelivr/cdnjs/openai/anthropic). `0_Home.py` 의 Pretendard / IBM Plex Mono CDN @import 는 **이전 엔지니어 결정 보존** — `ALLOW_SUBSTRINGS` 에 명시 허용.
  - `smoke_compile.sh` — `python -m py_compile` 49 파일 sweep.
  - `backend_freeze_baseline.json` — 37 파일 / 576 fns / 223 SQL / 87 session keys 스냅샷.

### 1.4 디자인 토큰 정렬 (P2)
- **`b2d7ecd`** — `theme.py` (`--radius:8/12`) vs `streamlit-clone.css` (`--sc-radius:8/12/999`) 의 충돌을 모두 0 으로 통일 (직사각형 원칙). dark mode 토큰 (`--card-bg / --soft / --border / --ink-*`) hex drift 8건도 `theme.py` 를 source of truth 로 일치.

### 1.5 신규 8 STAGE 2 primitives (P2)
- **`0522f75`** — `streamlit-app/ui/vitals/components.py` 에 추가:
  - `render_top_strip()` — 6px wine identity bar
  - `render_sub_head(title, meta)` — 좌 4px wine + h3 + meta
  - `render_nav_card_grid(cards)` — 3-col nav 카드 grid
  - `render_modal_static(...)` — 정적 모달 (인터랙티브 모달은 `st.dialog` 권장)
  - `render_toast(msg, kind=)` — `st.toast` wrap
  - `render_csv_export(df, ...)` — `st.download_button` wrap (UTF-8 BOM 포함)
  - `render_sidebar_tree(groups, active_key)` — Home/MTBA tree
  - `render_filter_block(on_apply, on_reset)` — apply/reset row
  - 모두 `_inject_components_css_once()` sentinel 로 페이지당 1회만 CSS 주입.
  - 동일 commit 에서 emoji 위반 (🌐 / ●) 4사이트 → SVG 로 교체. `theme.py` 의 `_theme_attr_script` SecurityError 방어 강화 + `measure_design_integration.py` 의 mkdir 버그 fix.

### 1.6 Preview HTML 인터랙션 21건 fix (P3)
- **`bf7a4a6`** — `preview-streamlit-clone.html` 의 broken 인터랙션 정리:
  - 로그인 form validation (빈 필드 → 에러 슬롯 노출)
  - 회원가입 step1 → step2 transition + 5:00 timer + 재발송/이메일수정
  - chat send (Enter + 버튼) + chat history container + clear
  - alarm timeline row 클릭 → alarm-detail-modal 열기
  - patch body / edit / delete UI
  - dead `#sc-theme-toggle` 참조 제거 + `prefers-color-scheme` 첫로드 적용
  - 글로벌 modal focus trap (Tab cycling)

> 위 21건은 **preview HTML 시안의 인터랙션** 수정. Streamlit 페이지 자체의 인터랙션은 처음부터 native 위젯 기반으로 정상 작동 중 — 아무것도 안 바뀜.

### 1.7 백엔드 방식 보존 (revert 들)
- **`717732f`** — `85b1572` (DB 패스워드 fallback 제거) revert. 폐쇄망 운영성 회복. 7 파일.
- **`89b2d95`** — `f85fe71` + `0522f75` 일부 + `3e5afb6` 일부 revert. 회사 방식 그대로:
  - `tracking.py` 의 connection pool 변경 → 매 호출 fresh psycopg2.connect 복원
  - `preferences.py` 의 `CURRENT_TIMESTAMP` → `NOW()` 복원 (PG dialect)
  - `0_Home.py` 의 CDN @import 2줄 복원 (외부망 fallback 의도 존중)

이 두 revert 로 STAGE 1 의 "보안" 명목 하의 백엔드 변경은 모두 0 으로 복귀. 사용자 원칙 "데이터 호출 앞단 = 회사 방식 = 변경 금지" 100% 준수.

---

## 2. STAGE 2 — 9 페이지 시각 정렬 + 마무리 (12 commits)

각 페이지가 `render_top_strip()` + (해당 시) `render_sub_head()` 를 채택하고, 인라인 `border-radius` 를 제거해 `preview-streamlit-clone.html` 의 sec-* 섹션과 시각 정렬.

| Commit | 페이지 / 영역 | 변경 핵심 |
|---|---|---|
| `8e74e6d` | `8_Patch_Note.py` | top_strip + 2× sub_head + sc-mono detail meta |
| `175fdbf` | `5_Alarm_Action_List.py` | top_strip + 3× sub_head + gradient `.main-title` 제거 |
| `1aae4e0` | `1_CMP_Dashboard.py` | top_strip + section-heading bar 직각 |
| `29807fa` | `2_UPH_Dashboard.py` | top_strip + page-head eyebrow + 6× sub_head |
| `b44a69b` | `0_Home.py` | top_strip × 2 (Case0 / Case1) |
| `ddbad3d` | `3_MTBA_Dashboard.py` + `4_MTBA_Detail_View.py` | top_strip × 2 |
| `e845dcc` | `6_MaxCapa_Chat.py` | top_strip + 5사이트 radius 제거 |
| `98307eb` | `9_Admin_Analytics.py` | top_strip + 4× sub_head + page-head shadow/radius 제거 |
| `2aebd9b` | `ui/login_ui/styles.py` + `layout.py` | login 패널 7사이트 radius 제거 (status dot 만 유지) |
| `9983dc4` | `ui/login_ui/layout.py` | `[바로가기]` 의 `st.switch_page` 타겟 `8_Board.py` → `8_Patch_Note.py` rename 누락 fix |
| `3a68815` | `4_MTBA_Detail_View.py` | 8개 off-Vitals hex → Vitals 토큰 (81.1→96.1) |
| `645afc5` | `1_CMP_Dashboard.py` | 26개 off-Vitals hex × 45회 → Vitals 토큰 (86.5→100.0) |
| `889a72c` | 8 페이지 일괄 | ~100개 inline `border-radius` 0 (rectangles only) |
| `5ac647b` | `5_Alarm` + `1_CMP` | `render_csv_export` primitive 통합 |

### 2.1 누적 효과
- 모든 9 페이지 + login 모듈에 와인 6px identity strip 일관 적용
- 모든 카드 / 입력 / 버튼 / 패널 직사각형 (status dot 만 원형 유지)
- 페이지간 visual rhythm: 와인 6px → flat 페이지 헤딩 → 좌측 wine bar sub-head → 직사각형 콘텐츠 — 9 페이지 전부 동일
- design_integration_score 평균 96.6 / 100

### 2.2 STAGE 2 가 NOT 한 것 (의식적 deferred)
| 항목 | 이유 |
|---|---|
| 페이지 레이아웃 전체 재구성 (KPI 타일 / 차트 / 테이블의 preview 와 1:1 일치) | preview 의 `sc-soft-card / sc-board-row / sc-pill / vit-kpi-grid` 등 클래스 구조를 페이지에 1:1 매핑하면 Streamlit native 위젯과 충돌. 더 큰 작업이 필요. |
| 차트 SVG 의 하드코딩 hex (~20 사이트) → CSS var 토큰화 | dark mode 차트 색이 안 바뀌는 한계. 페이지별 chart 코드 재구조화 필요. |
| Modal 4-layer hide → `.is-open` only 일원화 | 현재 함께 작동 중, 위험 없음. `render_modal_static` primitive 가 이미 `.is-open` only — 자연 마이그레이션 시 자동 정리. |
| `secrets.toml` / `setting.ini` 의 plain DB 패스워드 | 사용자 명시 정책 (폐쇄망 의식적 commit). 정책 결정 사항. |
| 미사용 5 primitive (`render_nav_card_grid / modal_static / toast / sidebar_tree / filter_block`) | 통합 자리가 페이지마다 자체 UI 깊이 박혀 있음. 필요 시 future PR 에서 도입. |

---

## 3. Deploy 절차

### 3.1 사전 점검
```bash
cd /path/to/LGIT-MPAP
bash streamlit-app/scripts/preflight.sh
```

PASS 만 있고 FAIL 0 이면 ✓ deploy OK.

### 3.2 환경 변수 / secrets.toml — 셋업 안 해도 됨
이전 엔지니어 fallback 패턴 그대로라 `secrets.toml` 도 git 에 있고 코드에도 fallback `!Q2w3e4r5t` 박혀 있음. 새 PC 에서 git clone 하면 **즉시 작동**. env 설정 불필요.

(외부 공개 시점에는 secrets.toml + setting.ini + 코드 fallback 모두 제거 + 패스워드 회전 필요 — `Known issues` §5 참조.)

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
| `4_MTBA_Detail_View` design score 81.1 → 96.1 (개선됨) | tokens(30) 14.1 → 29.1 | DONE in `3a68815` |
| `1_CMP_Dashboard` design score 86.5 → 100.0 (개선됨) | tokens(30) 16.5 → 30.0 | DONE in `645afc5` |
| `fonts.py` 가 1.7MB woff2 base64 를 모듈 메모리 상주 + 매 페이지 inject | `streamlit-app/ui/vitals/fonts.py:29` | deferred (폐쇄망 / 자체 호스팅 환경에선 OK) |
| `secrets.toml` + `setting.ini` + 코드 3곳에 패스워드 평문 | 폐쇄망 정책 | 외부 공개 시 일괄 처리 필요 |

---

_Generated as part of STAGE 2 closure.
Branch `claude/streamlit-vitals-Sry57`, base `streamlit-source`._
