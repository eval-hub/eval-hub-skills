---
name: evalhub-bug-review
description: >
  Bug-focused review of an eval-hub or eval-hub-contrib pull request, branch,
  commit range, or uncommitted change. Adapts the Bugbot workflow to both
  repositories: eval-hub's Go service (SQL storage, runtimes, sidecar, MCP
  server, OpenAPI) and eval-hub-contrib's Python FrameworkAdapter packages
  (provider.yaml catalog, JobPhase contract, credentials, Containerfiles,
  per-adapter CI). Returns a severity-ranked findings table with file:line
  locations. It finds defects only and never edits code. Use when reviewing an
  eval-hub PR, doing a pre-merge review, or when the user asks for a "bug
  review", "review this PR", or a second pair of eyes on a change.
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

Never assume the working directory matches the target. For a PR, read the URL;
for a branch, inspect the tree:

```bash
gh pr view <n> --json url,baseRefName --jq '.url'
test -d internal/eval_hub && echo "eval-hub service (Go)"
ls adapters/*/provider.yaml 2>/dev/null | head -3   # contrib adapters
test -f adapters/<name>/main.py && echo "contrib adapter"
```

- Go service signals: `internal/eval_hub/`, `pkg/api/`, `docs/src/openapi.yaml`,
  `cmd/eval_runtime_sidecar/`.
- Contrib signals: `adapters/<name>/main.py`, `provider.yaml`, `Containerfile`,
  `requirements*.txt`, `meta/job.json`, `collections/*.yaml`,
  `.github/workflows/test-<name>.yml`.
- A diff can contain both (for example a contrib adapter plus a collections
  entry); run both checklists and say so in `Coverage`.

State the repository and the checklist range you are using in the report's
summary line. Everything below that names Go commands applies only to eval-hub;
contrib verification commands are in Step 5b.

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
unasked. An empty diff — or one touching only generated or ignored files — ends
the review in one sentence; do not invent findings. What counts as ignorable
differs by repository:

- eval-hub: `docs/openapi*.{yaml,json}`, `docs/index*.html`, `bin/`, coverage
  output.
- contrib: `.venv/`, `__pycache__/`, `.pytest_cache/` (should never be
  committed), and a `requirements.lock` that changed without a matching
  `requirements.txt`/`constraints.txt` change (a lock-only bump is usually
  Dependabot, but say which packages moved).

For a very large diff review by group and say which groups you covered:

- eval-hub: handlers → storage → runtimes → routes → tests → docs.
- contrib: `provider.yaml` → `main.py` → shared modules → tests →
  `Containerfile`/requirements → `Makefile`/CI → README/docs/collections.

### Step 2 — Build context beyond the diff hunks

Read the surrounding function/file and its test file for every changed file; a
hunk alone rarely shows the invariant that broke. Collect:

1. **Intent** — PR body, linked issue, commit type. A `refactor` that changes
   behavior, or a `fix` with no regression test, is a finding candidate.
   Deploy-order and external-dependency sentences ("deploy its images with these
   catalog changes", "the adapter changes are in contrib PR #N") are claims to
   verify, not context — see [checklists.md](checklists.md) §12 and
   [checklists-contrib.md](checklists-contrib.md) §20.
2. **Contract surfaces** — by repository:
   - eval-hub: `docs/src/openapi.yaml`, `pkg/api` structs,
     `internal/eval_hub/messages/messages.go`, `internal/eval_hub/constants/*`,
     DB schema/migrations, `sidecar_config.json` keys, MCP tool schemas.
   - contrib: the adapter's `provider.yaml` (benchmark ids, `metrics`,
     `parameters`, `agent:` block), the `FrameworkAdapter.run_benchmark_job`
     signature, `meta/job.json`, `collections/*.yaml`, the credential rules in
     `docs/model-role-auth.md`, the `Containerfile` `ENTRYPOINT`, and the README
     tables that advertise the adapter.
