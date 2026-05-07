# Streamlit Vitals 통합 — 다각도 검증 리포트

> **브랜치**: `claude/streamlit-vitals-Sry57` ← `streamlit-source` (백업)
> **검증 도구**: SimonK 스킬 5종 병렬 (code review · adversarial codex · design audit · security checklist · scenario walkthrough)
> **결과**: 통합 성공. **9 페이지 모두 비즈니스 로직 0 변경**, 글로벌 디자인 적용. 단 **4건의 페이지-레벨 블로커** 발견 — 다음 라운드에 픽스 필요.

---

## 🟢 통과 (변경 불필요)

| 항목 | 결과 |
|---|---|
| **9 페이지 함수 시그니처 / DB 쿼리 / session_state 키 / Streamlit 컴포넌트 호출** | 100% 보존. AST 분석 검증 |
| **import cycle** | 0 — `__init__.py` → `theme.py` → `fonts.py` 선형 |
| **font 캐싱** | `@lru_cache` 로 base64 인코딩 1회 |
| **`apply_vitals_theme()` 호출 순서** | 모든 페이지에서 `st.set_page_config()` → `require_login()` → `apply_vitals_theme()` 순. 안전 |
| **Streamlit 사이드바 hide → 네비 손실?** | 모든 페이지에 `initial_sidebar_state="collapsed"`. 사이드바 의존 0 |
| **Vitals CSS 인젝션 보안 (XSS)** | 인터폴레이션 사용자 입력 0. 정적 CSS만 |
| **render_chat_panel AI 슬롭 검사** | 노란 mark / 사각 아바타 / "↳" / fade gradient / 가짜 trace_id 모두 없음 |
| **드롭인 정책** | secrets.toml + Data/ + logs/ + uploads/ + access_log/ 제외 시 안전. 모든 .py / config.toml / SQL / ETL / Master_Data 교체 OK |

---

## 🟡 개선 권장 (블로커 아님)

### B1. CSS payload 매 rerun 재방출
**증상**: `st.markdown()` 호출은 매 rerun 마다 발생. base64 폰트 ~2.3MB 가 WebSocket 패킷으로 매번 방출됨 (브라우저는 data: URL 캐시 → 실제 렌더링 영향 없음). LAN 에서는 무시 가능, 원격 접근 시 대역폭 낭비.
**픽스**: `apply_vitals_theme()` 결과를 `@st.cache_resource` 로 감싸기 (1줄 변경).
**우선순위**: 낮음. 사내 LAN 운용엔 영향 미미.

### B2. font-display: swap 으로 1-2초 폰트 교체 시점 metric shift
**증상**: 첫 진입 시 LG EI 미로드 → Malgun Gothic fallback 렌더 → 1-2초 후 LG EI 로 교체될 때 텍스트 8-15px 시프트.
**픽스**: `font-display: block` (max 3초 텍스트 hide) 로 변경 또는 사용자가 첫 페이지 먼저 prefetch.
**우선순위**: 낮음.

---

## 🔴 진짜 블로커 — 다음 라운드 필수 픽스

### 🛑 R1. Pages 3/4/5 가 잘못된 와인레드 `#6D1028` 하드코드
**위치**:
- `pages/3_MTBA_Dashboard.py:69` `PRIMARY = "#6D1028"` + `:679` 셀 색 + `:894` ag-grid 헤더
- `pages/4_MTBA_Detail_View.py:53` `PRIMARY = '#6D1028'` + `:129/136` 컬러 사용
- `pages/5_Alarm_Action_List.py:45` 동일

**영향**: 우리 디자인 표준은 `#A50034` 인데 이 페이지들은 살짝 다른 와인 (`#6D1028` 더 어두움). 같은 앱 안에서 톤이 두 가지로 갈라짐.

**픽스 방향**: 페이지 상단 `PRIMARY = '#6D1028'` 상수 정의 자체를 `var(--primary)` CSS 변수 사용으로 교체. `f"... {PRIMARY} ..."` Python 문자열 보간을 CSS 변수 참조로 변환.

**예상 변경**: 페이지당 ~20줄.

### 🛑 R2. `pages/0_Home.py:110` 가 `--font-body` 를 Malgun Gothic 으로 재정의
**위치**: `pages/0_Home.py:110` 라인에 다음 이상한 (구문 깨진) 정의:
```css
--font-body:'Malgun Gothic', '맑은 고딕', sans-serif;,'LG Smart','Pretendard Variable',...
```
세미콜론(`;`) 가 중간에 있어 CSS 파싱이 끊기고, Home 페이지에서만 LG EI 가 적용 안 됨 (Malgun Gothic 으로 fallback).

