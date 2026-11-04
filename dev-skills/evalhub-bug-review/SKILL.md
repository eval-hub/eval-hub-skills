---
name: evalhub-bug-review
description: >
  Bug-focused review of an eval-hub pull request, branch, commit range, or
  uncommitted change. Adapts the Bugbot code-review workflow to eval-hub's Go
  service, SQL storage, runtimes, sidecar, MCP server, and OpenAPI conventions,
  then returns a severity-ranked findings table with file:line locations.
  It finds defects only and never edits code. Use when reviewing an eval-hub PR,
  doing a pre-merge review, or when the user asks for a "bug review",
  "review this PR", "/review-bugbot", or a second pair of eyes on a change.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - WebFetch
  # No Write / Edit: this skill reports findings and must not modify the code
  # under review.

user-invocable: true
# Scripted procedure skill: follow the steps below rather than delegating the
# review to another model.
---

# EvalHub Bug Review

A defect-finding review for **this** repository. It follows the same shape as
Cursor's built-in `/review-bugbot` skill (compute the diff, find bugs, print a
severity-ranked table) but adds the bug classes that actually bite eval-hub:
tenant scoping, context lifetime, transaction rollback, generated-doc drift,
runtime resource leaks, and the sidecar contract.

Read [checklists.md](checklists.md) before starting Step 4. Print findings with
[report-template.md](report-template.md).

## What this skill is (and is not)

| This skill covers | Use instead |
|-------------------|-------------|
| Logic, data, contract, concurrency, and lifecycle defects | `fix-fvt-test` when a CI FVT scenario is already failing |
| Bugs reachable from the change being reviewed | `review-security` (or `SECURITY.md`) for a full threat-model pass |
| Severity-ranked `file:line` findings with a justification | Style/naming/import-order nits — `make fmt lint` and CI already enforce those |

Report **only** what you can justify from the diff plus the code it touches.
Never fix the code unless the user asks for that as a separate step.

## How to invoke

**Cursor:** In Agent chat, ask e.g. "Review PR 1234 with the evalhub-bug-review
skill", or attach `@dev-skills/evalhub-bug-review/SKILL.md`. The Cursor
built-in `/review-bugbot` also works and can be combined with Step 3 below.

**Claude Code:** From the repo root run `claude`, then `/evalhub-bug-review`
(or ask naturally; the skill matches on its description once named).

**Codex CLI:** Ask for "evalhub-bug-review on PR 1234" and attach
`dev-skills/evalhub-bug-review/SKILL.md`.

## Procedure

Follow the steps **in order**. Do not skip Step 2 or Step 5.

### Step 1 — Resolve the review target

Accept any of: PR number, PR URL, branch name, commit range, or "uncommitted".
**Validate before interpolating** a PR number into a shell command: it must
match `^[0-9]+$`. Reject anything else and ask the user to restate it.

Determine the base branch first (do not assume `main`):

```bash
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```

**PR target** (preferred, non-mutating):

```bash
gh pr view <number> \
  --json number,title,url,state,isDraft,author,baseRefName,headRefName,body,files
gh pr diff <number>
gh pr view <number> --json commits --jq '.commits[] | "\(.oid[0:8]) \(.messageHeadline)"'
```

**Branch target** (diff against the merge base, so unrelated base-branch commits
do not pollute the review):

```bash
git fetch origin --quiet
git merge-base "origin/<base>" HEAD
git diff --stat "$(git merge-base "origin/<base>" HEAD)"...HEAD
git diff "$(git merge-base "origin/<base>" HEAD)"...HEAD
```

**Uncommitted target:** `git status --porcelain`, `git diff`, `git diff --cached`.

Rules:

- Stay read-only. Do **not** check out, stash, rebase, or reset the user's
  working tree. Reviewing a PR through `gh pr diff` is enough and cannot clobber
  local work. If the user explicitly asks you to check out the branch, ask
  before stashing and only stash after they confirm.
- If the diff is empty (or only touches generated files/lockfiles), say so in
  one sentence and stop — do not invent findings.
- Sanity-check size: for very large diffs, review file group by file group
  (handlers → storage → runtimes → server/routes → tests → docs) and say which
  groups you covered.

### Step 2 — Build context beyond the diff hunks

For every changed file, read the surrounding function/file and its test file.
A hunk alone rarely shows the invariant that broke.

Collect:

