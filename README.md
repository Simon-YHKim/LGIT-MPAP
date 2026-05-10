# LG Innotek **VITALS** — 설비 생산성 분석 플랫폼

> **공정의 호흡을 데이터로 듣다**
> 광학솔루션 사업부 · 생산혁신센터 · Max Capa 팀
> Equipment Productivity Analytics Platform · Streamlit + PostgreSQL

---

## 한 줄 요약

LG Innotek 광학 사업부의 설비 생산성을 **CMP · UPH · MTBA** 세 축으로 통합 분석·조회하는 사내 엔지니어링 플랫폼. Streamlit 1.55 기반, **사내 폐쇄망 운영 전용**.

---

## 빠른 배포 (사내 폐쇄망)

운영 PC 가 외부 인터넷 차단 환경이라는 전제로, 깃허브 zip 다운로드 한 번으로 셋업이 끝나도록 구성.

### 1단계 — 외부 인터넷 PC 에서 zip 다운로드

GitHub `Simon-YHKim/LGIT-MPAP` 레포에서 `codex/streamlit-clone-html-port` 브랜치를 zip 으로 다운로드:

```
https://github.com/Simon-YHKim/LGIT-MPAP/archive/refs/heads/codex/streamlit-clone-html-port.zip
```

또는 GitHub 웹에서:
1. 레포 페이지 우측 상단 `Branch` 드롭다운 → `codex/streamlit-clone-html-port` 선택
2. 초록 `Code` 버튼 → `Download ZIP`

zip 안에는 모든 코드 + 폰트 + 로고 + 분석 트래커 JS 가 inline 으로 포함됨 (외부 CDN 의존 0).

### 2단계 — 운영 PC 로 zip 이동

USB / 사내 파일서버 등으로 운영 PC 에 zip 복사. 압축 해제 위치는 자유 (예: `D:\LGIT_MPAP`).

### 3단계 — 사전 요구사항 (운영 PC, Windows)

| 항목 | 버전 / 비고 |
|---|---|
| **OS** | Windows 10/11 또는 Server |
| **Python** | 3.12.x (3.13 미테스트, 3.11 호환 가능) |
| **PostgreSQL** | 16+ (테스트 환경: 18.3) |
| **Outlook** | 데스크톱 클라이언트 + 공용 계정 `maxcapa@lginnotek.com` 로그인 (회원가입 인증 메일 발송용) |
| **사내 PostgreSQL DB** | `MTBA`, `CMP`, `I-TAS_Data`, `MES_UPH`, `auth` 5 개 |

### 4단계 — 자동 설치 (권장)

압축 해제한 폴더 안에서:

```powershell
.\setup.bat
```

자동으로 수행됨:
1. Python 3.12 가상환경 생성 (`.venv`)
2. `pip install -r streamlit-app/requirements.txt` (Windows 에서 pywin32 포함)
3. `compileall` + `verify_no_external` + `verify_backend_freeze` 검증
4. `streamlit-app/.streamlit/secrets.toml` 존재 여부 확인 (없으면 템플릿 안내)
5. PostgreSQL 연결 ping 테스트

설치 완료 후:

```powershell
.\run.bat
```

자동으로 `.venv` 활성화 + `streamlit run streamlit-app\login.py --server.port 8501` 실행. 브라우저는 자동 오픈하지 않음 (`headless = true`). 직접 `http://localhost:8501` 접속.

### 5단계 — 수동 설치 (대안)

```powershell
cd D:\LGIT_MPAP

REM 가상환경
python -m venv .venv
.venv\Scripts\activate

REM 의존성
pip install -r streamlit-app\requirements.txt

REM secrets.toml 작성 (없으면 db.py default 사용)
notepad streamlit-app\.streamlit\secrets.toml

REM 검증
.venv\Scripts\python.exe -m compileall -q streamlit-app
.venv\Scripts\python.exe streamlit-app\scripts\verify_no_external.py
.venv\Scripts\python.exe streamlit-app\scripts\verify_backend_freeze.py

REM 실행
streamlit run streamlit-app\login.py --server.port 8501
```

---

## DB 셋업

5 개의 PostgreSQL 데이터베이스가 필요. 각 DB 의 스키마 파일은 `streamlit-app/SQL/` 또는 `streamlit-app/Master_Data/`.

```sql
-- pgAdmin 또는 psql 에서 실행
CREATE DATABASE "MTBA";
CREATE DATABASE "CMP";
CREATE DATABASE "I-TAS_Data";
CREATE DATABASE "MES_UPH";
CREATE DATABASE "auth";
```

스키마 적용은 운영팀이 정한 절차 또는 `streamlit-app/SQL/` 안 `*.sql` 파일을 적절한 DB 에 import.

### auth DB 의 사용자 등록

회원가입은 Outlook 인증 메일을 사용하므로 사내 PC + Outlook 셋업이 필요. 대안: 직접 SQL 로 첫 admin 사용자 등록.

