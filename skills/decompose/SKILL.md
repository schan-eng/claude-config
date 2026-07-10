---
name: decompose
description: >-
  Decompose the current branch into small, fully independent modular PRs that
  each branch off and target a shared integration branch — mutually
  dependency-free buildups first in reading order, then one final wiring PR
  that ties the modules together to achieve the branch's objective — so a
  reviewer can read the work as an incremental story and approve each piece
  almost trivially, and buildups can merge in any order. Plan-first: always
  analyze and display a decomposition plan, and REQUIRE explicit human
  approval before creating any branch, commit, or PR. Invoke explicitly via
  `/decompose` (not auto-invoked) to decompose / split a branch into smaller
  reviewable PRs.
allowed-tools: Read, Grep, Glob, Bash, Skill
argument-hint: "[base-ref (default: origin/main)]"
user-invocable: true
disable-model-invocation: true
compatibility: Requires git and an authenticated GitHub CLI (gh) to open the decomposed PRs, and a repo with a runnable test suite (plus optional lint/build) so each compartment can be verified green. Invokes the /simplify and /self-review skills.
---

# Decompose — split a fat branch into small modular PRs

Big PRs hide intent and let slop slip through. This skill decomposes one large branch's objective into **minor objectives, each isolated in its own fully independent modular PR**, plus **one final wiring PR that ties the modules together to achieve the main objective**. A human reads the set like a story: each PR introduces one intention, is small enough to comprehend at a glance, and passes all tests on its own. Each small PR branches off and **targets a shared integration branch directly** (tracked by a checklist) — buildups have no dependencies on each other, so they can be reviewed and merged in any order, and **main is untouched until the whole feature is assembled and merged in one final PR**. The reviewer learns the feature incrementally and can confirm that *exactly* what's needed (and nothing more) enters the codebase.

## Prerequisites

`git`; an authenticated GitHub CLI (`gh auth status` succeeds) to open the decomposed PRs; and a repo with a runnable test suite (and ideally lint/build) so each compartment can be proven green. If `gh` isn't authenticated or no test command exists, say so up front — the plan can still be produced, but flag that PR creation / per-PR verification can't complete.

## PRIME DIRECTIVE — plan first, never auto-execute

This skill has two halves separated by a HARD GATE:

1. **Analyze + Plan** (read-mostly): understand the branch, design the split, and present a written plan.
2. **Execute** (creates branches/commits/PRs): ONLY after the human explicitly approves the displayed plan.

You MUST NOT create branches, commits, or PRs — or push anything — until the human has seen the plan and said to proceed. Present the plan and stop. If running in plan mode, surface it via `ExitPlanMode`; otherwise ask the human directly to approve before continuing. Treat silence or an ambiguous reply as "not approved."

The one mutation allowed before the gate is Phase 0's `/simplify` (cleanup only, reversible via git) because the split must be planned against already-clean code. Call this out when you run it.

---

## What you are optimizing: reviewer comprehension

The single metric is the **time and mental effort a reviewer spends to become confident** in a change. Everything below serves that. A PR is comprehensible when a reviewer can — in one sitting, with no outside context — answer five questions: *what is this, why now, what changed, what did NOT change, and how do I know it's safe.* Design every compartment and every PR description to answer those five up front. Hold this bar for each PR:

