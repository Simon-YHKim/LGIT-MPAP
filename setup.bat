@echo off
REM ============================================================
REM LG Innotek VITALS — 사내 폐쇄망 자동 설치 (Windows)
REM 사용자 피드백 (2026-05-11): 깃허브 zip 다운로드 후 더블클릭 1회로 셋업.
REM ============================================================
setlocal EnableDelayedExpansion
title VITALS Setup

cd /d "%~dp0"
set ROOT=%CD%
echo.
echo ============================================================
echo   LG Innotek VITALS — 사내 폐쇄망 자동 설치
echo ============================================================
echo   레포 경로: %ROOT%
echo.

REM --- 1. Python 3.12+ 확인 ---
echo [1/6] Python 버전 확인...
python --version 2>nul | findstr /R "Python 3\.1[2-9]" >nul
if errorlevel 1 (
    echo [ERROR] Python 3.12 이상이 필요합니다.
    echo         https://www.python.org/downloads/ 에서 다운로드 후 PATH 추가.
    echo         설치 후 이 스크립트를 다시 실행하세요.
    pause
    exit /b 1
)
python --version
echo.

REM --- 2. 가상환경 생성 ---
echo [2/6] 가상환경 (.venv) 생성...
if exist "%ROOT%\.venv\Scripts\python.exe" (
    echo     기존 .venv 발견 — 재사용.
) else (
    python -m venv "%ROOT%\.venv"
    if errorlevel 1 (
        echo [ERROR] 가상환경 생성 실패.
        pause
        exit /b 1
    )
    echo     .venv 생성 완료.
)
echo.

REM --- 3. pip 의존성 설치 ---
echo [3/6] Python 의존성 설치 (requirements.txt)...
echo     [INFO] 폐쇄망에서 pypi 접근 안되면 사내 mirror 또는 wheel 캐시 필요.
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip 1>nul 2>nul
"%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\streamlit-app\requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip install 실패. 폐쇄망 mirror 설정 또는 wheel 다운로드 필요.
    echo         사내 pypi mirror 사용 시:
    echo         pip install -r streamlit-app\requirements.txt -i ^<mirror URL^>
    pause
    exit /b 1
)
echo     의존성 설치 완료.
echo.

REM --- 4. secrets.toml 확인 ---
echo [4/6] secrets.toml 확인...
set SECRETS=%ROOT%\streamlit-app\.streamlit\secrets.toml
if exist "%SECRETS%" (
    echo     %SECRETS% 발견.
) else (
    echo     [WARN] secrets.toml 없음 — 템플릿을 만들어 둡니다.
    echo         경로: %SECRETS%
    if not exist "%ROOT%\streamlit-app\.streamlit" mkdir "%ROOT%\streamlit-app\.streamlit"
    (
        echo # secrets.toml — 사내망 운영 설정
        echo # ⚠ 외부 노출 금지. .gitignore 처리 권장.
        echo.
        echo DB_URL = "postgresql+psycopg2://postgres:!Q2w3e4r5t@localhost:5432/MTBA"
        echo.
        echo [db]
        echo host = "localhost"
        echo name = "auth"
        echo user = "postgres"
        echo password = "!Q2w3e4r5t"
        echo port = "5432"
        echo.
        echo [cookie]
        echo password = "change-me-to-random-string-min-32-chars"
    ) > "%SECRETS%"
    echo     기본 템플릿 작성 완료. 운영 환경에 맞게 수정 필요.
)
echo.

REM --- 5. 검증 게이트 실행 ---
echo [5/6] 검증 게이트 실행...
echo     5.1 compileall...
"%ROOT%\.venv\Scripts\python.exe" -m compileall -q "%ROOT%\streamlit-app" 1>nul
if errorlevel 1 (
    echo     [FAIL] compileall — Python syntax error 발생.
    pause
    exit /b 1
)
echo     5.1 compileall PASS

echo     5.2 verify_no_external...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\streamlit-app\scripts\verify_no_external.py"
if errorlevel 1 (
    echo     [FAIL] verify_no_external — 외부 URL 검출됨.
    pause
    exit /b 1
)

echo     5.3 verify_backend_freeze...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\streamlit-app\scripts\verify_backend_freeze.py"
if errorlevel 1 (
    echo     [FAIL] verify_backend_freeze — 백엔드 contract 위반.
    pause
    exit /b 1
)
echo.

REM --- 6. PostgreSQL 연결 테스트 (선택) ---
echo [6/6] PostgreSQL 연결 테스트 (선택)...
"%ROOT%\.venv\Scripts\python.exe" -c "import psycopg2, sys; ^
try: ^
    c = psycopg2.connect(host='localhost', port=5432, dbname='postgres', user='postgres', password='!Q2w3e4r5t', connect_timeout=3); ^
    print('     PostgreSQL 연결 OK'); ^
    c.close(); ^
except Exception as e: ^
    print('     [WARN] PostgreSQL 연결 실패: ', str(e)[:120]); ^
    print('            secrets.toml 또는 환경변수 DB_URL 확인 필요.'); ^
    sys.exit(0)" 2>nul

echo.
echo ============================================================
echo   설치 완료!
echo ============================================================
echo.
echo   다음 단계:
echo     1. (필요 시) streamlit-app\.streamlit\secrets.toml 의 비밀번호 수정
echo     2. PostgreSQL 5 개 DB (MTBA / CMP / I-TAS_Data / MES_UPH / auth) 준비
echo     3. run.bat 더블클릭하여 Streamlit 실행
echo     4. 브라우저에서 http://localhost:8501 접속
echo.
echo     첫 사용자 등록은 회원가입 (Outlook 인증) 또는 SQL 직접 INSERT.
echo.
pause
endlocal
