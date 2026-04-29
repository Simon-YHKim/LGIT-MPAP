#!/usr/bin/env bash
# simon-stack vendored SessionStart hook — self-contained.
# Installs simon-stack skills + Gstack runtime on every Claude Code web session.
# Reads simon-stack skills from THIS repo's .claude/skills/ (no network).
# Clones Gstack from upstream at session start.

set -euo pipefail

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
log() { echo "[simon-stack-vendor] $*"; }

log "Starting. repo=$REPO_DIR remote=${CLAUDE_CODE_REMOTE:-false}"

# Idempotency marker
MARKER=~/.claude/.simon-stack-installed
CURRENT_SHA=$(cd "$REPO_DIR" && git rev-parse HEAD 2>/dev/null || echo vendor-$(date +%s))

if [ -f "$MARKER" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$CURRENT_SHA" ]; then
  log "Already installed at $CURRENT_SHA, skipping"
  exit 0
fi

mkdir -p ~/.claude/skills ~/.claude/instincts

# --- Gstack runtime (clone from upstream — public repo, always accessible) ---
if [ ! -d ~/.claude/skills/gstack ]; then
  log "Cloning Gstack..."
  TMP=$(mktemp -d)
  if git clone --depth 1 https://github.com/garrytan/gstack "$TMP/gstack-src" 2>&1 | tail -3; then
    cp -a "$TMP/gstack-src" ~/.claude/skills/gstack
    rm -rf "$TMP"
    if command -v bun >/dev/null 2>&1; then
      (cd ~/.claude/skills/gstack && bun install >/dev/null 2>&1) || log "WARN: bun install failed"
    fi
  else
    log "WARN: Gstack clone failed — continuing with local skills only"
    rm -rf "$TMP"
  fi
fi

# --- Expose individual Gstack skills ---
if [ -d ~/.claude/skills/gstack ]; then
  for d in ~/.claude/skills/gstack/*/; do
    name=$(basename "$d")
    [ -f "$d/SKILL.md" ] || continue
    [ -e ~/.claude/skills/"$name" ] && continue
    cp -r "$d" ~/.claude/skills/"$name"
  done
fi

# --- simon-stack skills from THIS repo ---
for src_dir in "$REPO_DIR"/skills-src "$REPO_DIR"/.claude/skills; do
  [ -d "$src_dir" ] || continue
  for d in "$src_dir"/*/; do
    name=$(basename "$d")
    [ -f "$d/SKILL.md" ] || continue
    [ -e ~/.claude/skills/"$name" ] && continue
    cp -r "$d" ~/.claude/skills/"$name"
  done
done

# --- INDEX + instincts ---
[ -f "$REPO_DIR/.claude/skills/INDEX.md" ] && [ ! -f ~/.claude/skills/INDEX.md ] && \
  cp "$REPO_DIR/.claude/skills/INDEX.md" ~/.claude/skills/INDEX.md

for f in mistakes-learned.md project-patterns.md korean-context.md tool-quirks.md; do
  [ -f "$REPO_DIR/.claude/instincts/$f" ] && [ ! -f ~/.claude/instincts/"$f" ] && \
    cp "$REPO_DIR/.claude/instincts/$f" ~/.claude/instincts/"$f"
done

# --- Global CLAUDE.md ---
if [ ! -f ~/.claude/CLAUDE.md ] && [ -f "$REPO_DIR/.claude/CLAUDE.md.template" ]; then
  cp "$REPO_DIR/.claude/CLAUDE.md.template" ~/.claude/CLAUDE.md
fi

# --- Marker ---
echo "$CURRENT_SHA" > "$MARKER"
log "✅ Bootstrap complete"
