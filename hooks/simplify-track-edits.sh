#!/bin/bash
# PostToolUse (Edit|Write): record each source/test/markdown edit and its
# approximate churn (max of old/new line counts from the tool payload) so the
# Stop hook can trigger a deterministic, size-tiered simplify pass. Measuring
# churn here (not via git at stop time) stays correct even if the turn commits
# or reverts.
command -v jq >/dev/null 2>&1 || exit 0
IN=$(cat)
f=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // empty')
sid=$(printf '%s' "$IN" | jq -r '.session_id // "unknown"')
case "$f" in
  *.d.ts|*.min.js|*/node_modules/*|*/dist/*|*/generated/*|*/__generated__/*) ;;
  */.claude/plans/*|*/.claude/projects/*|/tmp/*|/private/tmp/*) ;;  # plan-mode, memory, scratchpad
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.py|*.go|*.rs|*.java|*.rb|*.c|*.cc|*.cpp|*.h|*.hpp|*.cs|*.swift|*.kt|*.scala|*.php|*.md|*.mdx)
    lines=$(printf '%s' "$IN" | jq -r '[(.tool_input.old_string // ""), (.tool_input.new_string // .tool_input.content // "")] | map(split("\n") | length) | max')
    printf '%s\t%s\n' "$f" "${lines:-1}" >> "/tmp/claude-simplify-pending-${sid}.txt"
    ;;
esac
exit 0
