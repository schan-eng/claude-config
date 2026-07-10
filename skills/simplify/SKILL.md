---
name: simplify
description: >-
  Post-implementation refinement pass: remove slop from recently changed code,
  tests, and docs — dead code, needless abstraction, duplication, comment
  noise, and stale references left by mid-development pivots. Behavior-
  preserving edits are applied directly; API/semantic changes are only
  reported. Invoked automatically by the personal stop hook after large
  changes, or manually as /simplify. Arguments: a file list (hook path),
  --diff <ref>, or empty to use the current uncommitted diff.
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
argument-hint: "[file list | --diff <ref>]"
user-invocable: true
compatibility: >-
  Works in any repo. Repo-specific heavy checks (scoped typecheck, knip) run
  only when the repo provides the commands; skipped silently otherwise.
---

# Simplify — post-implementation refinement pass

Clean up what was just implemented so the shipped output is clean, concise, and free of slop. This is a **concision gate**, not a defect gate — bug-finding belongs to `self-review`.

## Hard rules

- **Behavior-preserving edits only.** If an edit could change observable behavior, it goes in the report, not the diff.
- **Safe-only auto**: never auto-apply anything that changes exports, public API shape, function signatures used elsewhere, or semantics (including collapsing a helper into its single caller if the helper is exported). Report those in one line each instead.
- **Never widen scope** beyond the resolved file set. Sole exception: the stale-reference grep (below) may *read* anywhere, and may fix stale references it finds in docs/artifacts belonging to the current effort.
- **No subagents.** Run inline; this pass must stay cheap.
- Do not re-explain or justify edits in code comments. Apply, then summarize per the output contract.
- If there is nothing to do, say "Diff is already minimal." and stop.

## 1. Resolve scope and tier

- `$ARGUMENTS` is a file list (the stop-hook path): use it as-is.
- `$ARGUMENTS` starts with `--diff <ref>`: `b=$(git merge-base <ref> HEAD)`, then `git diff --name-only "$b"` plus `git ls-files --others --exclude-standard`.
- Empty: uncommitted changes — `git diff --name-only HEAD` plus untracked via `git ls-files --others --exclude-standard`.

Read the **diff** of tracked files (`git --no-pager diff -U10 HEAD -- <files>` or vs the merge-base), and full contents only for new/untracked files. Do not re-read whole files whose diff you already have.

**Tier**: if the hook's instruction stated a tier, use it. Otherwise compute: total changed lines ≤ 40 AND < 3 files → **micro** (taxonomy pass only, no heavy checks); otherwise **full** (taxonomy pass + conditional heavy checks).

Drop from scope: lockfiles, `*.d.ts`, minified/generated files, anything under `node_modules/`, `dist/`, build output.

## 2. Slop taxonomy — what to look for

Work through the diff hunks against these checklists. Fix what is safe; note the rest.

### Code

- **Dead weight**: unreachable branches, unused imports/variables/parameters, code kept "in case" with no caller.
- **Needless structure**: else-after-return, single-use flags, nesting that flattens with early returns, branching that collapses to an expression.
- **Duplication introduced by this change**: near-identical blocks within the diff — extract or unify (only when the extraction is private to the touched files; otherwise report).
- **Reinvention**: before keeping a new helper, grep for an existing util that already does it (mono principle: *extend, don't duplicate*). Swap to the existing one when the call is a drop-in.
- **Speculative generality**: options, parameters, generics, or abstraction layers with exactly one caller and no concrete second use. Inline private ones; report exported ones.
- **Defensive redundancy**: checks that cannot fail given the types, try/catch that swallows and rethrows or wraps nothing meaningful, duplicate validation of already-validated input.
- **Leftover debug**: `console.log`/`print`/dbg output, commented-out code, TODO markers for work that was actually done.
- **Type slop**: `any`, `as` assertions that a narrower declaration would avoid, redundant type annotations the compiler infers.
- **Comment slop**: comments that narrate the next line, restate the code, describe the change's history, or address a reviewer. Keep only comments stating constraints the code can't show.

### Tests

- Duplicate or fully-overlapping cases — collapse to the distinct behaviors.
- Copy-pasted setup where an existing factory/helper exists — use it.
- Assertions that test the mock instead of the code under test.
- Over-mocking: in repos with a testing standard (mono: `testing-standards` skill — banned mocks list), defer to it; don't invent local exceptions.

### Prose (md, docs, dev artifacts)

- Filler, restating the obvious, sections duplicating other docs — cut.
- **Stale-info sweep** (the ad-hoc-pivot check):
  1. Every identifier, path, command, flag, or option named in md files in scope must exist in the final code — verify each by grep; fix or delete mentions that don't.
  2. From the code diff, extract identifiers that were **removed or renamed** during this change. Grep the effort's docs for survivors: md files in scope, plus `docs/artifacts/**/<ticket>*` when a ticket id is resolvable from the branch name. Fix stale mentions.
  3. SPEC/progress-log claims must match what the implementation finally does — correct descriptions of approaches that were tried and abandoned mid-turn.

## 3. Conditional heavy checks (full tier only)

Run only what the repo provides; skip silently otherwise.

- **Scoped typecheck** of touched packages — mono: `yarn workspace <pkg> typecheck` per touched package (fall back to root `yarn typecheck` only if the change spans many packages). Run after applying edits; fix any type error your edits introduced.
- **Unused exports (knip)** — only if the diff **deleted or moved exports**: mono: `yarn check:unused` from the touched package dir (only some packages wire it). Flag newly-unused exports in the report; deleting them is an API-shape change (report, don't apply — unless the export was introduced in this same diff).

## 4. Output contract

At most 10 lines:

```
Simplify pass (<tier>, N files):
Applied: <count by category, e.g. "3 dead-code, 2 comment-slop, 1 util-reuse">
Stale refs fixed: <count, with file names if ≤3>
Suggested (not applied): <one line per safe-only exclusion, with file:line>
Checks: <typecheck/knip result or "skipped (micro)">
```

Or the single line: `Diff is already minimal.`
