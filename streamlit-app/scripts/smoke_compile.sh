#!/usr/bin/env bash
# smoke_compile.sh — Streamlit 앱 전수 syntax 검증.
#
# STAGE 2 가 페이지 / UI 모듈을 수정할 때마다 모든 .py 가 import 가능한
# 상태인지 확인. import 실제 실행이 아닌 byte-compile 만 (의존성 없는
# 환경에서도 통과해야 하므로).
#
# 사용법:  bash streamlit-app/scripts/smoke_compile.sh
#         exit 0 = PASS, exit 1 = SyntaxError 발견

set -euo pipefail

cd "$(dirname "$0")/../.."  # repo root

TARGETS=(
  streamlit-app/login.py
  streamlit-app/db.py
  streamlit-app/queries.py
  streamlit-app/utils.py
  streamlit-app/auth_guard.py
  streamlit-app/access_logger.py
  streamlit-app/tracking.py
  streamlit-app/Alarm_Master_Data.py
  streamlit-app/MTBA_Data.py
  streamlit-app/reset_mtba_db.py
)
TARGETS+=( $(find streamlit-app/pages -maxdepth 1 -name "*.py" 2>/dev/null) )
TARGETS+=( $(find streamlit-app/llm_api -name "*.py" 2>/dev/null) )
TARGETS+=( $(find streamlit-app/mtba_detail_view -name "*.py" 2>/dev/null) )
TARGETS+=( $(find streamlit-app/ui -name "*.py" 2>/dev/null) )
TARGETS+=( $(find streamlit-app/ETL -name "*.py" 2>/dev/null) )
TARGETS+=( $(find streamlit-app/scripts -name "*.py" 2>/dev/null) )

failed=()
total=0
for f in "${TARGETS[@]}"; do
  [ -f "$f" ] || continue
  total=$((total + 1))
  if ! python -m py_compile "$f" 2>/tmp/.smoke_compile.err; then
    echo "[FAIL] $f"
    cat /tmp/.smoke_compile.err
    failed+=("$f")
  fi
done

if [ ${#failed[@]} -gt 0 ]; then
  echo ""
  echo "[FAIL] ${#failed[@]} of $total files have SyntaxError:"
  for f in "${failed[@]}"; do
    echo "  - $f"
  done
  exit 1
fi

echo "[PASS] $total Python files compile clean"