- **One concept per PR.** A reviewer holds one idea at a time. Never mix a refactor with a behavior change, or two intentions, in a single PR.
- **No surprises in the diff.** Mechanical noise — renames, file moves, formatting, generated files, lockfiles — drowns the lines that matter. Isolate it into its own "no-thinking-required" PR so the diffs that need thought are pure signal.
- **Teach, don't just show.** The PR body points the reviewer's eye at the 1–3 lines that carry the meaning and states what's deliberately absent, so they aren't hunting for missing wiring.
- **Introduce vocabulary before use.** A type/helper/concept lands in a buildup PR (earlier in reading order) and is consumed **only by the wiring PR** — so each diff reads with everything it references already understood. Buildup PRs never consume each other's code; every cross-compartment import lands in wiring.
- **Stay within a cognitive budget, under a hard 5-PR cap.** Prefer a PR a reviewer grasps in ~5 minutes (≈ ≤200 net logic lines, one subsystem) — but never exceed **5 PRs total** for the set. When the budget and the cap collide, the cap wins: keep ≤5 coherent PRs and use the cover note + per-PR "Read this" pointers to make a larger one navigable. (Generated/mechanical lines don't count toward the per-PR budget.)
- **Each PR earns its approval alone.** A reviewer should be able to read PR *k* and say "yes, this is correct and harmless" without first re-deriving PRs 1…k-1. The description carries whatever prior context is needed.

---

## Phase 0 — Simplify the whole branch first (mandated)

Before analyzing anything, run the `/simplify` skill over the entire branch diff (vs the merge-base with the default branch). Splitting dirty code just multiplies the cleanup across PRs. Apply simplify's safe fixes, note what it skipped, and decompose the *result*.

If the working tree has unrelated uncommitted changes, tell the user and let them set them aside first — don't sweep them into the split.

## Phase 1 — Analyze the branch

Establish the exact change set, the same way a careful reviewer would:

1. Resolve the base ref: use `$ARGUMENTS` if given (a branch/ref to diff against); otherwise default to the repo's real default branch — `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback `origin/main`). Then `base=$(git merge-base <base-ref> HEAD)`. The decomposition source is the **cumulative diff from `base` to the current working state**, including uncommitted changes.
2. List changed files with churn: `git diff --stat "$base"` across **ALL paths — never scope the diff to one subdirectory.** A branch's work often spans services (e.g. a backend endpoint + the CLI that calls it); narrowing to `-- some/dir/` silently drops cross-cutting changes and yields an incomplete, mis-ordered split. Read every non-trivial hunk — you cannot group what you haven't read.
3. For each file/hunk, identify:
   - **Intention** — what feature/fix/capability it serves (group by *why*, not by file type).
   - **Kind** — new module, new function, edit to existing reachable code, config/flag, test, docs, dependency, migration, deletion.
   - **Reachability** — is it executed by a production entrypoint today, or is it inert (nothing imports/calls it yet)? This drives ordering.
   - **Dependencies** — what other hunks it needs to compile/run.
4. Write a one-line "what is this branch actually trying to do" thesis. The set of PRs must tell that story.
5. **Resolve the Linear ticket id** — it anchors every branch/PR/checklist name (see Naming). Extract it from the current branch name (match `[A-Za-z]+-[0-9]+`, e.g. `simon/eng-10751-…` → `ENG-10751`); if absent, scan recent commit subjects for a `[ENG-####]` tag (`git log -20 --format=%s`); if still none, ask the user for the ticket. If there's genuinely no ticket, fall back to a descriptive group slug and note that in the plan.

## Phase 2 — Decompose by intention (the core)

Group the hunks into compartments that each carry one coherent intention. **Hard cap: at most 5 PRs.** A large set is its own review burden — more than ~5 PRs to track, rebase, and merge in order outweighs the benefit of smaller diffs. So group by *intention* into ≤5 coherent units (the natural shape is often: backend/data → primitives → libraries → assembly → wiring). Within that cap, **decompose modularly**: every buildup compartment must stand alone — green against the base with **no dependency on any other compartment**. If buildup B needs code buildup A introduces, that's a re-seam signal: merge them into one compartment, or move the consuming line into wiring. The **only** compartment that may reference others is the wiring compartment, which ties the modules together to achieve the branch's objective. The shape is hub-and-spoke — independent modules plus one wiring hub — never a linear chain. Prefer smaller and minimize nesting/coupling — but the cap wins: when hitting it would force a 6th PR, merge the two most-related compartments instead and lean on the cover note + "Read this" pointers to keep the larger PR legible.

### The ordering principle: additive buildup, wiring last

Order compartments so **production behavior does not change until the final PR**. This is branch-by-abstraction / dark-launch applied to review:

- **Buildup PRs (1 … n-1)** add code that is **inert in production** — present, unit-tested in isolation, but not reachable from any live entrypoint. A change is production-inert when it is:
  - a new file/module nothing imports yet,
  - a new function/class/type no reachable path calls yet,
  - a new flag/config that defaults to *current* behavior (off),
  - tests, docs, or fixtures,
  - an added-but-unused dependency,
  - an additive, backward-compatible migration (new nullable column / new table that no running code reads yet).
- **Wiring PR (n, usually last)** is the small diff that makes it live: register the route/handler, import-and-call the new module from the existing entrypoint, flip the flag default, swap the old path for the new, delete the dead old code. This is the **only** PR that flips behavior, kept small enough to scrutinize line-by-line. It is also the **only PR with dependencies**: it merges into the integration branch last, after every buildup PR has landed, and is the sole place cross-compartment code may meet.

### Where the PRs land: an integration branch, not main

The small PRs do **not** merge into main. Every small PR **branches off the integration branch and targets it directly** — no PR is ever based on another PR's branch. The integration branch is the assembly area, tracked by a checklist. Buildup PRs merge in any order; the wiring PR merges last, once every buildup has landed. Main is untouched until the whole feature is assembled and the integration branch is merged in **one** final PR.

**Invariant: the integration branch is main-mergeable at every point.** Because each buildup is inert and dependency-free, any subset of merged buildup PRs leaves integration a behavior no-op vs main — merging integration into main early would break nothing. Only after the wiring PR lands does integration deliver the objective, and even then the lone production event is the `integration → main` merge, after every checklist box is ticked and the integration branch is green. The inert→wiring ordering still governs the *reading order* of the small PRs so the reviewer learns the feature incrementally.

Each compartment must satisfy:
- **Self-contained & green** — compiles and passes the full test suite on its own against the base (a buildup references only itself; only the wiring compartment references the buildups).
- **Independent** — a buildup depends on nothing but the base, never on another compartment. Can't satisfy that? Re-seam: merge the coupled compartments or push the coupling into wiring.
- **Inert until wiring** — if a buildup PR would change production behavior, it's mis-grouped; move the behavior-changing line to the wiring PR.
- **Minimal** — as few lines and as little nesting as the intention allows.
- **Covered** — ships the tests for the code it introduces (see "Tests travel with their code"); never defers them to a later PR.

*Illustrative example* — a branch that adds rate-limiting to an API endpoint splits into 3 PRs (`api rate limit v1/3 … v3/3`), all targeting the integration branch:
- `api rate limit v1/3: add RateLimiter` — the class + its unit tests; nothing imports it. **INERT**, independent.
- `api rate limit v2/3: add config` — the setting + parsing, defaulting to *unlimited* (today's behavior) + unit tests for parsing. **INERT** (the default preserves production), independent — v1 and v2 can merge in either order.
- `api rate limit v3/3: enforce in request handler` — imports `RateLimiter`, applies it on the live path (~15 lines) + an integration test asserting the Nth request gets 429. **LIVE — the only PR that flips behavior** (and only reaches production when the integration branch merges to main). The wiring PR: the only one that references v1 and v2, merged after both.

The reviewer reads v1 ("here's the mechanism"), v2 ("here's the knob, off by default"), v3 ("here's where it switches on") and scrutinizes prod risk only in v3.

### Tests travel with their code — every PR carries its own

No PR defers its tests to a later one ("tests coming next" is forbidden — each PR is green *and* covered on its own). Match the test level to what the PR introduces:
- **Buildup PR** ships the **unit tests** for the unit it adds — the new function/class/module is exercised in isolation in the same PR. A buildup PR that adds code with no accompanying unit test is incomplete: write the test or re-group.
- **Wiring PR** ships the **integration / end-to-end tests** for the now-connected behavior (plus any contract / migration / smoke tests the live path needs) — these can only be written once the pieces are wired, so they belong here.
- A **refactor/rename PR** carries the **updated** existing tests in the same PR, kept green.

State the level(s) present in each plan entry and confirm the PR's own change is actually *exercised* — a green suite with zero coverage of the new lines does not count.

### When "no impact until last" can't fully hold

Be honest. A pure bugfix, a security patch, or a change to a hot path is inherently live. Don't fake inertness. Instead: isolate each such change into its own minimal PR, place it as early as safe, and **flag it explicitly** in the plan as "has production impact" with the blast radius. The goal is that *most* of the set is inert and the live pieces are tiny and conspicuous.

### Boundary heuristics
- Prefer **whole-file** compartment boundaries — they're robust to build and to review. Split a single file across PRs only when its hunks serve genuinely different intentions, and note that intra-file splits are harder to keep green.
- Keep refactors separate from behavior changes. A rename/move PR should be a pure no-op a reviewer can approve without thinking; a behavior PR should contain no incidental renames.
- **Quarantine the noise.** Pure-mechanical churn (formatting, renames, moves, regenerated lockfiles/snapshots) goes in its own early "no-thinking-required" PR, so it never inflates a PR that needs real attention.
- One new dependency = its own (or a clearly-labeled) PR; reviewers scrutinize new deps.

### Flag slop — don't just relocate it

Splitting must not launder unnecessary code into a tidy-looking set of PRs. As you map hunks to intentions, anything that does NOT trace to the branch's thesis is a **cut candidate**: dead/unreachable code, speculative gold-plating, debug/commented-out leftovers, unrelated drive-by edits, abstractions with a single caller. Do not silently spread these across PRs. List them in the plan under **"Cut candidates"** with a one-line reason each, and let the human decide to drop them. A good decomposition usually makes the branch *smaller*, not just rearranged — surfacing what shouldn't ship is half the value of reviewing incrementally.

## Phase 3 — Present the plan, then STOP (HARD GATE)

The plan's audience is a busy human reviewer, not a machine. Lead with a **reading guide** — the cover note they read first — then a terse per-PR entry for each beat.

**Reading guide (the cover note):**
- the branch thesis in one sentence,
- the integration branch name + the checklist (in `docs/artifacts/<YYYY-MM>/<ticket-slug>/`, optionally also a hosted Artifact), and that every small PR merges into the integration branch (not main),
- the set as a numbered table of contents (reading order), each line = that PR's story beat, so the arc is visible before any diff is opened,
- the merge-order rule: buildup PRs are mutually independent and merge in any order; the wiring PR merges last,
- where behavior flips (which PR) and that main itself only changes at the final `integration → main` merge,
- totals: PR count, LOC, and the inert-vs-live split,
- any **Cut candidates** from Phase 2 (slop to drop before splitting).

**Naming — anchor everything on the Linear ticket (Phase 1, step 5).** Use the ticket id (e.g. `ENG-10751`) as the shared identifier across the whole group so the integration branch, every small PR, and the checklist are unmistakably one group and trace straight back to the ticket. Pick a short, descriptive **group label** too (from the thesis) for human readability in titles, plus each PR's position **out of the total count**:
- **Integration branch:** `<ticket-lower>-integration` — e.g. `eng-10751-integration`. The assembly area every small PR merges into.
- **Small PR branch:** `<ticket-lower>-v<k>-of-<n>-<beat-slug>` — e.g. `eng-10751-v1-of-5-archive-endpoint` (n ≤ 5).
- **PR title:** `[<TICKET>] <group label> v<k>/<n>: <brief beat>` — e.g. `[ENG-10751] kindo cli validate v1/5: archiveConversation endpoint`. The `[<TICKET>]` prefix matches the repo's commit/PR convention; the group label + `/<n>` make the group and its size visible from any one PR.
- **Checklist:** a committed markdown tracker that lives in the repo's **feature-artifacts directory**, NOT the repo root — in this monorepo that's `docs/artifacts/<YYYY-MM>/<ticket-slug>/CHECKLIST.md` (e.g. `docs/artifacts/2026-06/eng-10751-kindo-validate/CHECKLIST.md`). It's a tracked feature artifact that ships to main with the rest (the same convention as the specs/proposals/qa-evidence already there), and it anchors the umbrella PR. Optionally also render it as a hosted **Artifact** for sharing, and mirror an interactive `- [ ]` task list into the umbrella PR body for live ticking.
- **Final PR:** `integration → main`, titled `[<TICKET>] <group label>: integrate <n> PRs`.

`v<k>` is the **reading order** — merge order is free for buildups; only wiring-last constrains it — and the highest `v<n>` is the wiring PR. If no ticket was resolved, fall back to a descriptive `<group-slug>` in place of `<ticket-lower>` and drop the `[<TICKET>]` prefix — and say so in the plan. Show the proposed title **and** branch for every PR in the plan so the human approves the names and the count too. (If the count changes during planning, renumber so every name's `/<n>` agrees.)

**Per PR, in order** (keep every line to a short phrase — this doubles as the shipped PR body, which must stay brief):

```
v<k>/<n> — title: "[<TICKET>] <group label> v<k>/<n>: <brief beat>"   branch: <ticket-lower>-v<k>-of-<n>-<beat-slug>
  Base:       <ticket-lower>-integration   (every PR — buildups and wiring alike)
  Role:       buildup (independent, merges in any order) | wiring (ties together v1…v<n-1>; merges last)
  Why now:    <the intention this beat serves — one line>
  Read this:  <the 1–3 files/lines that carry the meaning>
  Does NOT:   <what's deliberately absent — so nothing reads as missing wiring>
  Production: INERT | LIVE — <blast radius if live>
  Tests:      <levels present — unit / integration / e2e — and what they assert>
  ~Review:    <minutes> · ~<LOC> lines · <#files>
```

Then a one-paragraph **narrative**: read v1→v<n>, what story unfolds, where behavior flips inside the integration branch, and that main changes only at the final `integration → main` merge once every box is ticked. The reviewer should finish the narrative already understanding the feature, so each diff merely *confirms* what they were told.

End with the explicit gate: state that execution will create the integration branch + checklist, then N small PRs targeting it (running `/simplify` + `/self-review` + tests on each), plus the draft `integration → main` PR; list any cut candidates awaiting a decision; and **ask for approval**. Do not proceed without it. Invite the human to re-group (merge/split/reorder), drop cut candidates, or adjust the narrative before approving — comprehension is subjective, so let them tune the seams.

## Phase 4 — Execute (ONLY after explicit approval)

The small PRs assemble onto an **integration branch**; main is touched once, at the end. When every small PR has merged into the integration branch, it equals the **intended** final state (the original branch, minus any approved cut candidates), and a single `integration → main` PR ships it.

1. **Capture the target.** Snapshot the full working tree (incl. uncommitted changes) as a commit: `target=$(git stash create)` — `git rev-parse HEAD` is WRONG when the tree is dirty. Then `git stash push -u` (the `-u` matters — it removes untracked files too, so they can't be swept into a compartment later). If the human approved dropping cut candidates, build the intended target on a scratch branch (everything except the cuts) and use *that* as `target`. Restore the user's tree (`git stash pop`) when done.
   - **Never `git add -A` / `git add .`** when building a compartment — that sweeps in any stray untracked file. Stage ONLY the compartment's paths: `git checkout "$target" -- <paths>` already stages exactly those; `git rm <path>` stages a deletion; `git add <explicit-path>` for anything else (e.g. the checklist). Then `git commit`.
2. **Create the integration branch + checklist** (names from the ticket — Phase 1, step 5). `git checkout -b <ticket-lower>-integration "$base"`. Add the tracking markdown in the repo's feature-artifacts dir — `docs/artifacts/<YYYY-MM>/<ticket-slug>/CHECKLIST.md` (NOT the repo root) — with: the thesis, the reading order and the merge rule (buildups in any order, wiring last), and a checkbox line per PR — `- [ ] v<k>/<n> — <beat> — INERT|LIVE — buildup|wiring — <PR link>` — ending with `- [ ] integration → main`. Commit (explicit path, never `git add -A`), push, and open the **draft** `integration → main` PR titled `[<TICKET>] <group label>: integrate <n> PRs`, mirroring the checklist into its body so the umbrella PR shows the whole arc. Optionally also render the checklist as a hosted Artifact and link it from the PR.
3. **Build each compartment `k` = 1 … n** (names: branch `<ticket-lower>-v<k>-of-<n>-<beat-slug>`, title `[<TICKET>] <group label> v<k>/<n>: <brief beat>`):
   - Branch off the **integration branch** — every compartment is built directly on `<ticket-lower>-integration` and contains only its own changes. The wiring compartment additionally merges each buildup branch in before adding its own changes; its PR still bases on integration (note in the body that its diff includes the buildups until they land) and merges last.
   - Apply **only** compartment `k`'s changes: whole-file → `git checkout "$target" -- <files>`; intra-file splits → `git apply --3way` a patch for just those hunks.
   - Run `/simplify` on this compartment's diff; apply safe fixes.
   - Confirm the compartment ships its own tests (unit for buildup; integration/e2e for wiring), then run the full test suite (and lint/build). It MUST be green AND the new/changed lines exercised. If red, the compartment isn't self-contained — fix the grouping; if uncovered, add the test before opening the PR.
   - Run `/self-review` (skill) on this compartment's diff; resolve real findings.
   - Commit, then `gh pr create --base <ticket-lower>-integration --title "[<TICKET>] <group label> v<k>/<n>: <brief beat>"`. **Every PR targets the integration branch directly** — buildups merge in any order, wiring last. Keep the **PR body brief** — a few short lines from the plan entry (one-line *why*, the "Read this" pointer, "Does NOT yet" if inert, `Production: INERT|LIVE`). No essays; the cover note + checklist hold the full arc.
4. **Reconstruction check (mandatory):** the wiring branch — every buildup branch merged in, plus the wiring changes — must satisfy `git diff <wiring branch> "$target"` empty **except** for the checklist file. (No wiring compartment? Merge all branches onto a throwaway assembly branch off integration and diff that instead.) A merge conflict while assembling means two compartments overlap; anything else differing means a hunk was dropped or duplicated — reconcile before handing off.
5. **Hand off — do NOT merge.** Merging each small PR into the integration branch, ticking the checklist, and finally merging `integration → main` are **human** actions (this skill never merges). Report: the integration branch, the checklist file/PR, every small-PR URL in reading order (buildups merge in any order, wiring last), which PR flips behavior, and the final `integration → main` PR. Note that main stays unchanged until that last merge, and remind the human to tick the checklist as each lands.

## Guardrails
- Never push or open any PR before the Phase 3 approval.
- Small PRs target the **integration branch directly**, never main and never each other. Buildup compartments must not depend on one another — the wiring branch is the only place compartments meet (it merges the buildup branches locally, and its PR still targets integration). Only the final `integration → main` PR touches main, and only humans merge it.
- Each PR green on its own — no "fixed in a later PR."
- Don't let `/simplify` or `/self-review` silently change a compartment's scope; the merged compartments must reconstruct to `target` (modulo the checklist file).
- If the branch is already small and single-intention, say so and recommend NOT splitting rather than inventing seams.
