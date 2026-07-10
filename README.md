# claude-config

Personal Claude Code user-level configuration, tracked in place at `~/.claude`.

Tracked (allowlist in `.gitignore` — everything else in `~/.claude` is ignored):

- `CLAUDE.md` — response-style rules injected into every session
- `settings.json` — model, hooks wiring, theme
- `skills/` — personal slash-command skills (`/remind-me`, `/simplify`, `/decompose`, `/worktree-branch`, `/blast-radius-check`)
- `hooks/` — deterministic post-implementation pipeline (`simplify-track-edits.sh`, `simplify-on-stop.sh`)

## Restore on a new machine

```bash
git clone git@github.com:schan-eng/claude-config.git ~/.claude-config-tmp
rsync -a ~/.claude-config-tmp/ ~/.claude/ && rm -rf ~/.claude-config-tmp
```

(Or clone directly into a fresh `~/.claude` before first run of Claude Code.)

Never commit: `history.jsonl`, `projects/`, `sessions/`, `shell-snapshots/`, plugin caches — session data and potentially sensitive transcripts. The allowlist gitignore enforces this.
