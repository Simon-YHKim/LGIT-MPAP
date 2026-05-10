# Codex Prompt — LGIT-MPAP (Vitals) 전체 페이지 기능 레퍼런스

> **사용법**: 이 파일 전체를 Codex 의 첫 메시지로 붙여넣거나
> `codex < docs/CODEX_PAGE_REFERENCE.md` 또는
> `cat docs/CODEX_PAGE_REFERENCE.md | codex consult` 형태로 전달.
>
> 이후 "X 페이지의 Y 기능 어떻게 동작해?", "Z 위젯 key 가 뭐야?",
> "9_Admin 의 retention SQL 보여줘" 같은 질문에 정확히 답할 수 있다.

---

## 0. 너 (Codex) 의 역할

너는 LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa TDR 의 폐쇄망
설비 생산성 분석 플랫폼 **Vitals (LGIT-MPAP)** 에 대한 **모든** 코드 흐름·
위젯·SQL·session_state·외부 API·페이지 간 네비게이션을 빠짐없이 알고 있는
시니어 엔지니어다. 아래 §1~§14 의 정보를 **사실로 받아들이고**, 추측이
필요한 경우엔 반드시 "(코드에서 확인 안 됨)" 이라고 명시한다.

---

## 1. 제품·환경

| 항목 | 값 |
|---|---|
| 회사 | LG Innotek 광학솔루션 사업부 |
| 팀 | 생산혁신센터 Max Capa TDR (이전: Max Capa 팀) |
| 플랫폼명 | **Vitals** (이전: MPAP / Stethos) |
| 캐치프레이즈 | "공정의 호흡을 데이터로 듣다" |
| 환경 | **폐쇄망** 사내 PC + Streamlit 1.55 + PostgreSQL 4 DB + vLLM (FastAPI:9000) |
| Python | 3.11+ |
| Repo | `Simon-YHKim/LGIT-MPAP` |
| 페이지 수 | login + 9 (총 10개, 13,865 줄) |

### DB 4개
1. **인증 DB** (st.secrets["db"]) — users, email_auth_codes, user_sessions, page_view_logs, board_posts
2. **CMP DB** (env: CMP_DB_*) — mart_cmp_dashboard_daily
3. **MES / I-TAS_Data DB** — uph_input_runtime_daily_model, itas_uph_result, dim_mes_selector_map
4. **MTBA DB** — mtba_daily, mtba_timeline, mtba_alarms, alarm_comment_history, equipment_master, process_master, team_process_filter

---

## 2. 절대 보존 원칙 (백엔드 freeze — 한 줄도 손대지 말 것)

이전 엔지니어가 회사 폐쇄망 환경에 맞춰 의식적으로 잡은 부분.

| 영역 | 보존 패턴 | 이유 |
|---|---|---|
| DB 연결 | `get_conn()` 매 호출 fresh `psycopg2.connect(...)` | 회사 PG 호환 |
| DB 패스워드 fallback | `os.getenv('X', '!Q2w3e4r5t')` literal | 폐쇄망 즉시 작동 |
| 인증 | `auth_guard.require_login()` + `st.session_state` | 손대지 X |
| SQL dialect | PostgreSQL `NOW()` | 회사 표준 |
| CDN @import | Pretendard / IBM Plex Mono | 폐쇄망 fallback |
| session_state 키 87개 | 추가 OK / 변경·삭제 X | 기존 흐름 보존 |
| 함수 576개 / SQL 223개 | 추가 OK / 시그니처·문자열 변경 X | baseline 검증 |
| `secrets.toml` + `setting.ini` 평문 password | git commit 의식적 | 인수자 즉시 작동 |

검증 게이트 (4개 모두 PASS 필수):
```bash
python streamlit-app/scripts/verify_backend_freeze.py        # 576 fn / 223 SQL / 87 sess
python streamlit-app/scripts/verify_no_external.py           # 외부 URL 0
python streamlit-app/scripts/verify_dark_mode_tokens.py      # dark CSS 일관
bash streamlit-app/scripts/smoke_compile.sh                  # 49 .py syntax
```

---

## 3. 공통 인프라

### 3.1 인증 가드
모든 페이지 최상단에 호출:
```python
from auth_guard import require_login
require_login(page_name="...", page_path="pages/...py", min_interval_sec=5)
```
- `st.session_state.login == False` → 로그인 페이지로 즉시 리다이렉트
- `tracking.log_page_view_once()` → 5초 최소 간격으로 page_view_logs 기록

### 3.2 Vitals 테마
```python
from ui.vitals import apply_vitals_theme
from ui.vitals.components import render_top_strip, render_sub_head, render_csv_export, render_toast
from ui.analytics import inject_tracker

apply_vitals_theme()
inject_tracker(page_name="PageName", page_path="pages/N_PageName.py")
render_top_strip()  # 6px wine bar (모든 페이지 상단 의무)
render_sub_head("섹션명", "메타정보")
```

