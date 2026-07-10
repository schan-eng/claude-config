#!/bin/bash
# Stop: deterministic post-implementation simplify pass, tiered by churn.
#   <= MICRO_MAX_LINES and < FULL_MIN_FILES  -> inline micro-pass (no skill, cheap)
#   otherwise                                -> full simplify skill
# A marker file distinguishes our own block from another stop hook's block:
# on our own follow-up stop we clean up (no loop); on someone else's we keep
# the pending list so it fires on the next fresh stop (no lost edits).
MICRO_MAX_LINES=40
FULL_MIN_FILES=3

command -v jq >/dev/null 2>&1 || exit 0
IN=$(cat)
sid=$(printf '%s' "$IN" | jq -r '.session_id // "unknown"')
active=$(printf '%s' "$IN" | jq -r '.stop_hook_active // false')
F="/tmp/claude-simplify-pending-${sid}.txt"
M="/tmp/claude-simplify-fired-${sid}"

if [ "$active" = "true" ]; then
  if [ -f "$M" ]; then
    rm -f "$M" "$F"   # our block ran; drop the simplify pass's own edits
  fi
  exit 0              # another hook's block: keep list for the next fresh stop
fi

rm -f "$M"            # stale marker from an interrupted continuation
find /tmp -maxdepth 1 -name 'claude-simplify-*' -mtime +2 -delete 2>/dev/null

[ -s "$F" ] || exit 0

files=$(cut -f1 "$F" | sort -u)
n=$(printf '%s\n' "$files" | wc -l | tr -d ' ')
head5=$(printf '%s\n' "$files" | head -5 | paste -sd, - | sed 's/,/, /g')
all=$(printf '%s\n' "$files" | paste -sd' ' -)
total=$(awk -F'\t' '{s+=$2} END {print s+0}' "$F")

rm -f "$F"
touch "$M"

if [ "$total" -le "$MICRO_MAX_LINES" ] && [ "$n" -lt "$FULL_MIN_FILES" ]; then
  reason="Simplify micro-pass (small change: ~${total} lines across ${n} file(s): ${head5}). Re-read the diff of those files and directly apply any clear simplification (dead code, needless branching/nesting, duplication, existing-util reuse); for md files, remove stale references to anything this turn renamed or dropped; for tests, collapse duplicate cases. Do NOT invoke the simplify skill and do NOT spawn subagents. If the diff is already minimal, state that in one line and finish."
else
  reason="Simplify pass, full tier (~${total} changed lines across ${n} file(s)). Invoke the Skill tool with skill \"simplify\" and args \"${all}\" to apply the post-implementation refinement pass to those files."
fi

jq -n --arg r "$reason" '{decision: "block", reason: $r}'
