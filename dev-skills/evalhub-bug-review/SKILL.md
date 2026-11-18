---
name: evalhub-bug-review
description: >
  Bug-focused review of an eval-hub or eval-hub-contrib PR, branch, commit range,
  or uncommitted change. Covers eval-hub's Go service (SQL storage, runtimes,
  sidecar, MCP, OpenAPI) and eval-hub-contrib's Python FrameworkAdapter packages
  (provider.yaml catalog, JobPhase contract, credentials, Containerfiles,
  per-adapter CI). Returns a severity-ranked findings table with file:line
  locations; finds defects only and never edits code. Use for a "bug review",
  "review this PR", a pre-merge review, or a second pair of eyes on a change.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - WebFetch
  # No Write / Edit: this skill reports findings and never changes the code
user-invocable: true
---

# EvalHub Bug Review

Defect-finding review of an eval-hub family PR, branch, commit range, or working
tree: Cursor's `/review-bugbot` shape plus the bug classes that actually bite
these repositories.

The skill covers **two** repositories with different languages, contracts and
tooling. Pick the checklist that matches the diff before reading code:

| Repository | What it is | Checklist | Dominant bug classes |
|---|---|---|---|
| `eval-hub/eval-hub` | Go service, SQL storage, runtimes, sidecar, MCP, OpenAPI | [checklists.md](checklists.md) §1–§12 | tenant scoping, context lifetime, rollback, job state machine, k8s resource leaks, generated-doc drift |
| `eval-hub/eval-hub-contrib` | Python `FrameworkAdapter` packages, `provider.yaml` catalog, collections, Containerfiles, per-adapter CI | [checklists-contrib.md](checklists-contrib.md) §13–§22 | JobPhase contract, provider/benchmark drift, credential roles, offline assets, subprocess/artifact lifecycle, packaging, dependency pinning |

Both share §12/§20: an eval-hub catalog change and a contrib adapter change are
only correct together, so a cross-repo claim in the PR body is a finding to
verify, never context to trust.

Invoke from **Cursor** by asking for "review PR 1234 with the evalhub-bug-review
skill" or attaching `@dev-skills/evalhub-bug-review/SKILL.md`, from **Claude
Code** with `/evalhub-bug-review`, from **Codex CLI** with the same file attached.
A failing CI FVT scenario in eval-hub belongs to `fix-fvt-test`, a threat-model
pass to `review-security`, style nits to the repository's own formatter/linter.

## Procedure

Follow the steps in order. Do not skip Step 0, Step 2 or Step 5.

### Step 0 — Identify the repository under review