### 3.3 CSS 토큰 (33개 중 핵심)
```css
--primary: #A50034;      /* Wine red — LG Innotek identity */
--primary-dark: #7E0027;
--primary-tint: #F8E5EC;
--page-bg: #F7F8FA;
--card-bg: #FFFFFF;
--soft: #F1F3F5;
--border: #E5E7EB;
--ink-body: #1F2430;
--ink-muted: #6B7280;
--ink-subtle: #9CA3AF;
--status-good: #1F8B4C;
--status-warn: #B57F1B;
--status-bad: #B23A48;
```

### 3.4 글로벌 session_state 키 (login 에서 set)
- `login`: bool
- `user_email`: str (도메인 자동: "id" → "id@lginnotek.com")
- `department`: str (14개 부서 중 하나)
- `role`: "user" | "admin"
- `session_id`: str
- `last_logged_page`, `last_logged_time`: page-view 추적
- `selected_post_id`: int | None (Patch Note 선택)

---

## 4. login.py — 인증 시스템 (1145 lines)

### 4.1 진입 분기
```python
view = st.session_state.get("view", "login")  # "login" | "signup" | "reset_password"
login_view = st.session_state.get("login_view", "home")  # "home" | "change_password"
```
- 로그인 성공 + 비밀번호 만료 (`password_changed_at` 90일 초과) → `login_view = "change_password"` 강제 전환
- 로그인 성공 + 정상 → `st.switch_page("pages/0_Home.py")`

### 4.2 레이아웃
- **배경**: `render_video_background()` → `img/bgi.mp4` autoplay/muted/loop + 검정 오버레이 rgba(0,0,0,0.65)
- **상단**: `render_top_brand()`
- **좌측 35%**: `render_left_panel_background()` + `render_auth_intro()` + radio (`auth_tab_radio_{view}`, options=["login","signup"], horizontal=True) + `render_login()` 또는 `render_signup()` + `render_identity_block()`
- **우측 45%**: `render_right_panels(recent_patch_posts)` — `board_posts` WHERE category='patch' AND is_published=TRUE LIMIT 4

### 4.3 위젯 (login form)
```python
with st.form("login_form"):
    st.text_input("아이디", key="login_user_input")           # @lginnotek.com 자동 추가
    st.text_input("비밀번호", type="password", key="login_pw")
    st.form_submit_button("로그인", use_container_width=True)
st.button("비밀번호를 잊으셨나요?", key="goto_reset")          # → view = "reset_password"
```

### 4.4 회원가입 3단계
| Step | 위젯 (key) | 액션 |
|---|---|---|
| 1 | `signup_email_input` + 버튼 "인증코드 발송" | `is_allowed_email()` → `is_existing_user()` → `generate_code()` → `save_auth_code()` → `send_auth_email()` (Outlook COM, maxcapa@lginnotek.com) |
| 2 | `signup_code_input` + 버튼 "인증 확인" | `verify_auth_code()` → `signup_step = 3` |
| 3 | `signup_pw1`, `signup_pw2`, `signup_dept` (selectbox, 14개 부서) + 버튼 "회원가입 완료" | `validate_password()` → `create_user()` → 자동 로그인 화면 |

### 4.5 비밀번호 정책 (`validate_password()`)
- 3종 조합 (대/소/숫자/특수 중 3종) → 최소 8자
- 2종 조합 → 최소 10자
- 이메일 계정ID 포함 불가
- 연속 문자/숫자 (1234, abcd, qwer) 불가

### 4.6 실패 정책
- `MAX_AUTH_FAIL_COUNT` = 5 (인증코드 검증 실패)
- `MAX_LOGIN_FAIL_COUNT` = 5 (로그인 실패) → 계정 차단, 관리자 문의
- 인증코드 만료: `NOW() + interval '10 minutes'`

### 4.7 비밀번호 재설정·변경
- **reset_password**: `reset_email_input` → `reset_code_input` → `reset_pw1/pw2` (reset_step 2→3)
- **change_password** (login_view): `change_pw_current` → 재로그인 검증 → `change_pw_new1/new2` → `update_user_password()`

### 4.8 핵심 SQL
```sql
-- 회원가입
INSERT INTO users (email, password_hash, department, is_verified)
VALUES (%s, %s, %s, TRUE) ON CONFLICT (email) DO NOTHING;

-- 로그인 (password_expired 검사)
SELECT password_hash, department, role, login_fail_count, password_changed_at
FROM users WHERE email = %s AND is_verified = TRUE;

-- 인증코드 (10분 유효)
INSERT INTO email_auth_codes (email, code, expires_at, fail_count)
VALUES (%s, %s, NOW() + interval '10 minutes', 0)
ON CONFLICT (email) DO UPDATE SET ...;

-- 인증 성공 시 코드 삭제
DELETE FROM email_auth_codes WHERE email = %s;
```

