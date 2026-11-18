# EvalHub bug-review report template

Use exactly this shape for Step 6 of [SKILL.md](SKILL.md), and rate each finding
with the rubric in §2. Keep it compact: a reviewer should be able to read the
table, pick a row, and see the justification in `Details`.

## 1. Summary line

Whenever findings are reported, the summary must name both the repository under
review and the checklist range you ran:

```text
eval-hub (checklists.md §1–§12) — Found 3 bugs in 7 changed files (Critical: 1, High: 1, Medium: 1, Low: 0)
```

```text
eval-hub-contrib (checklists-contrib.md §13–§22) — Found 3 bugs in 7 changed files (Critical: 0, High: 2, Medium: 1, Low: 0)
```

No findings (the repository and range still say what was reviewed):

```text
eval-hub-contrib (checklists-contrib.md §13–§22) — No bugs found in this diff (7 files reviewed).
```

Empty diff:

```text
No diff to review — the branch matches origin/main (0 changed files).
```

## 2. Findings table

Exactly three columns, highest severity first. One row per finding. Keep each
example self-contained: its summary line, table and `Details` blocks must agree
on the finding count, severities and coverage. Do not mix Go and contrib rows in
one example.

**eval-hub (Go) example** — one Critical, one High, one Medium:

```markdown
eval-hub (checklists.md §1–§12) — Found 3 bugs in 7 changed files (Critical: 1, High: 1, Medium: 1, Low: 0)

| Severity | Location (file:line) | Finding |
|----------|----------------------|---------|
| Critical | internal/eval_hub/handlers/evaluations.go:612 | List query bypasses `h.getStorage(ctx)` and reads `h.storage` directly, so `total_count` is computed across all tenants. |
| High | internal/eval_hub/handlers/evaluations.go:488 | The job is marked `RUNNING` before the runtime create call, so a create failure leaves a job no pod will ever update. |
| Medium | internal/eval_hub/handlers/evaluations.go:530 | The count query runs before the filter is applied, so `total_count` can exceed the number of rows returned. |
```

**eval-hub-contrib (Python) example** — two High, one Medium, no Go rows:

```markdown
eval-hub-contrib (checklists-contrib.md §13–§22) — Found 3 bugs in 7 changed files (Critical: 0, High: 2, Medium: 1, Low: 0)

| Severity | Location (file:line) | Finding |
|----------|----------------------|---------|
| High | adapters/lighteval/main.py:245 | `create_oci_artifact` is called with `files_path=output_files[0].parent`, so per-task result files written to sibling directories are never uploaded. |
| High | adapters/mteb/provider.yaml:34 | `benchmarks[].id: mteb_summarization` is declared but `BENCHMARK_PRESETS` has no such key, so selecting the advertised benchmark fails the job at `INITIALIZING`. |
| Medium | adapters/lighteval/main.py:250 | The `else` branch reports "No OCI exports configured" even when exports *are* configured but `output_files` is empty, so a real upload miss looks like an intentional skip. |
```

Rules:

- `Location` is `path:line` or `path:start-end`; no line-less locations.
- Severity is one of `Critical`, `High`, `Medium`, `Low`.
- The finding column states the **defect and its consequence**, not the fix.
- Keep each cell to one or two sentences; detail goes below.
- Do not include a row you cannot justify from the code (see Step 5).

### Severity rubric (eval-hub and eval-hub-contrib)

Rate every row with this rubric; the label is what makes two reviews comparable.

| Severity | Meaning | eval-hub examples | eval-hub-contrib examples |
|----------|---------|-------------------|---------------------------|
| **Critical** | Data exposure, auth bypass, corruption, or crash on a normal path | tenant/owner scoping dropped so one namespace reads another's job; route added without `s.canContinueRequest`; token/secret written to logs; partial write committed by a `ServiceError` missing `.WithRollback()`; nil dereference on a request path | credential or secret logged, written into `evaluation_metadata`, or placed on a child process's command line; a judge/target credential silently substituted because a legacy inline URL is honoured; `overall_score`/results crash on the normal path (uncaught `ZeroDivisionError`, `KeyError` on every run) |
| **High** | Wrong results/state, resource leak, or contract break | illegal job state transition; created k8s resource with no owner reference or delete path; submit returns 202 but the job never starts; wrong status code vs. `docs/src/openapi.yaml`; background work bound to the request context | `run_benchmark_job` signature/return changed; declared benchmark/parameter not implemented (or vice versa) so a selected job fails or an advertised knob is a no-op; `FAILED` never reported so the job hangs; artifacts dropped because the upload path swallows siblings or runs after cleanup; a framework subprocess that ignores exit codes or timeouts and reports partial metrics; offline path broken so disconnected pods fail; credential-contract change not mirrored in `docs/model-role-auth.md`/eval-hub |
| **Medium** | Wrong under specific conditions, or weakens operability | race under concurrent events; off-by-one in `total_count`; unbounded Prometheus labels; missing `%w`; no regression test for the fix | `metrics_schema` `ResultType` wrong so the UI renders a distribution as a scalar; `PERSISTING_ARTIFACTS` gating inconsistent with `config.exports.oci`; adapter added without a CI workflow or `Makefile` aggregate entry; stale `requirements.lock` behind a changed `requirements.txt`; `.trivyignore` entry without expiry/reachability; log message that drops the framework's stderr; no regression test for the fix |
| **Low** | Documentation drift, dead code, minor clarity | stale comment; unused helper; unfinished marker comment | README/adapter table no longer matching the adapter; `agent:` hints or benchmark counts stale; `meta/job.json` out of date; duplicated metric extraction helper |

