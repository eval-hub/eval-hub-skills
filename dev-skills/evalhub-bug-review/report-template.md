# EvalHub bug-review report template

Use exactly this shape for Step 6 of [SKILL.md](SKILL.md). Keep it compact: a
reviewer should be able to read the table, pick a row, and see the justification
in `Details`.

## 1. Summary line

```text
Found 3 bugs in 7 changed files (Critical: 1, High: 1, Medium: 1, Low: 0)
```

No findings:

```text
No bugs found in this diff (7 files reviewed).
```

Empty diff:

```text
No diff to review — the branch matches origin/main (0 changed files).
```

## 2. Findings table

Exactly three columns, highest severity first. One row per finding.

```markdown
| Severity | Location (file:line) | Finding |
|----------|----------------------|---------|
| Critical | internal/eval_hub/handlers/evaluations.go:612 | List query bypasses `h.getStorage(ctx)` and reads `h.storage` directly, so `total_count` is computed across all tenants. |
| High | internal/eval_hub/runtimes/k8s/k8s_runtime.go:418 | New per-job ref Secret is created without an owner reference and is not included in the `DeleteEvaluationJobResources` sweep, leaking one Secret per job. |
| Medium | internal/eval_hub/storage/sql/evaluations_crud.go:154 | `ServiceError` returned after a partial write is missing `.WithRollback()`, so the transaction commits half the update. |
```

Rules:

- `Location` is `path:line` or `path:start-end`; no line-less locations.
- Severity is one of `Critical`, `High`, `Medium`, `Low`.
- The finding column states the **defect and its consequence**, not the fix.
- Keep each cell to one or two sentences; detail goes below.
- Do not include a row you cannot justify from the code (see Step 5).

## 3. Details

One block per finding, same order as the table, labelled with the severity and
location. Include the snippet, the trigger, and a suggested direction.

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

Status is `confirmed` (provable from code or reproduced) or `suspected` (needs a
cluster/MLflow/race condition). Never present `suspected` as certain.

## 4. Coverage

```markdown
**Coverage:** reviewed handlers, SQL storage, and their unit tests. Did not
exercise `@cluster` Kubernetes paths or MLflow integration locally. Open
question: is the `total_count` change intentional for system-scope callers?
```

State honestly what was reviewed and what was not. Reviewers use this to decide
whether a second review (for example a `@cluster` run) is needed.

## 5. Phrasing guide

| Situation | Write |
|-----------|-------|
| Confident defect | "Returns 200 with an empty body when the job does not exist, so clients cannot distinguish not-found from an empty result." |
| Pre-existing issue the diff exposes | "Pre-existing, not introduced here: ... The new route makes it reachable from the API." |
| Needs runtime confirmation | "Suspected: duplicate status events arriving out of order may reset a completed job to running; confirm with the runtime event ordering." |
| Missing test with a concrete risk | "The new `--local` branch has no test; the `@local_runtime` FVT scenario is the only coverage for it and CI's default FVT job excludes that tag." |
| Open question (not a bug) | Put it under `Coverage` as a question, not in the table. |
| Style preference | Do not write it. |

## 6. What not to include

- A patch or diff (only if the user asks for fixes in a follow-up).
- A "nice to have" section, praise, or a restatement of the PR description.
- Rows for formatting, import order, naming, or comments that `make fmt lint`
  would settle.
- Duplicate rows for the same root cause in several places — report once and
  list the other affected locations in the detail block.