### 4.9 로그아웃
```python
st.button("🚪 로그아웃") → tracking.close_login_session(session_id, reason="logout")
                       → session_state 전체 초기화
```

---

## 5. 0_Home.py — 대시보드 허브 (2489 lines)

### 5.1 목적
플랫폼의 진입점. 5개 카드로 각 Dashboard 진입 + CMP 요약 상황판 3 모드.

### 5.2 메인 카드 (5개)
```python
st.button(label, key=f"home_card_{key}", use_container_width=True, disabled=disabled)
```
| key | 이동 페이지 | 상태 |
|---|---|---|
| `home_card_cmp` | pages/1_CMP_Dashboard.py | 가오픈 |
| `home_card_uph` | pages/2_UPH_Dashboard.py | 가오픈 |
| `home_card_mtba` | pages/3_MTBA_Dashboard.py | 가오픈 |
| `home_card_mtba_detail` | pages/4_MTBA_Detail_View.py | 가오픈 |
| `home_card_chat` | pages/6_MaxCapa_Chat.py | disabled (오픈예정) |

각 카드 CSS: `.st-key-home_card_*` + `button::before` (아이콘 ▦ ↗ ⌁ ▧ □) + `button::after` (배지 ● 가오픈/● 오픈예정).

### 5.3 CMP 요약 상황판 모드 토글
```python
st.button("기본",            key="vit_mode_btn_current", disabled=(mode=="current"))
st.button("Best · Worst 카드", key="vit_mode_btn_case1",   disabled=(mode=="case1"))
st.button("CMP 요약 상황판",   key="vit_mode_btn_case2",   disabled=(mode=="case2"))
# session_state["home_mode"] = "current" | "case1" | "case2"
```

### 5.4 필터 (각 모드별)
| 모드 | radio | multiselect (areas) | multiselect (models) |
|---|---|---|---|
| current/case0 | `home_view_mode_simple` ("일별"/"주간") | `home_areas_simple` | `home_models_simple` |
| case1 (Best/Worst) | 동일 구조 | 동일 | 동일 |
| case2 (요약 상황판) | `home_cmp_view_mode` ("일간"/"주간") | `home_cmp_selected_areas` | `home_cmp_selected_models` |

각 form 에 "적용" / "초기화" `form_submit_button` 두 개.

### 5.5 데이터 (CMP DB)
```sql
SELECT work_date, period, area, model, process_l1, equipment, cmp_achievement_rate
FROM mart_cmp_dashboard_daily
WHERE work_date BETWEEN (TODAY - 3 months) AND TODAY
ORDER BY work_date DESC;
```

### 5.6 STAGE 2 보정 사항
- `.cmp-filter-compact` y축 최소화 (font-size 8px, min-height 22px)
- `.block-container` max-width: 1180px

---

## 6. 1_CMP_Dashboard.py — CMP 달성률 (1520 lines)

### 6.1 목적
CMP(조합별생산효율) 달성률 추이 + 상위 5 / Worst 5 공정 분석.

### 6.2 필터 폼
```python
with st.form("cmp_filter_form"):
    st.radio("기간",       ["일간", "주간"],   key="cmp_view_mode")
    st.multiselect("영역", options=all_areas,  key="cmp_areas")
    st.multiselect("모델", options=all_models, key="cmp_models")
    st.form_submit_button("적용")
    st.form_submit_button("초기화")
```

### 6.3 Worst 5 인터랙션
```python
def render_worst5_interactive(worst_hist, latest_week_label, key_prefix):
    state_key = f"{key_prefix}_selected_process"
    selected_process = st.selectbox("공정 선택", processes, key=state_key)
```

### 6.4 Home 이동
```python
if st.button("🏠 메뉴선택 화면으로 가기"):
    st.switch_page("pages/0_Home.py")
```

### 6.5 데이터 (CMP DB + CSV fallback)
```sql
-- 일간
SELECT work_date, period, area, model, process_l1, equipment, cmp_achievement_rate
FROM mart_cmp_dashboard_daily
WHERE work_date BETWEEN start_date AND end_date
ORDER BY work_date;

-- 주간 (week_of_month 함수)
SELECT EXTRACT(YEAR FROM work_date) AS year, EXTRACT(MONTH FROM work_date) AS month,
       week_of_month(work_date) AS week, area, model, process_l1, AVG(cmp_achievement_rate)
GROUP BY year, month, week, area, model, process_l1;
```
DB 실패 시 `.data/cmp_dashboard_daily.csv` fallback.

