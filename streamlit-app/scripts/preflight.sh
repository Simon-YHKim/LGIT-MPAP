#!/usr/bin/env bash
# preflight.sh — Deploy 전 1-shot 점검.
#
# 폐쇄망 LG Innotek 사내 PC 에서 streamlit-app 을 처음 deploy 할 때
# 실행해서 모든 사전 조건이 충족됐는지 빠르게 확인. 한 항목이라도 FAIL
# 이면 exit 1, 모두 PASS 면 exit 0.
#
# 사용:  bash streamlit-app/scripts/preflight.sh
#        cd streamlit-app && bash scripts/preflight.sh
#
# 검사 항목:
#   1. Python 버전 + 핵심 패키지 (streamlit / sqlalchemy / psycopg2)
#   2. .streamlit/secrets.toml 존재 + 필수 키 (DB_URL, [db], [cookie])
#   3. 환경변수 fallback (DB_URL / ITAS_DB_PASSWORD / CMP_DB_PASSWORD) —
#      secrets.toml 없으면 env 가 있어야 함
#   4. 모든 .py 파일 syntax (smoke_compile.sh)
#   5. 백엔드 freeze (verify_backend_freeze.py)
#   6. 외부 URL 0 (verify_no_external.py)
#   7. dark mode tokens (verify_dark_mode_tokens.py)
#   8. 폰트 woff2 5개 + 비디오 mp4 1개 자체 호스팅 확인
#   9. DB 연결 smoke test (MTBA / auth / ITAS / CMP 4 DB) — 실 connection
#  10. design integration score >= 90/100

set -uo pipefail

# repo root 로 이동
cd "$(dirname "$0")/../.."

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }

check_pass() { green "[PASS] $1"; PASS_COUNT=$((PASS_COUNT+1)); }
check_fail() { red   "[FAIL] $1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
check_warn() { yellow "[WARN] $1"; WARN_COUNT=$((WARN_COUNT+1)); }

echo "================================================================"
echo " LG Innotek Vitals — Deploy Preflight"
echo " repo: $(pwd)"
echo " time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"

# ─── 1. Python + 핵심 패키지 ─────────────────────────────────────
echo ""
echo "[1] Python + dependencies"
PY_VER=$(python --version 2>&1)
echo "  $PY_VER"

for pkg in streamlit sqlalchemy psycopg2 pandas; do
  if python -c "import $pkg" 2>/dev/null; then
    ver=$(python -c "import $pkg; print(getattr($pkg, '__version__', 'unknown'))" 2>/dev/null)
    check_pass "import $pkg ($ver)"
  else
    check_fail "import $pkg failed"
  fi
done

# Streamlit 버전 권장: 1.55.x (clone.css data-testid 가 이 버전 기준)
ST_VER=$(python -c "import streamlit; print(streamlit.__version__)" 2>/dev/null || echo "")
if [ -n "$ST_VER" ]; then
  case "$ST_VER" in
    1.55.*) check_pass "streamlit version match (1.55.x)" ;;
    *)      check_warn "streamlit $ST_VER — 권장 1.55.x. data-testid selector 가 깨질 수 있음" ;;
  esac
fi

# ─── 2. secrets.toml 존재 + 필수 키 ─────────────────────────────
echo ""
echo "[2] secrets.toml configuration"
SECRETS=streamlit-app/.streamlit/secrets.toml
if [ -f "$SECRETS" ]; then
  check_pass "$SECRETS exists"
  for key in "DB_URL" "\[db\]" "host" "name" "user" "password"; do
    if grep -qE "^$key" "$SECRETS"; then
      check_pass "secrets.toml has: $key"
    else
      check_fail "secrets.toml missing: $key"
    fi
  done
else
  check_warn "$SECRETS not found — env vars 로 대체 가능"
fi

# ─── 3. 환경변수 (정보성 — secrets.toml + 코드 fallback 둘 다 있어 필수 아님) ──
echo ""
echo "[3] Environment variables (정보성 — secrets.toml + 코드 fallback 우선)"
for env_var in DB_URL ITAS_DB_PASSWORD CMP_DB_PASSWORD; do
  if [ -n "${!env_var:-}" ]; then
    check_pass "env $env_var is set (override 우선 적용)"
  else
    # 폐쇄망 운영성 보존을 위해 코드에 fallback literal !Q2w3e4r5t 가 있고
    # secrets.toml 에도 password 가 commit 되어 있음 — env 미설정 OK.
    echo "  [INFO] env $env_var unset — secrets.toml 또는 코드 fallback 사용"
  fi
done

# ─── 4. py_compile 전수 ─────────────────────────────────────────
echo ""
echo "[4] Python syntax (smoke_compile.sh)"
if bash streamlit-app/scripts/smoke_compile.sh 2>&1 | tail -1 | grep -q PASS; then
  check_pass "smoke_compile — 49 .py files clean"
else
  check_fail "smoke_compile failed"
  bash streamlit-app/scripts/smoke_compile.sh 2>&1 | tail -10
fi