```sql
-- auth DB
\c auth
INSERT INTO users (email, password_hash, department, role, is_verified)
VALUES (
  'admin@lginnotek.com',
  '<bcrypt 해시>',  -- python -c "import bcrypt; print(bcrypt.hashpw(b'pass', bcrypt.gensalt()).decode())"
  '광학솔루션',
  'admin',
  TRUE
);
```

---

## 환경 변수 (선택, 우선순위 높음)

`secrets.toml` 보다 우선 적용. 운영 환경에서 비밀번호를 코드에서 분리하고 싶을 때 사용.

```powershell
$env:DB_URL = "postgresql+psycopg2://postgres:<PW>@localhost:5432/MTBA"
$env:CMP_DB_HOST = "localhost"
$env:CMP_DB_PASSWORD = "<PW>"
$env:ITAS_DB_HOST = "localhost"
$env:ITAS_DB_PASSWORD = "<PW>"

REM Outlook 미사용 환경 (개발/테스트) — 인증코드 화면 표시
$env:LGIT_MOCK = "1"

streamlit run streamlit-app\login.py
```

---

## 페이지 구성

| URL | 페이지 | 백엔드 |
|---|---|---|
| `/` | 로그인 / 회원가입 | auth DB · Outlook COM |
| `/Home` | 메뉴 게이트웨이 (5 hero 카드) + Home_1/2/3 시안 | CMP DB |
| `/CMP_Dashboard` | CMP 달성률 대시보드 (3-model × 12-process 그리드) | CMP DB |
| `/UPH_Dashboard` | UPH / 동작시간 분석 (호기 필터 + 동작 분석 3 카드) | I-TAS_Data + MES_UPH |
| `/MTBA_Dashboard` | MTBA 분석 Reporting (필터 + Target + 6-period bar) | MTBA DB |
| `/MTBA_Detail_View` | MTBA Heatmap (셀 클릭 → 알람 상세) | MTBA DB |
| `/Alarm_Action_List` | 알람 액션 리스트 (타임라인 카드 + 상세 모달) | MTBA DB |
| `/MaxCapa_Chat` | 자연어 생산지표 조회 | FastAPI:9000 + vLLM:150.150.83.26 |
| `/Patch_Note` | 변경 이력 (목록/상세 + 등록 아코디언) | auth DB |
| `/Admin_Analytics` | 관리자 분석 (10 tabs) | auth DB analytics 스키마 |

---

## 검증 게이트 (CI / pre-commit)

운영 중에도 정기적으로 실행 권장:

```powershell
.\.venv\Scripts\python.exe -m compileall -q streamlit-app
.\.venv\Scripts\python.exe streamlit-app\scripts\verify_no_external.py
.\.venv\Scripts\python.exe streamlit-app\scripts\verify_backend_freeze.py
.\.venv\Scripts\python.exe streamlit-app\scripts\verify_dark_mode_tokens.py
```

| 게이트 | 의미 |
|---|---|
| `compileall` | 모든 `.py` 가 syntactically valid |
| `verify_no_external` | 외부 CDN / Google Fonts / jsdelivr 등 인터넷 fetch 없음 (폐쇄망 보장) |
| `verify_backend_freeze` | 함수 시그니처 / SQL / session_state 키 / import 가 baseline 대비 사라지지 않음 |
| `verify_dark_mode_tokens` | 다크 모드 CSS 토큰 일관성 |

---

## 폐쇄망 운영 보장

✅ **확인된 사항** (2026-05-11 기준 commit `8c081f2`):

- 모든 폰트 (LG EI Text/Headline) base64 inline data URI (`ui/vitals/fonts.py`)
- LG Innotek 로고 base64 data URI (`ui/vitals/components.py`)
- Analytics tracker JS 인라인 번들 (`ui/analytics/tracker.js`)
- Streamlit telemetry 차단 (`gatherUsageStats = false`)
- 외부 CDN @import 제거 (jsdelivr Pretendard, Google Fonts IBM Plex Mono)
- 라이브 검증 결과: Home/CMP/UPH/MTBA 페이지에서 외부 fetch = **0** (이전 75 → 0)

⚠️ **사내망 외부 노출 시 즉시 회전 필요**:
- `streamlit-app/db.py` 의 hardcoded password fallback (`!Q2w3e4r5t`)
- `streamlit-app/.streamlit/secrets.toml` (git 에 commit 됨)

---

## 디렉토리 구조

