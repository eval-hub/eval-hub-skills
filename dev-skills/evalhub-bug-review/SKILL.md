---
name: evalhub-bug-review
description: >
  Bug-focused review of an eval-hub pull request, branch, commit range, or
  uncommitted change. Adapts the Bugbot workflow to eval-hub's Go service, SQL
  storage, runtimes, sidecar, MCP server, and OpenAPI conventions, then returns a
  severity-ranked findings table with file:line locations. It finds defects only
  and never edits code. Use when reviewing an eval-hub PR, doing a pre-merge
  review, or when the user asks for a "bug review", "review this PR",
  "/review-bugbot", or a second pair of eyes on a change.
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

Defect-finding review of an eval-hub PR, branch, commit range, or working tree:
Cursor's `/review-bugbot` shape plus the bug classes that bite eval-hub — tenant
scoping, context lifetime, rollback, generated-doc drift, runtime leaks, the
sidecar contract, cross-repo adapter coupling. Read [checklists.md](checklists.md)
before Step 4; rate findings with [report-template.md](report-template.md).

Invoke from **Cursor** by asking for "review PR 1234 with the evalhub-bug-review
skill" or attaching `@dev-skills/evalhub-bug-review/SKILL.md`, from **Claude
Code** with `/evalhub-bug-review`, from **Codex CLI** with the same file attached.
A failing CI FVT scenario belongs to `fix-fvt-test`, a threat-model pass to
`review-security`, style nits to `make fmt lint`.

## Procedure

Follow the steps in order. Do not skip Step 2 or Step 5.

### Step 1 — Resolve the review target

Accept a PR number/URL, branch, commit range, or "uncommitted". **Validate** that
a PR number matches `^[0-9]+$` before interpolating it into a shell command, and
resolve the base branch first (`gh repo view --json defaultBranchRef --jq
'.defaultBranchRef.name'`) — never assume `main`.

```bash
gh pr view <n> --json number,title,url,state,isDraft,author,baseRefName,headRefName,body,files
gh pr diff <n>
gh pr view <n> --json commits --jq '.commits[] | "\(.oid[0:8]) \(.messageHeadline)"'
mb=$(git merge-base "origin/<base>" HEAD)   # branch target: diff from merge base
git diff --stat "$mb"...HEAD && git diff "$mb"...HEAD
git status --porcelain && git diff && git diff --cached   # uncommitted target
```

Stay read-only: never check out, stash, rebase, or reset the working tree
unasked. An empty diff — or one touching only generated files/lockfiles — ends
the review in one sentence; do not invent findings. For a very large diff review
by group (handlers → storage → runtimes → routes → tests → docs) and say which
groups you covered.

### Step 2 — Build context beyond the diff hunks

Read the surrounding function/file and its test file for every changed file; a
hunk alone rarely shows the invariant that broke. Collect:

1. **Intent** — PR body, linked issue, commit type. A `refactor` that changes
   behavior, or a `fix` with no regression test, is a finding candidate.
   Deploy-order and external-dependency sentences ("deploy its images with these
   catalog changes", "the adapter changes are in contrib PR #N") are claims to
   verify, not context — see [checklists.md](checklists.md) §12.
2. **Contract surfaces** — `docs/src/openapi.yaml`, `pkg/api` structs,
   `internal/eval_hub/messages/messages.go`, `internal/eval_hub/constants/*`, DB
   schema/migrations, `sidecar_config.json` keys, MCP tool schemas.
3. **Blast radius** — the invariant each change can break: tenant/owner scoping,
   job state machine, transaction atomicity, context lifetime, HTTP status
   contract, cluster resource lifecycle, generated docs.
4. **Callers** — grep call sites of every changed exported function or storage
   method; a signature or semantics change with untouched callers is a common
   eval-hub bug.

### Step 3 — Fast path: Bugbot subagent (Cursor only)

If a `bugbot` subagent exists, launch exactly one (`subagent_type: "bugbot"`, not
in the background unless asked) without computing the diff first, and give it the
repository path, `Diff: branch changes` (or `uncommitted changes`, or `natural
language` + per-file `Change Description`), base branch and instructions. Retry
once, then continue with Step 4 — the checklist is the primary path. Reconcile
its output (de-duplicate, re-verify); without the subagent, go to Step 4.

### Step 4 — Run the eval-hub bug checklist

Work through [checklists.md](checklists.md) §1–§12, highest yield first:
multi-tenancy, context lifetime, errors/transactions, job state machine,
runtimes/sidecar, API contract/docs, security, observability, tests, repo
conventions, cross-repo adapter coupling. Three are easy to miss:

- **Identity** — `h.getStorage(ctx)` on every handler storage call,
  `s.canContinueRequest(...)` on new routes, tenant/owner on list *and*
  `total_count`, `--local` mode intact.
- **Cross-repo adapter contract** — if the diff touches
  `config/providers/*.yaml`, `tests/benchmarks/testdata`,
  `tests/benchmarks/generate`, or the `tests/features` jsonnet payloads, check
  the referenced `eval-hub/eval-hub-contrib` PR's merge state and the adapter that
  runs today on contrib's default branch, then classify the mismatch as reject
  (loud) or ignore (silent). Procedure and probes: §12.
- **Contract and generated docs** — `docs/src/openapi.yaml` is the only hand-edit
  target; `make documentation` regenerates the rest.

### Step 5 — Verify each finding before reporting

For every candidate: quote the exact lines; name the failure mode (input/sequence
→ wrong outcome) or downgrade it to a question; confirm it is not guarded
elsewhere (validation, middleware, storage wrapper, caller); confirm the diff
introduced it — pre-existing bugs once, labelled "pre-existing, not introduced
here". Verify read-only where cheap:

```bash
make fmt                  # no-op on a clean branch
make lint && go build ./...
go test ./internal/eval_hub/<pkg>/... -run '<TestName>' -count=1
make verify-api-docs      # only when docs/src/openapi.yaml changed
```

Never let a tool mutate the working tree unasked. Mark each finding **confirmed**
(provable from code or reproduced) or **suspected** (needs runtime/cluster
conditions).

### Step 6 — Report

Use [report-template.md](report-template.md): a summary line, a table sorted
highest severity first with exactly `Severity | Location (file:line) | Finding`, a
`Details` block per actionable finding (snippet, failure mode, suggested direction
— **no patch** unless asked), then `Coverage`: what you reviewed, what you could
not (for example `@cluster` paths), open questions. If nothing is wrong, say
`No bugs found in this diff (M files reviewed).` with no padding.

### Step 7 — Optional follow-ups (only when asked)

- **Post to the PR** — `gh pr review` or `gh api
  repos/{owner}/{repo}/pulls/<n>/comments`; show the text, get confirmation.
- **Fix the findings** — separate pass, regression test first, then `make fmt
  lint` and `go test ./internal/... ./cmd/... ./pkg/...`.
- **Commit** — Conventional Commits, `git commit -s`, one trailer from
  `make -s assisted-by-trailer`; never guess it.

## Additional resources

- Rules: [AGENTS.md](https://github.com/eval-hub/eval-hub/blob/main/AGENTS.md), [ARCHITECTURE.md](https://github.com/eval-hub/eval-hub/blob/main/ARCHITECTURE.md), [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub/blob/main/CONTRIBUTING.md)
- API: [docs/src/openapi.yaml](https://github.com/eval-hub/eval-hub/blob/main/docs/src/openapi.yaml); FVT tags: [tests/features/README.md](https://github.com/eval-hub/eval-hub/blob/main/tests/features/README.md); depth: [checklists.md](checklists.md); output: [report-template.md](report-template.md)
