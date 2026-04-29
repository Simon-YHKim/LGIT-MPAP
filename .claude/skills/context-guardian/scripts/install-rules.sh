#!/usr/bin/env bash
# Install Context Guardian prevention rules into the current project root.
# Idempotent: re-running is safe (marker-based skip).
set -euo pipefail

CLAUDE_MD="CLAUDE.md"
CLAUDEIGNORE=".claudeignore"
MARKER="<!-- context-guardian-rules:v1 -->"

# --- 1. CLAUDE.md rule block ---
if [ -f "$CLAUDE_MD" ] && grep -qF "$MARKER" "$CLAUDE_MD"; then
  echo "[context-guardian] CLAUDE.md already has rules block, skipping"
else
  cat >> "$CLAUDE_MD" <<RULE_BLOCK_END

$MARKER
## Context Guardian Rules (auto-inserted)

### 작업 범위 제한
- 한 세션에서 수정 파일 최대 5 개
- 한 번에 하나의 기능/파일 단위로만 작업
- 작업 완료 즉시 git commit 후 세션 종료 권고

### 파일 읽기 제한
- node_modules/, .next/, dist/, .git/ 절대 읽지 않기
- 목적 없는 디렉토리 스캔 금지
- 대용량 파일 (1000 줄 이상) 전체 읽기 금지 — Read offset+limit 사용

### 작업 요청 방식
- 광범위 요청은 작은 단위로 분해 후 사용자 확인
  예: "Auth 전체 마이그레이션" → "어떤 파일부터 시작할까요?"
- Plan 모드로 먼저 계획 수립 → 승인 후 실행

### 컨텍스트 보호
- 80% 도달 시 SESSION_RECOVERY.md 생성 + 새 세션 전환 권고
- 90% 도달 시 즉시 작업 마무리 + 새 세션 강제

RULE_BLOCK_END
  echo "[context-guardian] CLAUDE.md rules inserted"
fi

# --- 2. .claudeignore ---
if [ -f "$CLAUDEIGNORE" ]; then
  echo "[context-guardian] .claudeignore exists, skipping"
else
  cat > "$CLAUDEIGNORE" <<IGNORE_END
node_modules/
.next/
dist/
.git/
*.lock
build/
coverage/
.cache/
.turbo/
.vercel/
.parcel-cache/
*.min.js
*.min.css
IGNORE_END
  echo "[context-guardian] .claudeignore created"
fi

# --- 3. .gitignore hint ---
echo ""
echo "[context-guardian] Consider adding to .gitignore:"
echo "  SESSION_RECOVERY.md"
echo "  context_limit_log.json"
echo "(These are per-session state, usually not committed.)"