1. **Intent** — PR body, linked issue, commit type (`feat`/`fix`/`refactor`).
   A `refactor` that changes behavior, or a `fix` with no regression test, is
   itself a finding candidate. Read the body for **deploy-order and external
   dependency statements** ("deploy its images together with these catalog
   changes", "the related adapter changes are in contrib PR #N", "already in
   upstream main"). Those sentences are claims to verify, not context — see
   [checklists.md](checklists.md) §12.
2. **Contract surfaces touched** — `docs/src/openapi.yaml`, `pkg/api` structs,
   `internal/eval_hub/messages/messages.go`, `internal/eval_hub/constants/*`,
   DB schema/migrations, `sidecar_config.json` keys, MCP tool schemas.
3. **Blast radius** — for each change, name the invariant it can break:
   tenant/owner scoping, job state machine, transaction atomicity, context
   lifetime, HTTP status contract, cluster resource lifecycle, generated docs.
4. **Callers** — grep for call sites of any changed exported function or
   storage method (`grep -rn 'FuncName' --include='*.go' .`). A signature or
   semantics change with untouched callers is a common eval-hub bug.

Architecture refresher: `ARCHITECTURE.md` (request flow, `ExecutionContext`,
`Storage`/`Runtime` abstractions, post-processing workloads).

### Step 3 — Fast path: Bugbot subagent (Cursor only)

If the `bugbot` subagent is available in the current harness, launch **exactly
one** subagent with:

- `run_in_background: false` unless the user explicitly asked for background
- `description: "Bugbot"`
- `subagent_type: "bugbot"`

Do not compute the diff yourself first. Use this exact prompt shape:

```text
Full Repository Path: <absolute repository path>
Diff: <one of: "branch changes", "uncommitted changes", "natural language">
Base Branch: <include only when the review is against a specifically known base branch>
Change Description: <required only when Diff is "natural language"; list each changed file and what changed in it>
Custom Instructions: <include only when the user gave specific review instructions; mention eval-hub focus areas>
```

Default to `branch changes`; use `uncommitted changes` when the user asked for
working-tree only. If the subagent cannot compute the diff, retry **once** with
`Diff: natural language` plus a per-file `Change Description`. If it fails
again, stop retrying and continue with Step 4 manually — the checklist review is
the primary path and is never blocked on the subagent.

Then **reconcile** Bugbot output with Step 4: de-duplicate, re-verify each claim
against the code, and drop anything you cannot justify. Bugbot findings that
fail verification must not reach the report.

If no `bugbot` subagent exists (Claude Code, Codex CLI, or Cursor without it),
go straight to Step 4.

### Step 4 — Run the eval-hub bug checklist

Work through [checklists.md](checklists.md) section by section. In priority
order (highest yield first):

1. **Multi-tenancy and identity** — every handler storage call goes through
   `h.getStorage(ctx)`; new routes call `s.canContinueRequest(...)`; list *and*
   `total_count` queries filter on tenant/owner; `--local` mode still works.
2. **Context lifetime** — request path uses `ctx.Ctx`; the only background
   detach point is `otel.DetachedContext(ctx.Ctx)` in `executeEvaluationJob`.
3. **Errors and transactions** — `serviceerrors.NewServiceError(messages.X, ...)`
   to clients, no double write after `w.Error`, and `.WithRollback()` on any
   `ServiceError` returned after a partial write inside `withTransaction`.
4. **Job state machine** — legal transitions, duplicate/out-of-order status
   events, cancel vs. complete, exactly-once finalization.
5. **Runtimes** — k8s resources created vs. deleted, label/DNS limits,
   `sidecar_config.json` key parity with `cmd/eval_runtime_sidecar`, local
   process/temp-dir cleanup.
6. **API contract and docs** — `docs/src/openapi.yaml` is the only hand-edit
   target; generated `docs/openapi.*` / `docs/index*.html` come from
   `make documentation`.
7. **Security** — no `#nosec`/`//gosec:disable`, no secret logging, traversal-safe
   file access, per-tenant credentials.
8. **Observability** — `constants.Log*` field names, bounded metric label
   cardinality, correct log levels.
9. **Tests** — regression test for a bug fix, branch coverage for new handler
   paths, correct FVT tags, no `t.Parallel()` with process-wide state.
10. **Repo conventions** — `make fmt lint`, conventional commit, DCO sign-off,
    `Assisted-by` trailer, four-file version bump, no generated files committed.
11. **Cross-repo adapter contract** — when the diff changes
    `config/providers/*.yaml`, `tests/benchmarks/testdata`,
    `tests/benchmarks/generate`, or `tests/features` jsonnet payloads, verify the
    adapter in `eval-hub/eval-hub-contrib` still matches. Confirm the referenced
    contrib PR's merge state and file list, read the adapter on contrib's default
    branch, and classify the mismatch as reject (loud) or ignore (silent). See
    [checklists.md](checklists.md) §12.

### Step 5 — Verify each finding before reporting

For every candidate finding:

1. Re-read the exact lines and quote the offending code in the finding.
2. Name the concrete failure mode: input/sequence → wrong outcome. If you cannot
   describe a trigger, downgrade it to a question or drop it.
3. Confirm the code is not already guarded elsewhere (validation, middleware, a
   storage wrapper, or a caller).
4. Confirm the diff introduced it (or made it reachable). Pre-existing bugs may
   be reported once, clearly labelled "pre-existing, not introduced here".
5. Where cheap and read-only, confirm with the toolchain:

```bash
make fmt                 # should be a no-op on a clean branch
make lint                # go vet + golangci-lint (.golangci.yml)
go build ./...
go test ./internal/eval_hub/<pkg>/... -run '<TestName>' -count=1
make verify-api-docs     # only when docs/src/openapi.yaml changed
```

Never let a tool run mutate the working tree in a way the user did not ask for.
Mark each finding as **confirmed** (reproduced or provable from code) or
**suspected** (needs runtime/cluster conditions).

### Step 6 — Report

Use the format in [report-template.md](report-template.md):

- One summary line: `Found N bugs in M changed files (Critical: a, High: b, Medium: c, Low: d)`.
- A compact markdown table with exactly these columns, sorted highest severity
  first: `Severity | Location (file:line) | Finding`.
- The `Location` column uses `path/to/file.go:123` (or `:120-134` for a range).
- Then a short `Details` list, one entry per actionable finding, with the code
  snippet, failure mode, and a suggested direction (**no patch** unless asked).
- Finish with `Coverage`: what you reviewed, what you could not (for example
  `@cluster`-tagged paths not exercised locally), and any open questions.

If nothing is wrong, say so plainly: `No bugs found in this diff (M files reviewed).`
Do not pad the report with style observations to look thorough.

### Step 7 — Optional follow-ups (only when asked)

- **Post to the PR:** summarize or inline-comment via `gh pr review` /
  `gh api repos/{owner}/{repo}/pulls/<n>/comments`. Show the exact text first and
  get confirmation before posting.
- **Fix the findings:** start a separate pass, add the regression test first,
  then run `make fmt lint` and `go test ./internal/... ./cmd/... ./pkg/...`.
- **Commit:** Conventional Commits, `git commit -s`, and one attribution trailer
  printed by `make -s assisted-by-trailer`. Never guess the trailer.

## Severity rubric (eval-hub)

| Severity | Meaning | Examples |
|----------|---------|----------|
| **Critical** | Data exposure, auth bypass, corruption, or crash on a normal path | tenant/owner scoping dropped so one namespace can read or mutate another's job; route added without `s.canContinueRequest`; token/secret written to logs; partial write committed by a `ServiceError` missing `.WithRollback()`; nil dereference/panic on a request path reachable by any tenant |
| **High** | Wrong results/state, resource leak, or contract break | illegal job state transition or duplicate finalization; a created k8s resource with neither an owner reference nor a delete path (for example a ref Secret left out of the cleanup sweep); submit returns 202 but the job is never started; wrong status code vs. `docs/src/openapi.yaml`; `pkg/api` JSON tag no longer matches the spec; background work bound to the request context so long jobs die on client disconnect; a catalog/fixture change that needs an unreleased adapter image, so role traffic silently falls back to the primary endpoint and credential |
| **Medium** | Wrong under specific conditions, or weakens operability | race only under concurrent events; off-by-one in pagination or `total_count`; missing nil guard for an optional API field; unbounded Prometheus label values; misleading log level; error path that loses the original error without `%w`; no regression test for the fixed bug |
| **Low** | Documentation drift, dead code, minor clarity | stale doc/comment describing old behavior; unused helper; an unfinished marker comment without a linked issue; generated-doc edit that also changed `docs/src` inconsistently |

## Do not report

- Formatting and lint output that `make fmt`, `go vet`, `golangci-lint`, or
  gitleaks already reports. Commit-hygiene issues (missing DCO sign-off, missing
  or duplicated `Assisted-by`, non-conventional subject) may be reported **once**
  as a Low finding when they would block merge — never as per-line review
  comments.
- Personal style preferences, "consider renaming", or speculative future-proofing.
- "Missing tests" with no concrete untested risk. If behavior is genuinely
  untested and risky, report it as Medium with the specific path that is uncovered.
- Pre-existing defects in unchanged code, unless the change makes them
  reachable or worse — then label them `pre-existing, not introduced here`.
- Anything you could not justify from the code in front of you.

## Additional resources

- Repository rules for agents: [AGENTS.md](https://github.com/eval-hub/eval-hub/blob/main/AGENTS.md)
- Architecture and request flow: [ARCHITECTURE.md](https://github.com/eval-hub/eval-hub/blob/main/ARCHITECTURE.md)
- Contributor standards, PR template, review process: [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub/blob/main/CONTRIBUTING.md)
- API source of truth: [docs/src/openapi.yaml](https://github.com/eval-hub/eval-hub/blob/main/docs/src/openapi.yaml)
- FVT tags and how to run scenarios: [tests/features/README.md](https://github.com/eval-hub/eval-hub/blob/main/tests/features/README.md)
- Deep checklists: [checklists.md](checklists.md)
- Output format: [report-template.md](report-template.md)