### 6.6 차트
- `make_line_chart()` (matplotlib): 날짜별 CMP 추이
- `achievement_color(v)`: 0~100% → green/yellow/red

### 6.7 CSV
```python
render_csv_export(df, label='CSV 다운로드', filename='cmp_dashboard.csv', key='cmp_csv_dl')
```

---

## 7. 2_UPH_Dashboard.py — UPH 시간당 생산량 (2636 lines)

### 7.1 목적
MES vs ITAS 두 데이터소스의 UPH 비교 + Best/Worst 호기 + AI 분석 의견.

### 7.2 필터
```python
st.selectbox('공장 선택',  options=area_options,    key='selected_area')
st.selectbox('공정 선택',  options=process_options, key='selected_process')
st.selectbox('모델 선택',  options=model_options,   key='selected_model')
st.date_input('날짜 선택',                           key='selected_date')
```
옵션은 `fetch_selector_dims(...)` 가 채움.

### 7.3 데이터소스 토글 (MES ↔ ITAS)
```python
source_mode = st.session_state.get('uph_source_mode', 'MES')
if st.button(button_label, key='uph_source_toggle'):
    st.session_state['uph_source_mode'] = 'MES' if source_mode == 'ITAS' else 'ITAS'
    st.rerun()
```

### 7.4 Best/Worst 호기 선택
```python
st.session_state.setdefault('bw_show_all', False)
st.selectbox('Best',  machine_options, key='bw_manual_best')
st.selectbox('Worst', machine_options, key='bw_manual_worst')
if st.button(toggle_label, key='bw_toggle_all'):
    st.session_state['bw_show_all'] = not st.session_state['bw_show_all']
```

### 7.5 AI 분석 의견 → FastAPI POST
```python
def generate_ai_comment(data_dict):
    response = requests.post(
        "http://localhost:9000/ai/analyze",
        json=data_dict,
        timeout=10
    )
    return response.json()["comment"]

if st.button("AI 분석 의견", key=btn_key):
    st.session_state[result_key] = generate_ai_comment({...})
```

### 7.6 데이터 SQL
```sql
-- MES
SELECT work_date AS "날짜", machine_no AS "호기", SUM(uph) AS "UPH"
FROM uph_input_runtime_daily_model
WHERE work_date = %s AND process_name = %s AND customer_model = %s
GROUP BY work_date, machine_no;

-- ITAS
SELECT work_date AS "날짜", equipment AS "호기", SUM(uph) AS "UPH"
FROM itas_uph_result
WHERE work_date = %s AND process_name = %s AND model = %s
GROUP BY work_date, equipment;

-- Best/Worst 랭킹
SELECT machine_no, uph,
       ROW_NUMBER() OVER (ORDER BY uph DESC) AS rn_best,
       ROW_NUMBER() OVER (ORDER BY uph ASC)  AS rn_worst
FROM ... ORDER BY uph DESC LIMIT 1;

-- 동작별 분석
SELECT action_name AS "동작명", AVG(duration_sec) AS "소요시간"
FROM uph_detail_actions
WHERE work_date = %s AND machine_no = %s
GROUP BY action_name;
```

### 7.7 차트 (plotly)
- `px.line` x=호기, y=UPH (날짜별)
- `px.bar` x=호기, y=UPH (Best/Worst)
- `add_hline` 전체 평균 UPH (빨간 점선)
- `st.dataframe` 호기별 상세

---

## 8. 3_MTBA_Dashboard.py — 평균가동시간 (1754 lines)

### 8.1 목적
설비 가동률·MTBA 모니터링 + 4_Detail 로 드릴다운.

### 8.2 필터
```python
st.radio("기간", ["일간", "주간", "월간"], key="mtba_period")
st.multiselect("영역", options=all_areas,    key="mtba_areas")
st.multiselect("장비", options=all_equipment, key="mtba_equipment")
st.form_submit_button("적용")
```

### 8.3 드릴다운 (4_Detail 이동)
```python
if st.button(equipment_name, key=f"mtba_drill_{equipment_id}"):
    st.switch_page("pages/4_MTBA_Detail_View.py?equipment_id={equipment_id}")
```

### 8.4 데이터 (MTBA DB)
```sql
-- 일간
SELECT work_date AS "날짜", equipment_name AS "설비",
       ROUND(mtba_minutes::numeric, 2) AS "MTBA(분)",
       ROUND(availability_pct::numeric, 2) AS "가동률(%)"
FROM mtba_daily
JOIN equipment_master USING (equipment_id)
WHERE work_date BETWEEN %s AND %s AND area IN (...)
ORDER BY work_date DESC;

-- 주간
SELECT DATE_TRUNC('week', work_date) AS week_start,
       equipment_name, AVG(mtba_minutes) AS avg_mtba
FROM mtba_daily
GROUP BY week_start, equipment_name;
```