Never assume the working directory matches the target: read the PR URL it was
supplied with, and run `gh pr view` against that URL or an explicit
`--repo <owner>/<repo>`, so a same-numbered PR elsewhere is not inspected. A
diff can contain both (a contrib adapter, its `collections/*.yaml` entry and the
matching eval-hub `config/providers/<name>.yaml` change), in which case run both
checklists and say so in `Coverage`. State the repository and checklist range in
the summary. Path signals and commands:
[procedure.md](procedure.md#step-0--identify-the-repository-under-review).

### Step 1 — Resolve the review target

Accept a PR number/URL, branch, commit range, or "uncommitted". Validate a PR
number with `^[0-9]+$`, resolve the base branch, diff from the merge base, and
include staged and unstaged changes for a working-tree target. Stay read-only.
An empty or generated-only diff ends the review — but a contrib
`requirements.lock`-only bump does not: review it for broken or incompatible
pins, name the packages that moved, and keep the §18 dependency checks. Commands
and ignorable paths:
[procedure.md](procedure.md#step-1--resolve-the-review-target).

### Step 2 — Build context beyond the diff hunks

Read the surrounding file and test file for every changed file: intent (PR body,
issue, commit type), contract surfaces (eval-hub: OpenAPI, `pkg/api`,
messages/constants, DB schema, sidecar config, MCP schemas; contrib:
`provider.yaml`, `run_benchmark_job`, `meta/job.json`, `collections/*.yaml`,
`docs/model-role-auth.md`, `Containerfile`), blast radius and callers of every
changed exported function or shared adapter helper. Deploy-order and
external-dependency sentences are claims to verify, not context (§12/§20).
Detail: [procedure.md](procedure.md#step-2--build-context-beyond-the-diff-hunks).

### Step 3 — Fast path: Bugbot subagent (Cursor only)

If a `bugbot` subagent exists, launch exactly one (not in the background unless
asked) without computing the diff first; retry once, then continue with Step 4.
Reconcile its output (de-duplicate, re-verify); without the subagent, go to
Step 4. Inputs:
[procedure.md](procedure.md#step-3--fast-path-bugbot-subagent-cursor-only).

### Step 4 — Run the checklist for the repository

Work through [checklists.md](checklists.md) §1–§12 for eval-hub and
[checklists-contrib.md](checklists-contrib.md) §13–§22 for contrib. Each set has
three easy-to-miss classes:

- eval-hub: identity (`h.getStorage(ctx)`, `s.canContinueRequest(...)`,
  tenant/owner on lists and `total_count`, `--local`); the cross-repo adapter
  contract (§12); and contract/generated docs (`docs/src/openapi.yaml` is the
  only hand-edit target).
- contrib: declared ≠ implemented (`benchmarks[].id`, `benchmarks[].metrics` and
  `parameters[].name` must be dispatched and read by `main.py`); the JobPhase
  contract (ordered phases, `PERSISTING_ARTIFACTS` only with
  `config.exports.oci`, no manual `COMPLETED`, FAILED carries `MessageInfo`,
  only `status`/`phase` forwarded); and credential substitution
  (`model.auth.secret_ref` via `read_model_auth_key`, never env-var or
  inline-URL fallbacks).

Checklist order and probes:
[procedure.md](procedure.md#step-4--run-the-checklist-for-the-repository).

### Step 5 — Verify each finding before reporting

For every candidate: quote the exact lines; name the failure mode
(input/sequence → wrong outcome) or downgrade it to a question; confirm nothing
guards it elsewhere (validation, middleware, storage wrapper, caller; in contrib
the SDK wrapper, sidecar, `finally` cleanup, CI workflow); and confirm the diff
introduced it — pre-existing bugs once, labelled "pre-existing, not introduced
here". Verify read-only, never mutating the tree. Mark each finding **confirmed**
or **suspected**. Probes: `gofmt -l`, `make lint`, targeted `go test`,
`make verify-api-docs` (eval-hub); `ast.parse`, the `provider.yaml` dump and an
existing adapter venv's `pytest` (contrib — no venv means **not run**, never
`make test-<adapter>` just to see output).
[procedure.md](procedure.md#step-5--verify-each-finding-before-reporting).

### Step 6 — Report

Use [report-template.md](report-template.md): summary line with repository and
checklist range, severity-sorted table (`Severity | Location (file:line) |
Finding`), a `Details` block per actionable finding (snippet, failure mode,
direction — no patch unless asked), then `Coverage`. If nothing is wrong, say
`No bugs found in this diff (M files reviewed).` with no padding.

### Step 7 — Optional follow-ups (only when asked)

Only when asked: **post to the PR** (`gh pr review` or the review-comments API,
showing the text first), **fix the findings** (separate pass, regression test
first, then the repository's own gate), or **commit** (Conventional Commits,
adapter scope for contrib, and the repository's own sign-off/trailer rules —
never guess the trailer). Detail:
[procedure.md](procedure.md#step-7--optional-follow-ups-only-when-asked).

## Additional resources

- eval-hub rules: [AGENTS.md](https://github.com/eval-hub/eval-hub/blob/main/AGENTS.md), [ARCHITECTURE.md](https://github.com/eval-hub/eval-hub/blob/main/ARCHITECTURE.md), [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub/blob/main/CONTRIBUTING.md)
- eval-hub API: [docs/src/openapi.yaml](https://github.com/eval-hub/eval-hub/blob/main/docs/src/openapi.yaml); FVT tags: [tests/features/README.md](https://github.com/eval-hub/eval-hub/blob/main/tests/features/README.md)
- contrib rules: [AGENTS.md/CLAUDE.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/CLAUDE.md), [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/CONTRIBUTING.md) (provider.yaml schema, `metrics_schema`/`ResultType`)
- contrib contract: [JobPhase lifecycle](https://github.com/eval-hub/eval-hub-contrib/blob/main/README.md#jobphase-lifecycle), [model-role-auth.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/docs/model-role-auth.md), [adapters/mteb/provider.yaml](https://github.com/eval-hub/eval-hub-contrib/blob/main/adapters/mteb/provider.yaml)
- Depth: [procedure.md](procedure.md) (step commands and signals), [checklists.md](checklists.md) (eval-hub), [checklists-contrib.md](checklists-contrib.md) (contrib); output: [report-template.md](report-template.md)