3. **Blast radius** — the invariant each change can break:
   - eval-hub: tenant/owner scoping, job state machine, transaction atomicity,
     context lifetime, HTTP status contract, cluster resource lifecycle,
     generated docs.
   - contrib: whether the job runs at all in a disconnected pod, whether the
     reported metric is the one the collection/dashboard reads, whether a
     credential can be silently substituted, whether a child process or
     temporary file outlives the job, whether the shipped image contains the
     code that was tested.
4. **Callers** — eval-hub: grep call sites of every changed exported function or
   storage method. contrib: grep the other adapters that import the same helper
   (`_hf_offline.py`, `judge_auth.py`, `subprocess_utils.py`,
   `scoring_context.py`), plus the eval-hub `config/providers/<name>.yaml` and
   the docs that describe the adapter. A shared helper changed for one adapter
   silently changes the others.

### Step 3 — Fast path: Bugbot subagent (Cursor only)

If a `bugbot` subagent exists, launch exactly one (`subagent_type: "bugbot"`, not
in the background unless asked) without computing the diff first, and give it the
repository path, `Diff: branch changes` (or `uncommitted changes`, or `natural
language` + per-file `Change Description`), base branch and instructions. Retry
once, then continue with Step 4 — the checklist is the primary path. Reconcile
its output (de-duplicate, re-verify); without the subagent, go to Step 4.

### Step 4 — Run the checklist for the repository

**eval-hub (Go)** — work through [checklists.md](checklists.md) §1–§12, highest
yield first: multi-tenancy, context lifetime, errors/transactions, job state
machine, runtimes/sidecar, API contract/docs, security, observability, tests,
repo conventions, cross-repo adapter coupling. Three are easy to miss:

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

**eval-hub-contrib (Python)** — work through
[checklists-contrib.md](checklists-contrib.md) §13–§22 in order: adapter contract
and JobPhase lifecycle, provider catalog drift, credentials/roles/offline assets,
subprocess lifecycle, results/artifacts/MLflow, dependencies/Containerfile,
tests and CI wiring, cross-repo coupling, then the quick scan. Three are easy to
miss:

- **Declared ≠ implemented** — every `benchmarks[].id`, `benchmarks[].metrics`
  and `parameters[].name` in `provider.yaml` must be dispatched and read by
  `main.py`; CI only checks that the file exists and parses
  (`.github/scripts/validate_provider.py`), so drift here ships silently.
- **JobPhase contract** — phases in order, `PERSISTING_ARTIFACTS` only when
  `config.exports.oci` is set, never emit `COMPLETED` manually, FAILED carries
  `MessageInfo`, only `status`/`phase` are forwarded.
- **Credential substitution** — role keys come from `model.auth.secret_ref` via
  `read_model_auth_key`/`resolve_model_credentials`; a new env-var or inline-URL
  fallback re-introduces the silent judge/target substitution that
  `docs/model-role-auth.md` and PRs #263/#297/#304 removed.

### Step 5 — Verify each finding before reporting

For every candidate: quote the exact lines; name the failure mode (input/sequence
→ wrong outcome) or downgrade it to a question; confirm it is not guarded
elsewhere (validation, middleware, storage wrapper, caller — in contrib: SDK
wrapper, sidecar, `finally` cleanup, CI workflow); confirm the diff introduced it
— pre-existing bugs once, labelled "pre-existing, not introduced here". Verify
read-only where cheap, and never let a tool mutate the working tree unasked.

**5a — eval-hub (Go):**

```bash
gofmt -l .                # lists unformatted files; make fmt would rewrite them
make lint && go build ./...
go test ./internal/eval_hub/<pkg>/... -run '<TestName>' -count=1
make verify-api-docs      # only when docs/src/openapi.yaml changed
git diff --stat           # must be unchanged by the review
```

**5b — eval-hub-contrib (Python):** there is no `make lint`/`gofmt` here, and
`make test-<adapter>` creates `.venv` and installs packages. Prefer the
side-effect-free checks first, and reuse an existing adapter venv when present:

