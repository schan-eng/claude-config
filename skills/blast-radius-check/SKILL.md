---
name: blast-radius-check
description: After a heavy implementation is done, analyze the changed components and map the blast radius — what areas of the stack a bug in this change could break if released to prod as-is. Use when the user says "blast radius", "what could this break", "is this safe to ship/release", "pre-release risk check", or right after finishing a large/risky implementation and before opening a PR or cutting a release.
---

# Blast Radius Check

Goal: given a finished implementation, determine **what else in the system a bug in this change could take down if it shipped to prod as-is** — and how hard the failure would be to detect and reverse. This is a risk-mapping pass, NOT a correctness review (use `/code-review` or `self-review` for "is this code correct"). The question here is: *"assume a bug slips through — what is the worst it can reach, and would we catch it?"*

Do not modify code. Produce an analysis and a report.

## Step 1 — Establish the change set

Determine exactly what changed. In order of preference:
1. If `$ARGUMENTS` names a ref/range/PR, use it (e.g. `git diff main...HEAD`, or `gh pr diff <n>`).
2. Otherwise default to the working diff vs the default branch: `git fetch` then `git diff --stat $(git merge-base HEAD origin/main)...HEAD` plus uncommitted changes (`git status`, `git diff`).
3. If nothing is staged/committed, ask the user what to scope against.

List the changed files grouped by **component/layer**. In this monorepo that means at minimum: `apps/next` (frontend), `backend/api` (tRPC API), `backend/task-worker` (Hatchet workflows), `packages/*` (shared — high blast), `packages/prisma` (schema/migrations — often irreversible), `tools/kindo-cli` + `deploy/` + `helm_chart/` (install/release), infra/Terraform. If a `monorepo-architecture` skill exists, consult it for layer boundaries and dependency rules.

## Step 2 — Trace the dependents (reverse dependency map)

For each changed symbol/module, find **who consumes it** — that is the blast radius surface. The change itself is only the epicenter.
- Shared package / exported util / type → grep for importers across all workspaces. Changes here radiate widest.
- tRPC procedure / service → which screens, agents, workflows, or other services call it.
- Prisma schema / migration → every query touching those tables/columns; whether the migration is backward-compatible (additive vs destructive); rollback story.
- Env var / feature flag / config → every runtime that reads it; default-on vs default-off; build-time vs runtime.
- Helm/deploy/CLI change → which services redeploy, install ordering, post-install scripts, secrets.

For a large diff, fan this out: launch parallel `Explore` agents (one per changed component) to find dependents, so you map the whole surface without serializing. Wait for their results before writing the report.

## Step 3 — Reason about failure modes per affected area

For each affected area, ask the "what if there's a bug here" questions:
- **What concretely breaks?** (e.g. "chat send 500s", "agent runs silently stop firing", "migration locks the table", "all orgs lose model X").
- **Blast radius tier** — score each:
  - `LOCAL` — one screen/endpoint/feature, single user impact.
  - `ORG` — degrades a whole org/tenant.
  - `CLUSTER` — degrades the whole deployment / all users on it.
  - `RELEASE` — ships broken to every self-managed customer / irreversible data effect.
- **Reversibility** — feature-flagged (flip off), config (re-roll), code (redeploy/rollback), or **irreversible** (data migration, deleted column, dropped data). Irreversible + high tier is the top concern.
- **Detection** — would something catch it before customers do? Existing unit/integration tests, the `kindo validate` e2e gate, type-checking, monitoring/alerts? Or would it fail silently? Call out anything in the blast radius that has **no test/validation coverage** — silent + irreversible is the worst quadrant.

## Step 4 — Flag the cross-cutting amplifiers

Explicitly check whether the change touches any of these blast-radius multipliers, and surface them even if Step 2 didn't:
- **DB migrations** — destructive/locking operations, non-backward-compatible schema during rolling deploy.
- **Auth / authorization / security boundaries** — a bug here is org-data-leak class, not "broken feature" class.
- **Shared packages / widely-imported code** — one bug, many callers.
- **Feature flags / env defaults** — is the new path default-on (ships hot) or behind a flag (safe ramp)?
- **Release/install path** (kindo-cli, helm, post-install, secrets) — a bug here can brick a customer's *install*, not just a feature.
- **Background/async** (Hatchet workflows, crons, webhooks) — failures here are often silent (no user staring at a 500).

## Step 5 — Report

Output a concise, ranked report:
1. **One-line verdict** — safe to ship as-is / ship behind a flag / hold. State the single biggest risk.
2. **Blast radius table** — affected area | what breaks | tier (LOCAL/ORG/CLUSTER/RELEASE) | reversible? | detected by?
3. **Top risks** — the few high-tier × irreversible × undetected items, with the reasoning.
4. **Recommended guardrails before release** — concrete, e.g. "put X behind feature flag Y for a staged ramp", "add an e2e/integration assertion for Z (currently uncovered)", "make migration additive + backfill separately", "run `kindo validate` against a fresh install".

Keep it actionable: the value is telling the user *where to look and what to gate*, not a generic risk lecture. If the change is genuinely low-radius (e.g. an isolated leaf component, fully flagged), say so plainly rather than inventing risk.
