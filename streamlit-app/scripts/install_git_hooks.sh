#!/usr/bin/env bash
# install_git_hooks.sh — pre-commit hook 설치.
#
# 본 스크립트 1회 실행하면, 그 후 매 git commit 시 자동으로:
#   1. verify_backend_freeze.py  — 백엔드 (DB·SQL·session·imports) 변경 차단
#   2. smoke_compile.sh          — 49 .py 파일 syntax 검증
#   3. verify_no_external.py     — 외부 CDN URL 신규 도입 차단
# 이 셋 중 하나라도 FAIL 면 commit 차단. 회사 방식 보존 강제.
#
# 우회 (긴급 시): git commit --no-verify
# 단, --no-verify 는 회사 방식 위반 위험 — 반드시 사후 verify 재실행 권장.
#
# 사용:
#   bash streamlit-app/scripts/install_git_hooks.sh
#
# 제거:
#   rm .git/hooks/pre-commit

set -euo pipefail
cd "$(dirname "$0")/../.."  # repo root

if [ ! -d ".git" ]; then
    echo "[ERROR] .git 디렉토리 없음 — repo root 에서 실행하세요"
    exit 1
fi

HOOK_PATH=".git/hooks/pre-commit"

cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
# Auto-installed by streamlit-app/scripts/install_git_hooks.sh
# 4 게이트 중 회사방식·syntax 검증 3개를 commit 직전에 강제.

set -uo pipefail

# repo root 이동 (hook 은 .git/ 안에서 실행됨)
cd "$(git rev-parse --show-toplevel)"

# ANSI color
red()   { printf "\033[31m%s\033[0m\n" "$1"; }
green() { printf "\033[32m%s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$1"; }

echo ""
yellow "═══ pre-commit gate (회사 방식 보존 enforcement) ═══"

# ─── 1. backend freeze ────────────────────────────────────
echo ""
echo "[1/3] backend freeze..."
if ! python streamlit-app/scripts/verify_backend_freeze.py 2>&1 | tail -20; then
    red "✘ backend freeze FAIL — 함수/SQL/session_state/import 가 변경됨."
    red "  회사 방식 위반 가능성. revert 하거나 의도적이면 baseline 갱신 후 재시도."
    red "  baseline 갱신:  python streamlit-app/scripts/verify_backend_freeze.py --emit-baseline"
    echo ""
    red "긴급 우회: git commit --no-verify  (단, 사후 검증 책임은 본인)"
    exit 1
fi

# ─── 2. smoke compile ─────────────────────────────────────
echo ""
echo "[2/3] smoke compile..."
if ! bash streamlit-app/scripts/smoke_compile.sh 2>&1 | tail -10; then
    red "✘ smoke compile FAIL — Python syntax 에러"
    red "  위 출력의 SyntaxError 메시지 확인."
    exit 1
fi

# ─── 3. no external URL ───────────────────────────────────
echo ""
echo "[3/3] no external URL..."
if ! python streamlit-app/scripts/verify_no_external.py 2>&1 | tail -10; then
    red "✘ no_external FAIL — 새 외부 CDN URL 도입됨 (폐쇄망 위반)"
    red "  의도적이면 verify_no_external.py 의 ALLOW_SUBSTRINGS 에 추가."
    exit 1
fi

echo ""
green "✓ 3 gates PASS — commit 진행."
exit 0
HOOK_EOF

chmod +x "$HOOK_PATH"

echo "================================================================"
echo " ✓ pre-commit hook 설치 완료: $HOOK_PATH"
echo "================================================================"
echo ""
echo "이제 매 git commit 시 자동으로 3 gate 검증:"
echo "  · verify_backend_freeze.py  (백엔드 보존)"
echo "  · smoke_compile.sh          (Python syntax)"
echo "  · verify_no_external.py     (외부 URL 0)"
echo ""
echo "FAIL 시 commit 차단. 우회 (긴급 시): git commit --no-verify"
echo ""
echo "테스트: 빈 commit 으로 hook 확인"
echo "  git commit --allow-empty -m 'test pre-commit'"
echo ""
echo "제거: rm .git/hooks/pre-commit"
