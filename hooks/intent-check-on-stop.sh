#!/bin/bash
# Stop: demand an intent-check pass over this turn's edits — do the changes
# still serve the session's intent (Linear issue / user instructions)?
# Marker-file logic mirrors simplify-on-stop.sh: on our own follow-up stop we
# clean up (no loop); on another hook's block we keep the pending list.
command -v jq >/dev/null 2>&1 || exit 0
IN=$(cat)
sid=$(printf '%s' "$IN" | jq -r '.session_id // "unknown"')
active=$(printf '%s' "$IN" | jq -r '.stop_hook_active // false')
F="/tmp/claude-intent-pending-${sid}.txt"
M="/tmp/claude-intent-fired-${sid}"

if [ "$active" = "true" ]; then
  if [ -f "$M" ]; then
    rm -f "$M" "$F"   # our block ran; drop the check's own follow-up edits
  fi
  exit 0              # another hook's block: keep list for the next fresh stop
fi

rm -f "$M"            # stale marker from an interrupted continuation
find /tmp -maxdepth 1 -name 'claude-intent-*' -mtime +2 -delete 2>/dev/null

[ -s "$F" ] || exit 0

files=$(sort -u "$F" | paste -sd' ' -)
rm -f "$F"
touch "$M"

jq -n --arg r "Intent check: this turn edited implementation files. Invoke the Skill tool with skill \"intent-check\" and args \"${files}\" to verify the changes stay within the session's intent anchor. If the anchor does not exist yet, the skill gathers it once and caches it." '{decision: "block", reason: $r}'
