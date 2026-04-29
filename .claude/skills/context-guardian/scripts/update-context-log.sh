#!/usr/bin/env bash
# Manage context_limit_log.json — load at session start, record on disconnect.
# Never hardcodes limits — uses measured values from history.
set -euo pipefail

LOG="context_limit_log.json"
DEFAULT_LIMIT=100000
SAFETY_MARGIN=0.8

usage() {
  cat <<USAGE_END
Usage:
  $0 --load
      Print the current effective context limit to stdout.
  $0 --record --model <name> --measured <tokens>
      Append a history entry and update current measured_limit.
  $0 --check <current_tokens>
      Print a warning if current_tokens is above 80% or 90% of effective_limit.
USAGE_END
}

load() {
  if [ ! -f "$LOG" ]; then
    local eff
    eff=$(awk "BEGIN { print int($DEFAULT_LIMIT * $SAFETY_MARGIN) }")
    echo "[context-guardian] No $LOG; using conservative default"
    echo "  model:           (unknown)"
    echo "  measured_limit:  $DEFAULT_LIMIT"
    echo "  effective_limit: $eff"
    return
  fi
  python3 - "$LOG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"  model:           {d.get('model', '(unknown)')}")
print(f"  measured_limit:  {d.get('measured_limit', 'N/A')}")
print(f"  effective_limit: {d.get('effective_limit', 'N/A')}")
print(f"  safety_margin:   {d.get('safety_margin', 'N/A')}")
print(f"  last_disconnect: {d.get('last_disconnect', '(none)')}")
print(f"  history entries: {len(d.get('history', []))}")
PY
}

record() {
  local model="$1" measured="$2" now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  python3 - "$LOG" "$model" "$measured" "$now" "$SAFETY_MARGIN" <<'PY'
import json, sys
from pathlib import Path
log_path, model, measured, now, margin = sys.argv[1:]
measured = int(measured)
margin = float(margin)
effective = int(measured * margin)
p = Path(log_path)
data = json.loads(p.read_text()) if p.exists() else {"history": []}
data.update({
    "model": model,
    "measured_limit": measured,
    "last_disconnect": now,
    "safety_margin": margin,
    "effective_limit": effective,
})
data.setdefault("history", []).append({
    "date": now, "measured_limit": measured, "model": model
})
p.write_text(json.dumps(data, indent=2))
print(f"[context-guardian] Recorded: {model} measured={measured} effective={effective}")
PY
}

check() {
  local current="$1"
  if [ ! -f "$LOG" ]; then
    local eff
    eff=$(awk "BEGIN { print int($DEFAULT_LIMIT * $SAFETY_MARGIN) }")
  else
    local eff
    eff=$(python3 -c "import json; print(json.load(open('$LOG')).get('effective_limit', $DEFAULT_LIMIT))")
  fi
  local pct
  pct=$(awk "BEGIN { print int($current * 100 / $eff) }")
  if [ "$pct" -ge 90 ]; then
    echo "[context-guardian] 🚨 $pct% of effective_limit ($eff) — IMMEDIATE new session required"
    exit 2
  elif [ "$pct" -ge 80 ]; then
    echo "[context-guardian] ⚠️  $pct% of effective_limit ($eff) — create SESSION_RECOVERY.md and prepare new session"
    exit 1
  else
    echo "[context-guardian] ✅ $pct% of effective_limit ($eff) — OK"
  fi
}

case "${1:-}" in
  --load) load ;;
  --record)
    shift
    MODEL="" MEASURED=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --model)    MODEL="$2"; shift 2 ;;
        --measured) MEASURED="$2"; shift 2 ;;
        *)          echo "Unknown: $1"; usage; exit 1 ;;
      esac
    done
    [ -z "$MODEL" ] && { usage; exit 1; }
    [ -z "$MEASURED" ] && { usage; exit 1; }
    record "$MODEL" "$MEASURED"
    ;;
  --check)
    [ -z "${2:-}" ] && { usage; exit 1; }
    check "$2"
    ;;
  *) usage; exit 1 ;;
esac