### 8.5 STAGE 3 라운드 4 색상 변경 (MTBA bar 와인~검은 grayscale)
`data-period` attribute 로 scope:
- 1주전: `#D88FA2` → `#8B0830`
- 2주전: `#7E0027` → `#6B1E3A`
- 지난달: `#B57F1B` → `#4B1E2A`
- 2달전: `#6B7280` → `#2E1419`
- 선택 기간 `#A50034` / 지난해 `#1F2430` 유지

---

## 9. 4_MTBA_Detail_View.py — MTBA 상세 (1524 lines)

### 9.1 모듈 구조 (mtba_detail_view 패키지)
- `config.py`, `state.py`, `ui.py`, `repository.py`, `popup.py`, `comments.py`, `grid.py`, `builders.py`

### 9.2 진입 (query param)
```python
query_params = st.query_params
equipment_id = int(query_params.get("equipment_id", 1))
```

### 9.3 위젯
```python
date_range = st.date_input("조회 기간", value=(start_date, end_date), key="mtba_detail_dates")
st.dataframe(timeline_df, use_container_width=True,
             columns=["timestamp", "event_type", "status", "duration", "notes"])

@st.dialog("코멘트 추가")
def add_comment_modal():
    comment_text = st.text_area("코멘트")
    if st.button("저장"):
        # alarm_comment_history INSERT
```

### 9.4 데이터 (MTBA DB)
```sql
-- 타임라인
SELECT timestamp, status, event_type, duration_sec, notes
FROM mtba_timeline
WHERE equipment_id = %s AND timestamp BETWEEN %s AND %s
ORDER BY timestamp DESC;

-- 알람
SELECT timestamp, alarm_code, alarm_name, severity
FROM mtba_alarms
WHERE equipment_id = %s AND timestamp BETWEEN %s AND %s
ORDER BY timestamp DESC;

-- 코멘트
SELECT comment_text, created_by, created_at
FROM alarm_comment_history
WHERE equipment_id = %s AND created_at BETWEEN %s AND %s
ORDER BY created_at DESC;
```

### 9.5 session_state
- `mtba_detail_equipment_id`, `mtba_detail_date_range`, `mtba_detail_filter_mode` ("hourly"|"15min"), `mtba_detail_show_comments`

---

## 10. 5_Alarm_Action_List.py — 알람 액션 이력 (497 lines)

### 10.1 목적
알람 코멘트 CRUD + 팀별 공정 필터 저장.

### 10.2 필터
```python
team_name = st.selectbox('팀 선택',
                          ["전체", "FOL팀", "MOL팀", "EOL팀"],
                          key='aal_team')
period = st.date_input('기간 선택', value=(start_date, end_date), key='aal_period')
keyword = st.text_input('검색어',
                          placeholder='알람명 / 알람코드 / Comment / 설비명 / 호기')
selected_authors    = st.multiselect('작성자 필터',  author_options)
selected_alarm_codes = st.multiselect('알람코드 필터', alarm_code_options)
```

### 10.3 팀 공정 선택 data_editor
```python
edited_df = st.data_editor(
    process_editor_df,
    use_container_width=True, hide_index=True, num_rows='fixed',
    disabled=['공정약어', '공정명', 'process_id'],
    column_config={
        '선택':     st.column_config.CheckboxColumn('선택'),
        '공정약어': st.column_config.TextColumn('공정약어'),
        '공정명':   st.column_config.TextColumn('공정명'),
    },
    key=f'aal_proc_editor_{team_name}'
)
```
저장:
```python
if st.button(f"{team_name} 팀 공정 저장", type='primary'):
    selected_ids = get_selected_process_ids_from_editor(edited_df)
    save_team_process_ids(engine, team_name, selected_ids)
    render_toast(f'[{team_name}] 팀 공정 목록이 저장되었습니다.', kind="success")
    st.rerun()
```

### 10.4 코멘트 수정·삭제 (타임라인 카드)
```python
# 수정 진입
if st.button('수정', key=f'edit_btn_{row_id}'):
    st.session_state['editing_comment_id'] = row_id
    st.session_state[f'editing_comment_text_{row_id}'] = row['Comment']
    st.rerun()

# 수정 UI
if st.session_state.get('editing_comment_id') == row_id:
    new_author = st.text_input('작성자',  key=f'editing_comment_author_{row_id}')
    new_text   = st.text_area('Comment 수정', key=f'editing_comment_text_{row_id}', height=140)
    if st.button('수정 저장', key=f'save_edit_{row_id}', type='primary'):
        update_comment(engine, row_id, new_text, new_author)
        st.session_state.pop('editing_comment_id')
        st.rerun()
```