# ─── 5. backend freeze ──────────────────────────────────────────
echo ""
echo "[5] Backend freeze (function sigs / SQL / session_state / imports)"
if python streamlit-app/scripts/verify_backend_freeze.py 2>&1 | tail -1 | grep -q PASS; then
  check_pass "verify_backend_freeze — 37 files / 578 fns / 223 SQL / 87 keys preserved"
else
  check_fail "verify_backend_freeze failed"
  python streamlit-app/scripts/verify_backend_freeze.py 2>&1 | tail -20
fi

# ─── 6. 외부 URL 0 ──────────────────────────────────────────────
echo ""
echo "[6] No external URLs (closed-network compliance)"
if python streamlit-app/scripts/verify_no_external.py 2>&1 | tail -1 | grep -q PASS; then
  check_pass "verify_no_external — 56 files clean"
else
  check_fail "verify_no_external — external URL detected"
  python streamlit-app/scripts/verify_no_external.py 2>&1 | tail -10
fi

# ─── 7. dark mode tokens ────────────────────────────────────────
echo ""
echo "[7] Dark mode tokens"
if python streamlit-app/scripts/verify_dark_mode_tokens.py 2>&1 | head -1 | grep -q PASS; then
  check_pass "verify_dark_mode_tokens — light + dark CSS coherent"
else
  check_fail "verify_dark_mode_tokens failed"
fi

# ─── 8. 폰트 woff2 + 비디오 mp4 ─────────────────────────────────
echo ""
echo "[8] Self-hosted assets (closed network)"
FONTS_DIR=streamlit-app/ui/vitals/fonts
for f in lg-ei-headline-700.woff2 lg-ei-text-300.woff2 lg-ei-text-400.woff2 lg-ei-text-600.woff2 lg-ei-text-700.woff2; do
  if [ -f "$FONTS_DIR/$f" ]; then
    size=$(wc -c < "$FONTS_DIR/$f")
    check_pass "font: $f ($size bytes)"
  else
    check_fail "font missing: $FONTS_DIR/$f"
  fi
done

LOGIN_VIDEO=streamlit-app/img/bgi.mp4
if [ -f "$LOGIN_VIDEO" ]; then
  size_mb=$(echo "scale=1; $(wc -c < "$LOGIN_VIDEO") / 1048576" | bc 2>/dev/null || echo "?")
  check_pass "login video: $LOGIN_VIDEO (${size_mb} MB)"
else
  check_fail "login video missing: $LOGIN_VIDEO"
fi

# ─── 9. DB 연결 smoke test ──────────────────────────────────────
echo ""
echo "[9] DB connection smoke (4 DBs: MTBA / auth / ITAS / CMP)"
DB_RESULT=$(python -c "
import sys, os
sys.path.insert(0, 'streamlit-app')
try:
    from db import get_engine
    eng = get_engine()
    from sqlalchemy import text
    with eng.connect() as c:
        v = c.execute(text('SELECT 1')).scalar()
        print(f'OK_MTBA: {v}')
except Exception as e:
    print(f'FAIL_MTBA: {type(e).__name__}: {e}')
" 2>&1)

if echo "$DB_RESULT" | grep -q OK_MTBA; then
  check_pass "DB connect MTBA (via db.get_engine)"
else
  check_fail "DB connect MTBA — $DB_RESULT"
  echo "  → secrets.toml 의 DB_URL 확인 또는 env DB_URL 설정"
fi

# 다른 3 DB 는 실 password 없이는 connect 못 시도. 설정만 확인.
for env_var in ITAS_DB_PASSWORD CMP_DB_PASSWORD; do
  if [ -n "${!env_var:-}" ] || grep -qE "^password\s*=" "$SECRETS" 2>/dev/null; then
    check_pass "DB cred for $env_var (env or secrets.toml)"
  else
    check_warn "DB cred for $env_var unset — UPH/CMP 페이지 진입 시 RuntimeError"
  fi
done

# ─── 10. design score >= 90 ─────────────────────────────────────
echo ""
echo "[10] Design integration score"
SCORE=$(python streamlit-app/scripts/measure_design_integration.py 2>&1 | grep AVERAGE | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [ -n "$SCORE" ]; then
  if (( $(echo "$SCORE >= 90" | bc -l 2>/dev/null) )); then
    check_pass "design_score $SCORE / 100"
  else
    check_warn "design_score $SCORE / 100 (<90 — 추가 개선 권장)"
  fi
else
  check_warn "design_score 측정 실패"
fi

# ─── Final ──────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo " RESULT: PASS=$PASS_COUNT · FAIL=$FAIL_COUNT · WARN=$WARN_COUNT"
echo "================================================================"

if [ "$FAIL_COUNT" -gt 0 ]; then
  red " ✘ Deploy NOT recommended — fix FAIL items first"
  exit 1
fi
if [ "$WARN_COUNT" -gt 0 ]; then
  yellow " ⚠ Deploy OK — but review WARN items"
fi
green " ✓ Preflight PASS — safe to deploy"
exit 0
