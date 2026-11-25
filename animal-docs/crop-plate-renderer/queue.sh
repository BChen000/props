#!/bin/bash
# Render queue: runs the lines of queue.txt one at a time ("script.py args ..."), skipping lines already in done.txt.
# Append or reorder lines while it runs; a line runs again if you remove it from done.txt (or change any word).
#   ./queue.sh SCRIPT_DIR [STATE_DIR]     STATE_DIR defaults to SCRIPT_DIR/../build/queue
# Env: PYTHON (default python3), ONCE=1 to exit when the queue is empty instead of waiting for more lines.
SRC="$(cd "${1:-.}" && pwd)"
STATE="${2:-$SRC/../build/queue}"
mkdir -p "$STATE"; STATE="$(cd "$STATE" && pwd)"
PY="${PYTHON:-python3}"
touch "$STATE/queue.txt" "$STATE/done.txt"
cd "$SRC"
while true; do
  next=$(grep -v -x -F -f "$STATE/done.txt" "$STATE/queue.txt" | grep -v '^\s*$' | head -1)
  if [ -z "$next" ]; then [ -n "${ONCE:-}" ] && exit 0; sleep 20; continue; fi
  echo "$(date +%T) START $next" >> "$STATE/queue.log"
  log="$STATE/$(echo "${next%%.py*}" | tr '/' '_').log"
  $PY $next > "$log" 2>&1
  rc=$?
  echo "$(date +%T) END $next rc=$rc" >> "$STATE/queue.log"
  echo "$next" >> "$STATE/done.txt"
done