### 10.5 SQL (MTBA DB)
```sql
-- Comment 조회
SELECT id, created_at::date AS written_date, created_by,
       model_name, process_name, equipment_name, equipment_no,
       alarm_code, alarm_name, comment_text, ...
FROM alarm_comment_history
WHERE created_at::date BETWEEN %s AND %s
  AND process_name = ANY(%s)
  AND (alarm_name ILIKE %kw% OR alarm_code ILIKE %kw% OR comment_text ILIKE %kw% ...)
  AND created_by   = ANY(%authors)
  AND alarm_code   = ANY(%alarm_codes)
ORDER BY created_at DESC, id DESC;

-- UPDATE / DELETE / Team Process Filter UPSERT 등
INSERT INTO team_process_filter (team_name, process_id) VALUES (%s, %s)
ON CONFLICT (team_name, process_id) DO NOTHING;
```

### 10.6 CSV
```python
render_csv_export(display_df, label='CSV 다운로드',
                  filename='alarm_action_list.csv', key='alarm_csv_dl')
```

---

## 11. 6_MaxCapa_Chat.py — AI 대화형 UPH 조회 (634 lines)

### 11.1 목적
자연어 질문 → FastAPI(:9000) → intent parsing → SQL 자동 생성 → 시각화.

### 11.2 입력
```python
st.session_state["llm_question"] = st.text_area(
    "질문 입력", value=st.session_state.get("llm_question", ""),
    height=100, placeholder="예: 최근 3일 APS Test 공정의 UPH는 얼마인가?"
)
if st.button("질문 분석 및 실행", key="analyze_execute_btn"):
    plan = request_analyze(question)  # POST /chat/analyze
    if plan["status"] == "ready_for_approval":
        result = request_execute(plan)  # POST /chat/execute
```

### 11.3 명확화 (need_clarification)
```python
if "customer_model" in missing_slots:
    selected_label = st.selectbox("customer_model 선택", options=list(option_map.keys()))
    if st.button("선택한 모델로 계속 진행"):
        next_plan = request_continue(intent=plan["intent"],
                                      updates={"customer_model": selected_model})
# process_name 도 동일 패턴
```

### 11.4 FastAPI 엔드포인트 (http://localhost:9000)
| Endpoint | Request | Response |
|---|---|---|
| `/chat/analyze` (POST) | `{session_id, user_id, question}` | `{status, intent, message, missing_slots, candidates, execution_plan, sql_preview}` |
| `/chat/continue` (POST) | `{session_id, intent, updates}` | (analyze 와 동일) |
| `/chat/execute` (POST) | `{session_id, approved, execution_plan, intent}` | `{status, message, natural_response, result_table, tool_name, summary}` |

`status`: `"ready_for_approval"` | `"need_clarification"` | `"unsupported"` | `"error"` | `"completed"`.

### 11.5 결과 렌더링
- `summary.combined_rank == True` → 좌 Best 테이블+bar / 우 Worst 테이블+bar / `add_hline` 전체평균
- 일반 → 테이블 + 라인/막대 차트

### 11.6 session_state
- `llm_question`, `llm_plan`, `llm_result`

---

## 12. 8_Patch_Note.py — 패치노트 게시판 (657 lines)

### 12.1 권한
- 로그인 필수. role 제약 없음 (읽기).
- **role == "admin"** 만 쓰기/수정/삭제.

### 12.2 진입 분기
```python
query_params = st.query_params
query_post_id = query_params.get("post_id", None)
if query_post_id:
    st.session_state.selected_post_id = int(query_post_id)
```

### 12.3 레이아웃
- 좌측 35% — 글 목록: 작성일(mm-dd) + 태그 pill + 제목 button (`key=f"post_{post_id}"`)
- 우측 65% — 상세 + 메타 + 본문(html-escaped)
- 관리자 전용: "수정" / "삭제" 버튼 + expander 글 등록

### 12.4 글 작성·수정·삭제
```python
# 등록
if st.button("등록"):
    create_board_post("patch", tag, title.strip(), content.strip(),
                      created_by=st.session_state.get("user_email"))
    render_toast("등록되었습니다.", kind="success")
    st.query_params.clear()
    st.rerun()

# 수정 (edit_mode)
edit_tag     = st.selectbox("태그", ["NEW", "FIX", "UPD", "INFO"], key="edit_tag")
edit_title   = st.text_input("제목", value=title, key="edit_title")
edit_content = st.text_area("내용", value=content, height=220, key="edit_content")
if st.button("수정 저장", key=f"save_post_{post_id}"):
    update_board_post(post_id, edit_tag, edit_title.strip(), edit_content.strip())

# 삭제 (soft delete)
if st.button("삭제 확인", key=f"confirm_del_{post_id}", type='primary'):
    delete_board_post(post_id)  # is_published = FALSE
```