```bash
git diff --stat                                   # unchanged by the review
# syntax only, no __pycache__ written
python3 -c 'import ast; ast.parse(open("adapters/<name>/main.py").read())'
# provider.yaml parses and its catalog is what you claim it is
# (bare python3 usually lacks pyyaml; uv is used across this repo)
uv run --quiet --with pyyaml python - <<'PY'
import pathlib, yaml
for p in sorted(pathlib.Path("adapters").glob("*/provider.yaml")):
    d = yaml.safe_load(p.read_text()) or {}
    print(p.parent.name, "id=", d.get("id"), "type=", d.get("type"),
          "benchmarks=", len(d.get("benchmarks") or []))
PY
# one adapter's suite, offline tests only (CI uses -m "not local")
cd adapters/<name> && .venv/bin/python -m pytest tests/ -q -m "not local"
# optional style check only for adapters that ship a ruff.toml
.venv/bin/python -m ruff check .
```

If no `.venv` exists, do not run `make test-<adapter>` just to see output: run
`python3 -m pytest` only if the runtime deps are already importable, otherwise
report the test as **not run** in `Coverage` and say why. `make image-<adapter>`
and `podman build` are out of scope for a review — say the image was not built
rather than guessing.

Mark each finding **confirmed** (provable from code or reproduced) or
**suspected** (needs runtime/cluster/network conditions).

### Step 6 — Report

Use [report-template.md](report-template.md): a summary line naming the
repository, a table sorted highest severity first with exactly
`Severity | Location (file:line) | Finding`, a `Details` block per actionable
finding (snippet, failure mode, suggested direction — **no patch** unless asked),
then `Coverage`: what you reviewed, what you could not (for example `@cluster`
paths in eval-hub, `local`-marked adapter tests or an unbuilt image in contrib),
open questions. If nothing is wrong, say
`No bugs found in this diff (M files reviewed).` with no padding.

### Step 7 — Optional follow-ups (only when asked)

- **Post to the PR** — `gh pr review` or `gh api
  repos/{owner}/{repo}/pulls/<n>/comments`; show the text, get confirmation.
- **Fix the findings** — separate pass, regression test first, then the
  repository's own gate:
  - eval-hub: `make fmt lint` and `go test ./internal/... ./cmd/... ./pkg/...`.
  - contrib: the adapter's suite (`.venv/bin/python -m pytest tests/ -q -m "not
    local"`, plus `ruff check` when the adapter ships a `ruff.toml`).
- **Commit** — Conventional Commits with the adapter as scope
  (`fix(lighteval): ...`); contrib enforces it with commitizen
  (`.cz.toml`, `cz check --rev-range origin/main..HEAD` in CI).
  - eval-hub: sign off with `-s` and add exactly one trailer from
    `make -s assisted-by-trailer`; never guess it.
  - contrib: there is no `assisted-by-trailer` target. Match the trailers the
    repository already uses (`Assisted-by: <model> (<harness>)` and
    `Signed-off-by: ...`), and ask rather than inventing a model name.

## Additional resources

- eval-hub rules: [AGENTS.md](https://github.com/eval-hub/eval-hub/blob/main/AGENTS.md), [ARCHITECTURE.md](https://github.com/eval-hub/eval-hub/blob/main/ARCHITECTURE.md), [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub/blob/main/CONTRIBUTING.md)
- eval-hub API: [docs/src/openapi.yaml](https://github.com/eval-hub/eval-hub/blob/main/docs/src/openapi.yaml); FVT tags: [tests/features/README.md](https://github.com/eval-hub/eval-hub/blob/main/tests/features/README.md)
- contrib rules: [AGENTS.md/CLAUDE.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/CLAUDE.md), [CONTRIBUTING.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/CONTRIBUTING.md) (provider.yaml schema, `metrics_schema`/`ResultType`)
- contrib contract: [JobPhase lifecycle](https://github.com/eval-hub/eval-hub-contrib/blob/main/README.md#jobphase-lifecycle), [model-role-auth.md](https://github.com/eval-hub/eval-hub-contrib/blob/main/docs/model-role-auth.md), [adapters/mteb/provider.yaml](https://github.com/eval-hub/eval-hub-contrib/blob/main/adapters/mteb/provider.yaml)
- Depth: [checklists.md](checklists.md) (eval-hub), [checklists-contrib.md](checklists-contrib.md) (contrib); output: [report-template.md](report-template.md)
