#!/usr/bin/env python3
"""Append one ledger line per skill-related hook event.  argv[1] = mode."""
import json, os, re, sys, datetime, pathlib

mode = sys.argv[1] if len(sys.argv) > 1 else "unknown"
try:
    ev = json.load(sys.stdin)
except Exception:
    sys.exit(0)                      # never break the session over logging

ti = ev.get("tool_input") or {}
skill = (ev.get("command_name")      # UserPromptExpansion: /skill-name
         or ti.get("skill")          # Skill tool
         or ti.get("command")        # Skill tool, older field name
         or "")
if not skill:
    fp = ti.get("file_path") or ev.get("file_path") or ""
    m = re.search(r"/skills/([^/]+)/", fp)
    skill = m.group(1) if m else os.path.basename(fp) or "unknown"

line = {
    "ts": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "mode": mode,
    "skill": skill,
    "event": ev.get("hook_event_name"),
    "session_id": ev.get("session_id"),
    "prompt_id": ev.get("prompt_id"),
    "agent_type": ev.get("agent_type"),
    "source": ev.get("command_source"),
    "detail": ev.get("command_args") or ti.get("file_path") or ev.get("file_path"),
}
d = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".claude" / "skill-ledger"
d.mkdir(parents=True, exist_ok=True)
with (d / f"{line['session_id'] or 'unknown'}.jsonl").open("a") as f:
    f.write(json.dumps(line) + "\n")