### Do not report

- Formatting and lint output the repository's own gate already reports:
  eval-hub `make fmt`/`go vet`/`golangci-lint`/gitleaks; contrib `ruff` (only
  `adapters/atif` and `adapters/evalhub-post-processor` ship a `ruff.toml`, and
  `make test-lm-eval` runs `ruff check` with defaults) or `cz check` for commit
  subjects. Commit hygiene (non-conventional subject, missing or duplicated
  trailers) may be reported **once**, as Low, when it would block merge — never
  as per-line review comments.
- Personal style preferences, "consider renaming", speculative future-proofing.
- "Missing tests" with no concrete untested risk. If behavior is genuinely
  untested and risky, report it as Medium with the specific uncovered path.
- Pre-existing defects in unchanged code, unless the change makes them reachable
  or worse — then label them `pre-existing, not introduced here`. This includes
  repository-wide gaps such as `adapters/guidellm/` having no `provider.yaml`,
  `ruler`/`swebench`/`tooleval` having no CI workflow, or the `builtin` vs
  `community` `type:` inconsistency: mention them once in `Coverage`, not as
  findings against an unrelated PR.
- Anything you could not justify from the code in front of you.

## 3. Details

One block per finding, same order as the table, labelled with the severity and
location. Include the snippet, the trigger, and a suggested direction. Each
example's blocks match its table rows exactly.

**eval-hub (Go) example** — blocks 1–3 for the Go table above:

````markdown
### 1. Critical — internal/eval_hub/handlers/evaluations.go:612

```go
jobs, total, err := h.storage.ListEvaluationJobs(limit, offset)
```

`HandleListEvaluations` builds storage from `h.storage` instead of
`h.getStorage(ctx)`, so the query is not scoped with `WithTenant`/`WithOwner`.
Any tenant listing jobs sees other tenants' rows, and `total_count` leaks the
global job count.

Trigger: `GET /api/v1/evaluations/jobs` with any `X-Tenant` value.

Status: confirmed (read path, no other scoping layer).
Direction: build storage through `h.getStorage(ctx)` before the list/count calls.
````

````markdown
### 2. High — internal/eval_hub/handlers/evaluations.go:488

```go
if err := h.markRunning(ctx, job.ID); err != nil {
    return err
}
if _, err := h.runtimes.Create(ctx, job); err != nil {
    return err
}
```

`markRunning` commits `RUNNING` before `runtimes.Create`. If the create call
fails, the handler returns the error without reporting `FAILED`, so the job stays
`RUNNING` with no pod and no path back to a terminal state.

Trigger: a runtime create error (quota exhausted, rejected pod spec).

Status: confirmed (error path returns before any status update).
Direction: create the runtime before transitioning, or report `FAILED` before
returning.
````

````markdown
### 3. Medium — internal/eval_hub/handlers/evaluations.go:530

```go
total, err := h.storage.CountEvaluationJobs(ctx)
jobs, err := h.storage.ListEvaluationJobs(ctx, filter, limit, offset)
```

The count ignores `filter`, so `total_count` includes jobs the list excludes and
pagination advertises pages that return no rows.

Trigger: `GET /api/v1/evaluations/jobs` with a filter that excludes some jobs.

Status: confirmed.
Direction: pass the same filter to the count query.
````

Status is `confirmed` (provable from code or reproduced) or `suspected` (needs a
cluster, MLflow, network or race condition). Never present `suspected` as
certain.

**eval-hub-contrib (Python) example** — blocks 1–3 for the contrib table above,
with the adapter's own vocabulary:

````markdown
### 1. High — adapters/lighteval/main.py:245

```python
artifact = create_oci_artifact(OCIArtifactSpec(files_path=output_files[0].parent))
```

