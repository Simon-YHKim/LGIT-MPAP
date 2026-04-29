#!/usr/bin/env bash
# Generate SESSION_RECOVERY.md from current git state.
# Scans output for secret patterns and aborts if found.
set -euo pipefail

OUT="SESSION_RECOVERY.md"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(no git)")
LAST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "(no commits)")
STATUS_SHORT=$(git status --short 2>/dev/null || echo "")
DIFF_STAT=$(git diff --stat 2>/dev/null | tail -20 || echo "")

ENV_VARS="- (run this script after .env.example exists to auto-populate)"
if [ -f .env.example ]; then
  ENV_VARS=$(grep -E '^[A-Z_]+=' .env.example 2>/dev/null | cut -d= -f1 | sed 's/^/- /')
  [ -z "$ENV_VARS" ] && ENV_VARS="- (no vars in .env.example)"
fi

cat > "$OUT" <<RECOVERY_END
# 🚨 SESSION_RECOVERY.md
생성일시: $NOW

## 현재 작업 정보
- 레포: $REPO
- 브랜치: $BRANCH
- 마지막 커밋: $LAST_COMMIT

## 변경된 파일 (git status)
\`\`\`
$STATUS_SHORT
\`\`\`

## diff --stat
\`\`\`
$DIFF_STAT
\`\`\`

## 완료된 작업
<!-- 완료 항목 수동 기록 (사용자가 이 세션에서 한 일) -->
- [x] (예: validate 로직 추가)

## 미완료 작업
<!-- 남은 항목 수동 기록 -->
- [ ] (예: 에러 메시지 i18n)

## 핵심 변경 파일
<!-- 한 줄 요약으로 수동 기록 -->
- <path>: <변경 내용 한 줄>

## 환경변수 참조 (값 제외 - 보안)
$ENV_VARS

## 다음 세션 시작 프롬프트 (아래 전체 복사)
────────────────────────────────────────
$REPO 레포의 $BRANCH 브랜치에서 작업을 이어합니다.
SESSION_RECOVERY.md 를 먼저 읽고
<첫 미완료 작업> 부터 시작해주세요.
────────────────────────────────────────

---
**보안 규칙**: 이 파일에 API 키/토큰/패스워드 절대 기록 금지.
환경변수는 이름만 나열하고 값은 .env 에 유지.
**미커밋 변경 포함**: git status/diff 에 민감 정보가 있으면 저장 전 수동 검토.
RECOVERY_END

# Secret scan — abort if detected
if grep -qE 'sk-[a-zA-Z0-9]{20,}|sk_live_[a-zA-Z0-9]+|pk_live_[a-zA-Z0-9]+|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{30,}|xox[bps]-[a-zA-Z0-9]' "$OUT"; then
  echo "[context-guardian] ⚠️ Potential secret detected in $OUT"
  echo "[context-guardian] Review and remove before continuing"
  exit 1
fi

echo "[context-guardian] ✅ Created: $OUT"
echo "[context-guardian] Next steps:"
echo "  1. Fill in the '완료된 작업' and '미완료 작업' sections"
echo "  2. Start a new Claude Code session"
echo "  3. First message: paste the prompt from '다음 세션 시작 프롬프트'"
