# EvalHub bug-review report template

Use exactly this shape for Step 6 of [SKILL.md](SKILL.md), and rate each finding
with the rubric in §2. Keep it compact: a reviewer should be able to read the
table, pick a row, and see the justification in `Details`.

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

### Severity rubric (eval-hub)

Rate every row with this rubric; the label is what makes two reviews comparable.

| Severity | Meaning | Examples |
|----------|---------|----------|
| **Critical** | Data exposure, auth bypass, corruption, or crash on a normal path | tenant/owner scoping dropped so one namespace can read or mutate another's job; route added without `s.canContinueRequest`; token/secret written to logs; partial write committed by a `ServiceError` missing `.WithRollback()`; nil dereference/panic on a request path reachable by any tenant |
| **High** | Wrong results/state, resource leak, or contract break | illegal job state transition or duplicate finalization; a created k8s resource with neither an owner reference nor a delete path (for example a ref Secret left out of the cleanup sweep); submit returns 202 but the job is never started; wrong status code vs. `docs/src/openapi.yaml`; `pkg/api` JSON tag no longer matches the spec; background work bound to the request context so long jobs die on client disconnect; a catalog/fixture change that needs an unreleased adapter image, so role traffic silently falls back to the primary endpoint and credential |
| **Medium** | Wrong under specific conditions, or weakens operability | race only under concurrent events; off-by-one in pagination or `total_count`; missing nil guard for an optional API field; unbounded Prometheus label values; misleading log level; error path that loses the original error without `%w`; no regression test for the fixed bug |
| **Low** | Documentation drift, dead code, minor clarity | stale doc/comment describing old behavior; unused helper; an unfinished marker comment without a linked issue; generated-doc edit that also changed `docs/src` inconsistently |

### Do not report

- Formatting and lint output that `make fmt`, `go vet`, `golangci-lint`, or
  gitleaks already reports. Commit hygiene (missing DCO sign-off, duplicated or
  missing `Assisted-by`, non-conventional subject) may be reported **once**, as
  Low, when it would block merge — never as per-line review comments.
- Personal style preferences, "consider renaming", speculative future-proofing.
- "Missing tests" with no concrete untested risk. If behavior is genuinely
  untested and risky, report it as Medium with the specific uncovered path.
- Pre-existing defects in unchanged code, unless the change makes them reachable
  or worse — then label them `pre-existing, not introduced here`.
- Anything you could not justify from the code in front of you.

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
| Change depends on an unmerged external change | "The fixtures assume the adapter contract in contrib PR #263, which is open; with today's image the judge request is sent to the target endpoint, so the suite passes against the mock and misroutes against a strict upstream." |
| Open question (not a bug) | Put it under `Coverage` as a question, not in the table. |
| Style preference | Do not write it. |

## 6. What not to include

- A patch or diff (only if the user asks for fixes in a follow-up).
- A "nice to have" section, praise, or a restatement of the PR description.
- Rows for formatting, import order, naming, or comments that `make fmt lint`
  would settle.
- Duplicate rows for the same root cause in several places — report once and
  list the other affected locations in the detail block.