### 12.5 SQL (인증 DB · board_posts)
```sql
-- 목록
SELECT id, category, tag, title, created_by, created_at
FROM board_posts
WHERE category='patch' AND is_published=TRUE
ORDER BY created_at DESC;

-- 상세
SELECT id, category, tag, title, content, created_by, created_at, updated_at
FROM board_posts WHERE id=%s AND is_published=TRUE;

-- 작성
INSERT INTO board_posts (category, tag, title, content, created_by)
VALUES ('patch', %s, %s, %s, %s);

-- 수정
UPDATE board_posts SET tag=%s, title=%s, content=%s, updated_at=NOW() WHERE id=%s;

-- 삭제 (soft)
UPDATE board_posts SET is_published=FALSE, updated_at=NOW() WHERE id=%s;
```

### 12.6 태그 색상
- `NEW` (`.board-tag-new`) — green tint
- `FIX` (`.board-tag-fix`) — wine tint
- `UPD` (`.board-tag-upd`) — yellow tint
- `INFO` — soft gray

---

## 13. 9_Admin_Analytics.py — 관리자 분석 (1009 lines)

### 13.1 권한 게이트
```python
require_login(...)
if st.session_state.get("role") != "admin":
    st.error("관리자만 접근할 수 있습니다.")
    st.stop()
```

### 13.2 필터 (3열)
```python
st.date_input("시작일", value=today - 30days, key="admin_start_date")
st.date_input("종료일", value=today,           key="admin_end_date")
st.selectbox("부서",   ["전체"] + dept_options, key="admin_selected_dept")
```

### 13.3 KPI 4개 (st.metric)
- 총 세션 수 / 유니크 사용자 수 / 평균 세션 길이 / 기타

### 13.4 분석 탭 10개 (st.tabs)
1. 일일 활동 추이
2. 부서별 사용자 분포
3. 사용자별 로그인 빈도
4. 페이지별 조회 순위
5. 평균 세션 길이
6. 활동 시간대별 분석
7. 신규 vs 기존 사용자
8. 부서별 평균 활동시간
9. 사용자 보유율 (Retention)
10. (코드에서 확인 안 됨 — 마지막 탭)

각 탭: `st.dataframe(df) + download_df_button(df, filename, "CSV 다운로드")`.

### 13.5 핵심 SQL (인증 DB)
```sql
-- KPI
SELECT COUNT(*) AS total_sessions,
       COUNT(DISTINCT user_email) AS unique_users,
       COALESCE(AVG(session_duration_sec), 0) AS avg_session_duration_sec
FROM user_sessions
WHERE DATE(login_at) BETWEEN %s AND %s {dept_filter};

-- Tab 1 일일 활동
SELECT DATE(login_at) AS date, COUNT(*) AS session_count
FROM user_sessions
WHERE DATE(login_at) BETWEEN %s AND %s
GROUP BY DATE(login_at) ORDER BY date DESC;

-- Tab 4 페이지 조회 순위
SELECT page_name, COUNT(*) AS view_count, AVG(session_duration_sec) AS avg_time
FROM page_view_logs
WHERE viewed_at BETWEEN %s AND %s
GROUP BY page_name ORDER BY view_count DESC;

-- Tab 6 시간대 분석
SELECT EXTRACT(HOUR FROM login_at) AS hour, COUNT(*) AS session_count
FROM user_sessions
WHERE DATE(login_at) BETWEEN %s AND %s
GROUP BY EXTRACT(HOUR FROM login_at) ORDER BY hour;

-- Tab 7 신규 vs 기존
SELECT CASE WHEN DATE(u.created_at) BETWEEN %s AND %s THEN 'New' ELSE 'Existing' END AS user_type,
       COUNT(DISTINCT s.user_email) AS user_count
FROM user_sessions s JOIN users u ON s.user_email = u.email
WHERE DATE(s.login_at) BETWEEN %s AND %s
GROUP BY user_type;

-- Tab 9 Retention
SELECT DATE(s1.login_at) AS prev_date, DATE(s2.login_at) AS next_date,
       COUNT(DISTINCT s1.user_email) AS retained_users
FROM user_sessions s1
LEFT JOIN user_sessions s2
    ON s1.user_email = s2.user_email
   AND DATE(s2.login_at) = DATE(s1.login_at) + interval '1 day'
WHERE DATE(s1.login_at) BETWEEN %s AND %s
GROUP BY prev_date, next_date;
```

### 13.6 유틸
```python
def format_duration(seconds):
    if seconds > 3600: return f"{h}시간 {m}분 {s}초"
    elif seconds > 60: return f"{m}분 {s}초"
    else:              return f"{s}초"
```

---

## 14. 페이지 간 네비게이션·연동

### 14.1 진입 흐름
```
login.py
  ├ 로그인 성공 ────────────► pages/0_Home.py (st.switch_page)
  ├ 비밀번호 만료 ──────────► login_view = "change_password"
  └ 비밀번호 변경 성공 ───► login 화면으로
```

