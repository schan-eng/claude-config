#!/usr/bin/env python3
"""Render the ledger for one session into a markdown report.  Runs on Stop + SessionEnd."""
import json, os, sys, pathlib, collections, datetime

MARKER = "<!-- skills-used:v1 -->"
LABEL = {"direct": "direct (`/name`)", "model": "model-invoked",
         "model-failed": "model-invoked (failed)", "reference": "reference file",
         "instructions": "instructions"}

ev = json.load(sys.stdin)
sid = ev.get("session_id", "unknown")
root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
ledger = root / ".claude" / "skill-ledger" / f"{sid}.jsonl"
if not ledger.exists():
    sys.exit(0)

rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
skills = [r for r in rows if r["mode"] != "instructions"]

agg = collections.OrderedDict()
for r in skills:
    a = agg.setdefault(r["skill"], {"modes": [], "n": 0, "first": r["ts"], "last": r["ts"], "agents": set()})
    if r["mode"] not in a["modes"]:
        a["modes"].append(r["mode"])
    a["n"] += 1
    a["first"] = min(a["first"], r["ts"])
    a["last"] = max(a["last"], r["ts"])
    if r.get("agent_type"):
        a["agents"].add(r["agent_type"])

hm = lambda ts: ts[11:16]
out = [MARKER, "", "## Skills used", "",
       f"{len(agg)} skill(s) across {len(skills)} event(s) · session `{sid}`", "",
       "| Skill | Invoked as | Events | First | Last |", "|---|---|---|---|---|"]
for name, a in agg.items():
    modes = ", ".join(LABEL.get(m, m) for m in a["modes"])
    if a["agents"]:
        modes += f" · subagent: {', '.join(sorted(a['agents']))}"
    out.append(f"| `{name}` | {modes} | {a['n']} | {hm(a['first'])} | {hm(a['last'])} |")

instr = [r for r in rows if r["mode"] == "instructions"]
if instr:
    out += ["", "Instruction files loaded: " + ", ".join(f"`{r['skill']}`" for r in instr)]

out += ["", f"<details><summary>Raw ledger ({len(rows)} events)</summary>", "", "```jsonl"]
out += [json.dumps(r, separators=(",", ":")) for r in rows]
out += ["```", "", "</details>", ""]

art = root / ".claude" / "artifacts"
art.mkdir(parents=True, exist_ok=True)
(art / f"skill-report-{sid}.md").write_text("\n".join(out))
