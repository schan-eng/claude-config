#!/bin/bash
# PostToolUse (Edit|Write): record edited implementation files so the Stop
# hook can fire the intent-check pass on what this turn actually touched.
command -v jq >/dev/null 2>&1 || exit 0
IN=$(cat)
f=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // empty')
sid=$(printf '%s' "$IN" | jq -r '.session_id // "unknown"')
case "$f" in
  *.d.ts|*.min.js|*/node_modules/*|*/dist/*|*/generated/*|*/__generated__/*) ;;
  */.claude/plans/*|*/.claude/projects/*|/tmp/*|/private/tmp/*) ;;  # plan-mode, memory, scratchpad
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.py|*.go|*.rs|*.java|*.rb|*.c|*.cc|*.cpp|*.h|*.hpp|*.cs|*.swift|*.kt|*.scala|*.php|*.md|*.mdx)
    printf '%s\n' "$f" >> "/tmp/claude-intent-pending-${sid}.txt"
    ;;
esac
exit 0
