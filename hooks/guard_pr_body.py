#!/usr/bin/env python3
"""PreToolUse gate: refuse `gh pr create/edit` whose body lacks the skill report."""
import json, os, shlex, subprocess, sys, pathlib

MARKER = "skills-used:v1"

def body_text(cmd):
    """Return (text, checkable). Resolves --body-file so long bodies still verify."""
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return "", False                      # unparseable: fail open
    parts, i = [], 0
    while i < len(argv):
        a = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else ""
        if a in ("--body", "-b"):
            parts.append(nxt); i += 2
        elif a.startswith("--body="):
            parts.append(a.split("=", 1)[1]); i += 1
        elif a in ("--body-file", "-F"):
            if nxt == "-":
                return "", False              # body on stdin: can't inspect
            try:
                parts.append(pathlib.Path(nxt).read_text())
            except OSError:
                return "", False
            i += 2
        else:
            i += 1
    return "\n".join(parts), True

ev = json.load(sys.stdin)
cmd = (ev.get("tool_input") or {}).get("command", "")

# Stop fires at end of turn, so the last-rendered report can be one turn stale.
# Re-render now, before checking, so the PR can never carry an out-of-date report.
try:
    subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).with_name("render_report.py"))],
        input=json.dumps({"hook_event_name": "Stop",
                          "session_id": ev.get("session_id")}),
        text=True, timeout=10, capture_output=True)
except Exception:
    pass                                       # a stale report beats a stuck hook
text, checkable = body_text(cmd)

if not checkable:
    print(json.dumps({"systemMessage":
        "Skill report not verified: PR body was passed in a form the hook can't read."}))
    sys.exit(0)
sid = ev.get("session_id", "unknown")
root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
report = root / ".claude" / "artifacts" / f"skill-report-{sid}.md"

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

if MARKER not in text:
    deny(f"PR body is missing the skill report. Read {report} and append its "
         "contents to the PR body, then retry.")

# Marker present is not enough: an old report pasted once would pass forever.
# Every skill in the freshly rendered report must appear in the body.
if report.exists():
    want = {l.split("`")[1] for l in report.read_text().splitlines()
            if l.startswith("| `")}
    missing = sorted(w for w in want if w not in text)
    if missing:
        deny("The skill report in the PR body is out of date - missing: "
             + ", ".join(missing)
             + f". Re-read {report} and replace the report section, then retry.")

sys.exit(0)