Only the first output file's directory is uploaded. Per-task result files written
to sibling directories are never included, so the artifact is incomplete for any
job that splits output by task.

Trigger: a job with `exports.oci` set and more than one output directory.

Status: confirmed.
Direction: stage every referenced file under one directory, or use the job output
root.
````

````markdown
### 2. High — adapters/mteb/provider.yaml:34

```yaml
  - id: mteb_summarization
```

`provider.yaml` advertises `mteb_summarization`, but `MTEBAdapter.BENCHMARK_PRESETS`
has no such key and `_resolve_tasks` raises for an unknown id with no explicit
`tasks` parameter. A user who selects the advertised benchmark gets a `ValueError`
after the job is accepted and reported `INITIALIZING`.

Trigger: `POST /api/v1/evaluations/jobs` with `benchmark_id: mteb_summarization`
and no `tasks` parameter.

Status: confirmed (`BENCHMARK_PRESETS` and `_resolve_tasks` read; no other mapping).
Direction: add the preset in `main.py` or drop it from the catalog — and add a test
asserting every `benchmarks[].id` resolves.
````

````markdown
### 3. Medium — adapters/lighteval/main.py:250

```python
else:
    logger.info("No OCI exports configured")
```

The `else` branch runs whenever `output_files` is empty, including when
`config.exports.oci` is set but the framework wrote nothing. A real upload miss is
then logged as an intentional skip.

Trigger: `exports.oci` configured and the framework exits with no output files.

Status: confirmed.
Direction: gate the message on `config.exports.oci`, not on `output_files`.
````

## 4. Coverage

```markdown
**Coverage:** reviewed handlers, SQL storage, and their unit tests. Did not
exercise `@cluster` Kubernetes paths or MLflow integration locally. Open
question: is the `total_count` change intentional for system-scope callers?
```

```markdown
**Coverage:** eval-hub-contrib — reviewed `adapters/lighteval/main.py`,
`provider.yaml`, `tests/test_adapter.py` and the README tables, plus
`adapters/mteb/provider.yaml` and its presets. Ran the adapter suite offline
(`pytest tests/ -m "not local"`, 96 passed); did not run the `local`-marked
tests, build the image, or exercise a real LightEval endpoint. Checked the
eval-hub side of the catalog: no matching provider filename in
`config/providers/`, and no references to the provider ID in
`config/collections/` or the FVT benchmark fixtures, so no cross-repo dependency
was found. Pre-existing, not introduced here: `adapters/guidellm/` still has no
`provider.yaml`.
```

State honestly what was reviewed and what was not. Reviewers use this to decide
whether a second review (for example a `@cluster` run, or a container build) is
needed.

## 5. Phrasing guide

| Situation | Write |
|-----------|-------|
| Confident defect | "Returns 200 with an empty body when the job does not exist, so clients cannot distinguish not-found from an empty result." |
| Pre-existing issue the diff exposes | "Pre-existing, not introduced here: ... The new route makes it reachable from the API." |
| Needs runtime confirmation | "Suspected: duplicate status events arriving out of order may reset a completed job to running; confirm with the runtime event ordering." |
| Missing test with a concrete risk | "The new `--local` branch has no test; the `@local_runtime` FVT scenario is the only coverage for it and CI's default FVT job excludes that tag." |
| Missing adapter test with a concrete risk | "The new OCI branch is untested; `test_oci_export_persists_artifacts` only covers the configured case, so the skipped-phase regression is invisible to CI's `-m 'not local'` run." |
| Change depends on an unmerged external change | "The fixtures assume the adapter contract in contrib PR #263, which is open; with today's image the judge request is sent to the target endpoint, so the suite passes against the mock and misroutes against a strict upstream." |
| Contrib change that needs a new adapter image | "`provider.yaml` still points at `:latest`; the new parameter is ignored by the adapter currently published, so the setting is a no-op until a `v*` tag is released." |
| Open question (not a bug) | Put it under `Coverage` as a question, not in the table. |
| Style preference | Do not write it. |

## 6. What not to include

- A patch or diff (only if the user asks for fixes in a follow-up).
- A "nice to have" section, praise, or a restatement of the PR description.
- Rows for formatting, import order, naming, or comments that the repository's
  formatter/linter would settle (eval-hub `make fmt lint`; contrib `ruff` where
  configured).
- Duplicate rows for the same root cause in several places — report once and
  list the other affected locations in the detail block.
- Findings that only hold if you assume what the SDK, sidecar or evaluator does:
  read the SDK call (`evalhub.adapter`) or the sidecar behaviour first, or mark
  it `suspected`.