```
LGIT-MPAP/
├── README.md                   # 이 파일
├── DESIGN.md                   # Calm Engineering 톤·토큰 사양
├── setup.bat                   # 자동 설치 (Windows)
├── run.bat                     # Streamlit 실행 (Windows)
├── streamlit-app/
│   ├── login.py                # 로그인 + 회원가입 (Outlook COM)
│   ├── auth_guard.py           # 페이지 접근 보호
│   ├── db.py                   # SQLAlchemy 엔진
│   ├── tracking.py             # 페이지 조회 / 세션 로깅
│   ├── requirements.txt        # Python 의존성 (pywin32 포함)
│   ├── .streamlit/
│   │   ├── config.toml         # Streamlit 테마 + telemetry 차단
│   │   └── secrets.toml        # DB 비밀번호 (git 포함)
│   ├── pages/                  # 9 개 dashboard 페이지
│   ├── ui/
│   │   ├── vitals/             # 디자인 시스템 (Vitals 와인 accent)
│   │   │   ├── theme.py        # CSS 토큰 + 사이드바 / 모달
│   │   │   ├── fonts.py        # LG EI 폰트 base64 loader
│   │   │   ├── fonts/          # *.woff2 (5 파일)
│   │   │   ├── assets/         # LG Innotek 로고
│   │   │   └── components.py   # 재사용 컴포넌트
│   │   ├── login_ui/           # 로그인 페이지 전용 layout/styles
│   │   └── analytics/          # 사내 자체 trafic tracker (no GA/Clarity)
│   ├── llm_api/                # vLLM 클라이언트 (MaxCapa Chat)
│   ├── ETL/                    # 외부 시스템 → PostgreSQL 적재
│   ├── SQL/                    # 스키마 + 샘플 데이터
│   └── scripts/                # 검증 게이트 (no_external / freeze / dark_mode)
└── docs/
    ├── HANDOFF_TO_CLAUDE_COWORK.md     # 다음 세션 핸드오프
    └── design/                          # HTML 시안 (참조용)
```

---

## 트러블슈팅

### Q1. `streamlit run` 실행 시 `ModuleNotFoundError: pythoncom`

원인: 운영 PC 가 비-Windows 환경이거나 pywin32 가 설치되지 않음.

해결:
```powershell
pip install pywin32>=306
```

또는 비-Windows 개발 환경에서는 `LGIT_MOCK=1` 환경변수 설정 후 실행 (Outlook 메일 skip, 인증코드 화면 표시).

### Q2. 페이지 진입 시 "로그인이 필요합니다" 만 표시되고 실제 로그인 폼이 안 뜸

원인: Streamlit 세션이 유실됨 (보통 새 탭 열기 / 직접 URL 진입 시).

해결: `http://localhost:8501/` 로 진입 후 로그인 → 사이드바 클릭으로 페이지 이동.

### Q3. 회원가입 인증 메일이 안 옴

원인: Outlook 미설치 또는 공용 계정 미로그인.

해결:
1. 운영 PC 에 Outlook 데스크톱 설치
2. `maxcapa@lginnotek.com` 으로 Outlook 로그인 유지
3. 또는 임시로 `LGIT_MOCK=1` 사용하여 화면에 인증코드 표시

### Q4. `psycopg2.OperationalError: connection refused`

원인: PostgreSQL 미실행 또는 호스트/포트 불일치.

해결:
1. PostgreSQL 서비스 실행 확인 (Windows 서비스 관리자)
2. `streamlit-app/.streamlit/secrets.toml` 의 host/port/password 확인
3. 환경변수로 override: `$env:DB_URL = "postgresql+psycopg2://..."`

### Q5. 사이드바 Home_1/2/3 클릭 시 로그인 페이지로 회귀

해결됨 (commit `30228ba`): React onClick hijack 으로 SPA navigation 유지.
구버전 사용 중이면 최신 코드로 업데이트.

### Q6. 외부 fetch 가 검출됨 (개발자 도구 Network 탭)

원인: 구버전 사용 중 (jsdelivr CDN @import 또는 Streamlit telemetry).

해결됨 (commit `8c081f2`): 최신 코드로 업데이트 후 Streamlit 재시작.

---

## 업데이트 절차

1. 외부 인터넷 PC 에서 깃허브 최신 zip 다운로드
2. 운영 PC 로 이동
3. 기존 폴더 백업 (`D:\LGIT_MPAP_backup_YYYYMMDD`)
4. zip 압축 해제 (덮어쓰기)
5. `.streamlit/secrets.toml`, `secrets.toml` 등 환경 파일 복원
6. `pip install -r streamlit-app\requirements.txt --upgrade` (필요 시)
7. 검증 게이트 실행
8. Streamlit 재시작

---

## 핵심 원칙 (변경 금지)

다음은 backend freeze 게이트로 보호되며, **변경 시 PASS 가 깨집니다**:

- **함수 시그니처** (37 파일 / 603 functions)
- **SQL 쿼리** (230 statements)
- **`st.session_state` 키** (103 keys)
- **top-level imports**

이는 핸드오프 원칙: "preview UI → streamlit-app 덮어쓰기는 CSS 와 HTML 문자열만 교체. 백엔드 보존."

---

## 참고 문서

| 파일 | 목적 |
|---|---|
| [docs/HANDOFF_TO_CLAUDE_COWORK.md](docs/HANDOFF_TO_CLAUDE_COWORK.md) | 다음 AI 세션 핸드오프 (현재 상태 + 사용자 피드백 + 작업 우선순위) |
| [DESIGN.md](DESIGN.md) | 디자인 토큰 + 와인 accent 정책 |
| [docs/design/preview-streamlit-clone.html](docs/design/preview-streamlit-clone.html) | 시안 (브라우저로 직접 열기 가능) |

---

## 라이선스 / 권한

LG Innotek 사내 프로젝트. 외부 공개 시 db 비밀번호 회전, secrets.toml 제거, vLLM 내부 IP 환경변수화 필수.