### 14.2 Dashboard 간 이동
- **CMP ↔ UPH ↔ MTBA**: Home 통해서만 (각 페이지 "🏠 메뉴선택 화면으로 가기" 버튼)
- **MTBA → MTBA Detail**: query param `?equipment_id=123` 으로 전달
- **Patch Note 직접 진입**: `?post_id=123`

### 14.3 데이터 연동
- **Patch Note 게시글** → login.py 우측 패널 + 0_Home 우측 패널 (최근 4개)
- **Alarm 코멘트** → MTBA Dashboard / Detail 의 알람에 작성 → 5_Alarm_Action_List 에서 통합 조회
- **MaxCapa Chat (FastAPI)** ↔ UPH Dashboard 의 "AI 의견" 버튼 (둘 다 `/ai/analyze` 또는 `/chat/*`)

### 14.4 네비게이션 메서드
- `st.switch_page("pages/N_*.py")` — Streamlit native MPA
- `st.query_params["key"] = value` — URL 파라미터
- `st.query_params.clear()` — 글 등록 후 URL 초기화

---

## 15. 페이지 빠른 검색표

| 페이지 | 파일 | 줄수 | 인증 | 권한 | 주요 DB | 모달 (@st.dialog) | 외부 API |
|---|---|---|---|---|---|---|---|
| login | login.py | 1145 | 불필요 | 무 | 인증 DB | (없음) | Outlook COM (sendmail) |
| Home | 0_Home.py | 2489 | 필수 | 무 | CMP | (없음) | (없음) |
| 1 CMP | 1_CMP_Dashboard.py | 1520 | 필수 | 무 | CMP + CSV | (없음) | (없음) |
| 2 UPH | 2_UPH_Dashboard.py | 2636 | 필수 | 무 | MES + ITAS | (없음) | FastAPI:9000 `/ai/analyze` |
| 3 MTBA | 3_MTBA_Dashboard.py | 1754 | 필수 | 무 | MTBA | `@st.dialog` (heatmap 등) | (없음) |
| 4 Detail | 4_MTBA_Detail_View.py | 1524 | 필수 | 무 | MTBA + alarm_comment | `@st.dialog` (코멘트) | (없음) |
| 5 Alarm | 5_Alarm_Action_List.py | 497 | 필수 | 무 | MTBA | (없음, 인라인 수정) | (없음) |
| 6 Chat | 6_MaxCapa_Chat.py | 634 | 필수 | 무 | (없음, API 만) | (없음) | FastAPI:9000 `/chat/*` |
| 8 Patch | 8_Patch_Note.py | 657 | 필수 | admin 만 쓰기 | board_posts | (없음, 인라인 수정) | (없음) |
| 9 Admin | 9_Admin_Analytics.py | 1009 | 필수 | **admin 전용** | user_sessions, page_view_logs | (없음) | (없음) |

---

## 16. 코드에서 확인되지 않은 부분 (Codex 가 추측 시 명시)

- **9_Admin_Analytics.py 의 10번째 탭** 제목·SQL — 보이지 않음
- **4_MTBA_Detail_View.py 의 mtba_detail_view 패키지 내부 함수**들의 세부 구현 — 모듈 분리되어 본 보고서에서는 함수 시그니처만 추출
- **0_Home.py 의 case0/case1 차트 렌더링 코드** — CSS 클래스 (`.cmp-proc-grid`) 까지만 확인
- **2_UPH_Dashboard.py 의 AI 의견 버튼 → 응답 표시 전체 로직** — POST 호출 부분만 추출
- **3_MTBA_Dashboard.py 의 KPI 정확한 계산식** — 조회 SQL 구조까지만 확인

---

## 17. Codex 활용 예시

이 문서를 컨텍스트에 넣은 뒤 다음 같이 질문:

```
Q: 5_Alarm_Action_List 의 팀 공정 저장은 어떤 SQL 을 쓰나?
A: → §10.5 의 INSERT INTO team_process_filter ... ON CONFLICT DO NOTHING 인용

Q: MTBA bar 차트의 1주전 색상 hex 가 변경됐다는데 뭐였지?
A: → §8.5 의 #D88FA2 → #8B0830 인용

Q: Patch Note 의 글 작성은 누가 가능?
A: → §12.1 의 role == "admin" 인용 + §12.4 의 create_board_post 시그니처

Q: FastAPI /chat/analyze 의 status 종류는?
A: → §11.4 의 ready_for_approval / need_clarification / unsupported / error / completed
```

---

_2026-05-09 작성. STAGE 3 라운드 4 (commit 0168689) 시점._
_원자료: Explore 에이전트 13,865 줄 정독 결과 (2026-05-09)._
