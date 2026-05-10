@echo off
REM ============================================================
REM LG Innotek VITALS — Streamlit 실행 (Windows)
REM 가상환경 활성화 후 streamlit run.
REM ============================================================
setlocal
title VITALS Web Dashboard

cd /d "%~dp0"
set ROOT=%CD%

REM --- 가상환경 확인 ---
if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo [ERROR] 가상환경이 없습니다. 먼저 setup.bat 실행.
    pause
    exit /b 1
)

REM --- 운영 PC 환경변수 (선택, secrets.toml 보다 우선) ---
REM 필요 시 아래 주석 해제 + 실제 값 입력
REM set DB_URL=postgresql+psycopg2://postgres:<PW>@localhost:5432/MTBA
REM set CMP_DB_HOST=localhost
REM set CMP_DB_PASSWORD=<PW>
REM set ITAS_DB_HOST=localhost
REM set ITAS_DB_PASSWORD=<PW>

REM Outlook 미사용 환경 (개발/테스트) 인증코드 화면 표시
REM set LGIT_MOCK=1

echo.
echo ============================================================
echo   LG Innotek VITALS — Streamlit Dashboard
echo ============================================================
echo   포트: 8501
echo   URL : http://localhost:8501
echo.
echo   종료: Ctrl+C
echo ============================================================
echo.

call "%ROOT%\.venv\Scripts\activate.bat"
streamlit run "%ROOT%\streamlit-app\login.py" --server.port 8501

endlocal
pause