**픽스**: 라인 110 의 `--font-body` 정의 삭제 (또는 Vitals 와 동일 stack 으로 교체). 1줄 변경.

### 🛑 R3. 페이지들이 22~24px 라운드 카드 사용 (디자인 표준 ≤12px 위반)
**위치**:
- `pages/3_MTBA_Dashboard.py:89, :100` — 22px / 20px
- `pages/4_MTBA_Detail_View.py:74, :102` — 20px / 22px
- `pages/5_Alarm_Action_List.py:64` — 22px

**영향**: 우리 디자인 시스템은 카드 12px 최대. 이 페이지들은 시각적 톤이 너무 부드럽고 다른 페이지와 안 맞음.

**픽스**: 모든 `border-radius: 2Npx` → `var(--radius-card)` (12px) 로 교체. 페이지당 ~5줄.

### 🛑 R4. `streamlit-app/.streamlit/secrets.toml` 가 git 추적됨 (DB 비번 노출)
**위치**: `streamlit-app/.streamlit/secrets.toml` — 실 DB password 평문.
**사용자 명시**: "그냥 보안 관련도 그대로 유지해서 작업해. 어짜피 폐쇠 환경" → 사용자가 위험 수용함.
**그래도 권장**: 외부 깃허브 가시성 = 회사 자산 노출. 만약 레포가 PUBLIC 이면 **즉시 비밀번호 회전 + force-push 히스토리 정리** 권장.

또한 `pages/0_Home.py:35` 와 `llm_api/uph_llm_queries.py:17` 에 비밀번호 하드코드 의심 — secrets.toml 조회로 통일 권장.

---

## 📋 드롭인 적용 체크리스트 (사용자측)

```
✅ 안전 — 그대로 덮어쓰기
   .py 모든 파일 (login.py, pages/*, ui/*, utils.py, db.py, ...)
   .streamlit/config.toml
   SQL/, ETL/, Master_Data/, img/, llm_api/

❌ 절대 덮어쓰기 금지
   .streamlit/secrets.toml      ← 실 DB 비번 (각 환경별 다름)
   Data/                        ← 런타임 데이터
   logs/                        ← 액세스 로그 / 디버그
   uploads/                     ← 알람 어노테이션 이미지
   access_log/access_logs.db    ← 사용자 활동 SQLite

   __pycache__/, .idea/         ← 의미 없음, 덮어쓰면 다음 실행 시 재생성
```

권장 절차:
```bash
# 1. 백업
cp -r MTBA_Streamlit MTBA_Streamlit.bak.$(date +%Y%m%d)

# 2. 우리 streamlit-app/ 에서 안전 파일만 복사
rsync -av --exclude='.streamlit/secrets.toml' \
          --exclude='Data/' --exclude='logs/' \
          --exclude='uploads/' --exclude='access_log/' \
          --exclude='__pycache__' --exclude='.idea' \
          streamlit-app/ MTBA_Streamlit/

# 3. 실행
cd MTBA_Streamlit && streamlit run login.py
```

## 🧯 롤백 (한 줄)

```bash
git reset --hard ab46468  # Vitals 적용 직전 (login.py만 통합된 상태)
# 또는 완전 원본으로
git checkout streamlit-source -- streamlit-app/
```

---

## 다음 라운드 제안 (사용자 결정 대기)

### 옵션 1 — 블로커 4건 픽스 (1 라운드)
R1+R2+R3 픽스 → 모든 페이지 톤 통일. R4 는 사용자 선택.
**예상 작업**: 페이지 5개 패치, ~80 라인 변경, 1 커밋.

### 옵션 2 — 블로커 픽스 + 컴포넌트 통합 (2 라운드)
R1~R4 픽스 + 각 페이지에 `render_topnav()` / `render_page_header()` / `render_chat_panel()` 호출 추가.
**예상 작업**: 페이지 9개 수정, ~200 라인.

### 옵션 3 — 미설계 3 페이지 (Alarm/Board/Admin) 본격 디자인
원본 코드 읽고 → mockup HTML 합의 → 통합 (C1 합의대로).

진행 방향 결정해주세요.
