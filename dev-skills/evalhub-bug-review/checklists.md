# EvalHub bug-review checklists

Detailed probes for Step 4 of [SKILL.md](SKILL.md). Work top to bottom; the
first four sections produce most Critical/High findings in this repository.

Each item is phrased as **what to look for** and includes the eval-hub code that
defines correct behavior. Cite the file you checked in the report's `Coverage`
section so the PR author knows what was and was not covered.

Where a probe uses `origin/main`, substitute the repository's default branch
(`gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`) if it
differs.

## 1. Multi-tenancy and identity

Canonical scoping helper: `getStorage` in `internal/eval_hub/handlers/evaluations.go`.

- [ ] Every storage call in a handler starts from `h.getStorage(ctx)` (applies
      `WithLogger` + `WithContext` + `WithTenant` + `WithOwner`). A call on
      `h.storage` directly drops tenant/owner and is a **Critical** finding.
- [ ] Background/runtime storage goes through `runtimeStorage.scopedStorage()`,
      which re-applies the tenant/owner captured at create time.
- [ ] List *and* count queries both filter by tenant/owner. These are usually two
      separate SQL statements that drift apart; check the `total_count` query
      independently of the page query.
- [ ] New routes in `setupRoutes` (`internal/eval_hub/server/server.go`) call
      `s.canContinueRequest(ctx, resp)` when identity is required. A missing call
      makes the route reachable with an empty tenant in cluster mode.
- [ ] `GET /api/v1/health` stays identity-free (probe-friendly).
- [ ] `--local` mode (`config.RequiresIdentityHeaders()` is false) still works:
      no new hard failure when `ctx.Tenant` / `ctx.User` are empty.
- [ ] Cross-workload isolation: post-processing routes must not resolve an
      evaluation job id, and vice versa. Check `WithWorkloadType` is applied and
      that GET/DELETE/list routes are scoped to their own workload.
- [ ] Storage keys always include the tenant: a lookup by bare id
      (`WHERE id = ?`) without `tenant = ?` is a cross-tenant read.
- [ ] Tenant/user values are never used as filesystem paths, k8s object names,
      or SQL fragments without validation.

Probes:

```bash
grep -n 'h\.storage\.' internal/eval_hub/handlers/*.go
grep -rn 'total_count' internal/eval_hub/storage/sql/*.go
grep -rn 'canContinueRequest' internal/eval_hub/server/server.go
grep -rn 'WithTenant\|WithOwner\|WithWorkloadType' internal/eval_hub/storage/sql/*.go
```

## 2. Context lifetime, cancellation, concurrency

Reference: `newExecutionContext` (`internal/eval_hub/server/execution_context.go`)
uses `r.Context()` so OTEL spans and request IDs propagate;
`executeEvaluationJob` (`internal/eval_hub/handlers/evaluations.go`) is the
**single** detach point via `otel.DetachedContext(ctx.Ctx)`.

- [ ] No `context.Background()` / `context.TODO()` on a request path. It breaks
      trace parenting and loses request-scoped cancellation.
- [ ] New background work (goroutines, runtimes, exporters) does not capture
      `ctx.Ctx` from the request, or jobs die when the client disconnects.
- [ ] Detached contexts still carry the values the work needs (tenant, logger,
      user) — detaching a context also detaches cancellation, so pair it with an
      explicit timeout where the work can hang.
- [ ] Every `go func` has an owner: `WaitGroup`/channel for completion, a way to
      surface its error, and a shutdown path on `SIGINT`/`SIGTERM`.
- [ ] HTTP/SQL/exec calls take a context; no unbounded retry loops without
      backoff or attempt caps.
- [ ] `defer` is not used inside a loop for rows/files/tickers (they stay open
      until the enclosing function returns); close per iteration and still check
      `rows.Err()` after the loop.
- [ ] Shared mutable state on `Handlers`, runtime structs, or package-level
      caches is guarded by a mutex or replaced copy-on-write. `go test -race`
      only covers paths the tests exercise.
- [ ] Unbuffered channel sends in a goroutine cannot deadlock when the request
      returns early.

Probes:

```bash
grep -rn 'context.Background()\|context.TODO()' internal/ cmd/ pkg/ --include='*.go' | grep -v _test
grep -rn 'go func' internal/eval_hub --include='*.go' | grep -v _test
grep -rn 'DetachedContext' internal/ --include='*.go' | grep -v _test
```

## 3. Errors, HTTP semantics, transactions

References: `internal/eval_hub/serviceerrors/error.go`,
`internal/eval_hub/messages/messages.go`,
`internal/eval_hub/httpwrappers/defs.go`,
`internal/eval_hub/storage/sql/transaction.go`.

- [ ] Client-visible errors are `serviceerrors.NewServiceError(messages.X, "Param", value)`
      written through `w.Error(err, ctx.RequestID)` or
      `w.ErrorWithMessageCode(...)`. A raw `fmt.Errorf`/`errors.New` reaching the
      response hides the status code and can leak internals.
- [ ] New error cases add a `createMessage(...)` entry with the right HTTP code
      in `messages.go` instead of hardcoding a status in a handler.
- [ ] After `w.Error` / `w.ErrorWithMessageCode`, the handler `return`s. A later
      `w.WriteJSON` causes a double `WriteHeader` and a corrupt response.
- [ ] Transaction rollback rule: in `runTransaction`, a non-`ServiceError` error
      rolls back, but a `ServiceError` **without** `.WithRollback()` **commits**.
      Any error returned after a partial write inside a transaction must be
      `serviceerrors.WithRollback(...)` — otherwise partial state is committed.
- [ ] Transaction callbacks are retried on SQLSTATE 40001
      (`serializationFailureMaxAttempts`), so they must be idempotent and free of
      irreversible side effects (HTTP calls, file writes, k8s creates).
- [ ] Errors are wrapped with `%w` where callers use `errors.Is/As`
      (for example mapping `sql.ErrNoRows` to 404).
- [ ] No silently swallowed errors: `_ = err`, empty `if err != nil {}`, or a
      discarded `defer` close error on a write path without a justification.
- [ ] Status codes match `docs/src/openapi.yaml` and
      `internal/eval_hub/constants/http_codes.go` (200/201/202/204/400/401/403/
      404/409/413/500/501).
- [ ] Validation order: parse → validate → authorize/scope → persist → run. A
      handler that persists before validating can store invalid resources.
- [ ] `w.WriteJSON` payload types match the `pkg/api` response type; ad-hoc
      `map[string]any` responses drift from the spec.

Probes:

```bash
grep -rn 'w\.Error\|ErrorWithMessageCode' internal/eval_hub/handlers/*.go
grep -rn 'WithRollback' internal/eval_hub/storage --include='*.go'
grep -rn '_ = ' internal/eval_hub --include='*.go' | grep -v _test | head -30
grep -rn 'fmt.Errorf\|errors.New' internal/eval_hub/handlers --include='*.go' | grep -v _test
```

## 4. Job state machine and status events

References: `HandleUpdateEvaluation` and `runtimeStorage.UpdateEvaluationJob`
(`internal/eval_hub/handlers/evaluations.go`), `messages.JobCanNotBeUpdated`,
`internal/eval_hub/storage/sql/evaluations_status.go`.

- [ ] Transition guards cover every terminal state: a completed, failed, or
      cancelled job cannot be restarted by a late or duplicate event.
- [ ] The previous state is read before validation and used consistently; a
      validation failure must not have already mutated state.
- [ ] Duplicate events are idempotent (same benchmark result reported twice must
      not double-count or overwrite a newer state with an older one).
- [ ] Exactly-once finalization: results/MLflow fields, completion timestamp, and
      runtime cleanup happen once, on the transition into a terminal state.
- [ ] Cancel vs. delete: both stop the runtime, both release cluster resources,
      and both behave correctly when the job is already terminal.
- [ ] Benchmark-level bookkeeping is bounds-checked (index within
      `job.Benchmarks`), handles unknown benchmark ids, and rejects duplicate
      benchmark ids in a single create request.
- [ ] Event ingestion is tenant/owner scoped: an event for another tenant's job
      must 404, not update.
- [ ] Post-processing completion validates its source evaluation belongs to the
      same tenant and is completed before writing.

Probes:

```bash
grep -rn 'JobCanNotBeUpdated\|OverallState' internal/eval_hub/handlers internal/eval_hub/storage --include='*.go' | grep -v _test
grep -rn 'func .*Test.*Cancel\|func .*Test.*Update' internal/eval_hub/handlers/*_test.go
```

## 5. Runtimes, jobs, and the sidecar contract

References: `internal/eval_hub/runtimes/{local,k8s,shared}`,
`cmd/eval_runtime_sidecar`, `cmd/eval_runtime_init`,
`internal/eval_hub/config/sidecar_config.go`, `ARCHITECTURE.md`.

- [ ] Every resource the k8s runtime creates has a defined lifecycle.
      `DeleteEvaluationJobResources` deletes labeled Jobs and ref Secrets
      (`deleteLabeledJobsAndRefSecrets`); Job-owned ConfigMaps/NetworkPolicies are
      left to Kubernetes GC through the owner reference; unowned ConfigMaps are
      deliberately retained (see the comments in `k8s_runtime.go`). A new resource
      type added with **neither** an owner reference **nor** a delete path is a
      **High** leak.
- [ ] Object names are deterministic, unique per job, and valid: DNS-1123
      subdomain (≤253 chars), label values (≤63 chars, `[a-z0-9A-Z-_.]`),
      and no user-controlled raw strings in names.
- [ ] Labels/selectors used for cleanup match the labels applied at creation.
      A renamed label silently orphans resources.
- [ ] `sidecar_config.json` keys are a cross-binary contract:
      `eval_hub.base_url`, `eval_hub.token`, `mlflow.tracking_uri`,
      `mlflow.token_path`, CA paths, `insecure_skip_verify`, `local_mode`.
      Changing a key in the server without changing
      `cmd/eval_runtime_sidecar` (and its tests) breaks running pods.
- [ ] Fixed in the sidecar binary, not config: termination message path
      `/data/termination-log`, readiness file. Do not "reconfigure" them in a PR
      without updating the sidecar.
- [ ] Token handling: per-job/per-tenant tokens, mounted read-only, short-lived,
      never baked into the Job spec env in plaintext when a secret is available.
- [ ] k8s API errors: `apierrors.IsNotFound` treated as success on delete,
      transient errors retried, and no cross-namespace access.
- [ ] Local runtime: process start/stop symmetry, PID tracking, temp/work dir
      cleanup, cancellation kills the process group (not just the parent).
- [ ] Runtime settings validation: unsupported runtime for a provider/benchmark
      fails at create time with a client error, not mid-job.
- [ ] `RuntimeStorage` surface stays narrow (`GetProvider`,
      `GetEvaluationJob`, `UpdateEvaluationJob`); a runtime reaching into full
      `Storage` couples workers to server internals.
- [ ] The init container's outputs match what the sidecar and the job's main
      container expect (paths, env file names, exit codes).

## 6. API contract and documentation

- [ ] `docs/src/openapi.yaml` is the **only** hand-edited API artifact. These are
      generated by `make documentation` and must not be hand-edited in a PR:
      `docs/openapi.yaml`, `docs/openapi.json`, `docs/openapi-internal.yaml`,
      `docs/openapi-internal.json`, `docs/index.html`, `docs/index-public.html`,
      `docs/index-private.html`.
- [ ] A PR that changes generated files without also changing `docs/src` (or that
      hand-tweaks generated content) is a **Medium** finding.
- [ ] `pkg/api` structs match the spec: field names, `json` tags, `omitempty`,
      required vs. optional, enums, and nullable fields. A tag drift breaks SDKs
      even when Go compiles.
- [ ] New/changed query parameters are: allow-listed (else `QueryBadParameter`),
      checked for mutual exclusion (`QueryParameterMismatch`), validated
      (`QueryParameterValueInvalid`/`QueryParameterInvalid`), and defaulted.
- [ ] Pagination: `limit`/`offset` (or equivalent) bounds, `count` and
      `total_count` consistency, stable sort order, and no unbounded page size.
- [ ] New routes are registered for the right methods; unsupported methods return
      `messages.MethodNotAllowed`, not a 404/panic.
- [ ] Error responses documented in the spec are the ones actually returned.
- [ ] A release bump also updates `info.version` in `docs/src/openapi.yaml`
      (see section 10).
- [ ] `make verify-api-docs` passes (Redocly lint) when the spec changed, and
      `docs/scripts/check_unused_components.sh` still passes.

Probes:

```bash
grep -rn 'json:"' pkg/api/*.go | head -40
grep -rn 'QueryBadParameter\|QueryParameterMismatch' internal/eval_hub/handlers/*.go
git diff --name-only "$(git merge-base origin/main HEAD)"...HEAD -- docs/
```

## 7. Security

- [ ] No `#nosec` or `//gosec:disable` anywhere (CI rejects both). If a pattern
      needs suppression, restructure — e.g. use `internal/safefile`
      (`ReadFile`, `Open`, `Create` with a root dir) instead of joining
      user input into a path.
- [ ] Path handling: `filepath.Join` is **not** a traversal guard. Any path built
      from a query/path parameter, provider id, or config value must go through
      `internal/safefile` or explicit validation.
- [ ] Secrets never reach logs, error messages, or the API response: tokens,
      `Authorization` headers, API keys, secret file contents, full provider
      configs, MLflow credentials.
- [ ] `InsecureSkipVerify` is only honored when the config explicitly enables it,
      is documented, and has a test; never the default
      (`proxy.DefaultInsecureSkipVerify` is `false`).
- [ ] Per-tenant credentials: no process-wide client cached with one tenant's
      token then reused for another. Check `pkg/mlflowclient`, `pkg/ociclient`,
      and the results exporter wiring.
- [ ] SSRF: user-supplied provider/model URLs hitting internal addresses; check
      scheme validation and any allow-list.
- [ ] `text/template` is only used with trusted templates; user data goes in as
      parameters, never as the template source.
- [ ] Request body size limits still apply to new endpoints
      (`messages.RequestBodyTooLarge` / `MaxBytesReader`).
- [ ] MCP: tool handlers go through `pkg/evalhubclient` (inherits auth/tenant
      headers) rather than raw HTTP; errors returned to the model contain no
      secrets; tool descriptions do not invite prompt-injection with server data.
- [ ] New dependencies are justified, license-compatible, and not a banned
      package (`depguard` in `.golangci.yml` bans `golang.org/x/crypto/openpgp`).
- [ ] Authorization follows identity: a user may act on their own resources and
      their tenant's; cross-tenant access requires an explicit system scope.

## 8. Observability

- [ ] Log fields use the shared constants from
      `internal/eval_hub/constants/log_fields.go` (`request_id`, `tenant`,
      `user`, `error`, `method`, `uri`, `code`, ...) rather than ad-hoc strings,
      so log queries keep working.
- [ ] Log levels are meaningful: expected 4xx validation is not logged at
      `Error`; real failures are not logged at `Debug`; `Warn` for retryable
      conditions (see `runTransaction`).
- [ ] No unbounded Prometheus label values (job id, user id, raw URL, error
      text). Labels must be bounded sets; put high-cardinality data in logs, not
      metrics. Check `internal/eval_hub/metrics`.
- [ ] New routes are covered by the metrics middleware (they go through
      `s.handleFunc`), so latency/status are recorded.
- [ ] OTEL: long-running/background work uses `otel.DetachedContext` so spans are
      linked, not orphaned or wrongly parented to a finished request.
- [ ] Errors logged inside runtime workers include the job id and benchmark
      context, so a failing job can be traced from logs alone.
- [ ] No log line per item in a hot loop (log once per job/request with counts).

Probes:

```bash
grep -rn 'logger\.\(Info\|Error\|Warn\|Debug\)' internal/eval_hub/handlers/*.go | grep -v _test | head -30
grep -rn 'prometheus\|CounterVec\|HistogramVec' internal/eval_hub/metrics/*.go | head -30
grep -rn 'Log[A-Z]' internal/eval_hub --include='*.go' | grep -v _test | head -20
```

## 9. Tests

- [ ] A `fix` commit includes a regression test that fails without the change.
      A bug fix with no test is a **Medium** finding (state the exact uncovered
      behavior; do not just say "add tests").
- [ ] New handler branches cover: success, validation error, not-found, conflict,
      and the tenant-isolation path. Tests build a `Handlers` and drive the
      `RequestWrapper`/`ResponseWrapper` fakes, as in
      `internal/eval_hub/handlers/*_test.go`.
- [ ] New or changed routes have an FVT scenario/step in `tests/features/`
      (`tests/features/README.md` documents steps and tags). Tag choices:
      `@local_runtime` for a working local job runtime, `@cluster` for
      Kubernetes-only, `@mlflow` for MLflow, `@negative` for error paths.
      Note that default `make test-fvt` excludes `@local_runtime`, `@cluster`,
      and `@mlflow`, so a scenario tagged with one of them will not run in CI's
      default FVT job — check the PR explains why.
- [ ] New `Fuzz*` targets are added to `FUZZ_PACKAGES` in the `Makefile`,
      otherwise `make test`/`make test-fuzz` never runs them.
- [ ] `t.Parallel()` is not used where the test mutates process-wide state
      (`t.Setenv`, `os.Stdout`, package globals, shared temp dirs).
- [ ] Tests assert on decoded structs/fields where possible; assertions on raw
      JSON strings only when the wire format is the contract.
- [ ] Storage tests use a real in-memory SQLite database (default config) rather
      than a mock that cannot catch SQL/tenant-filter bugs.
- [ ] Tests that need Postgres/cluster are correctly skipped when unavailable,
      rather than silently passing.
- [ ] Table-driven tests assert the error message code/status, not only
      "an error happened".

Probes:

```bash
git diff --stat "$(git merge-base origin/main HEAD)"...HEAD -- '*_test.go' 'tests/'
grep -n 'FUZZ_PACKAGES' -A 3 Makefile
grep -rn 't.Parallel()' internal/eval_hub --include='*_test.go' | wc -l
```

## 10. Repository conventions and release mechanics

Process checks. Report them **once** and at **Low** severity — or as an open
question under `Coverage` — never as per-line findings.

- [ ] `make fmt lint` is clean (`go fmt`, `go vet`, `golangci-lint` with
      `.golangci.yml`). `go.mod`'s Go version is the source of truth; do not
      downgrade it to match a local toolchain.
- [ ] Conventional commit subject with an allowed type (`build`, `bump`, `chore`,
      `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`).
- [ ] DCO: commit made with `-s`; no hand-written `Signed-off-by` in the body.
- [ ] Exactly one `Assisted-by: <full model name> (<harness>)` trailer, generated
      with `make -s assisted-by-trailer`, at the end of the body.
- [ ] Version bump touches **all four** sources together: `VERSION`, the
      `Version` constant in `cmd/eval_hub/main.go`, both `BUILD_NUMBER` ARG
      defaults in `Containerfile`, and `info.version` in
      `docs/src/openapi.yaml` — followed by `make documentation`.
- [ ] Generated artifacts are not committed: `docs/openapi*.{yaml,json}`,
      `docs/index*.html`, `bin/`, coverage output.
- [ ] Config changes: new keys added to `config/config.yaml`, mapped in
      `env_mappings` / `secrets.mappings` when they should be overridable, with a
      safe default and no behavior change for existing deployments.
- [ ] Provider/collection YAML in `config/providers/` and `config/collections/`
      stays schema-valid (`make validate-configs`) and does not hardcode
      environment-specific URLs.
- [ ] MCP changes update `MCP.md` (tools/resources/prompts reference).
- [ ] Docs changes are consistent between `README.md`, `AGENTS.md`, `CLAUDE.md`,
      `ARCHITECTURE.md`, and the site docs; a comment describing behavior that
      no longer exists is a **Low** finding.
- [ ] No debug leftovers: `fmt.Print*`, `spew`, commented-out blocks, or a
      `TODO` without a linked issue.

## 11. High-yield quick scan

Run these once per review; they surface most of the recurring eval-hub defects.

```bash
# cross-repo adapter coupling claimed in the PR body
gh pr view <n> --json body --jq .body | grep -n -iE 'contrib|adapter image|deploy its images'

# scoping bypass
grep -rn 'h\.storage\.' internal/eval_hub/handlers/*.go | grep -v _test

# detached-context misuse
grep -rn 'context.Background()\|context.TODO()' internal/ cmd/ pkg/ --include='*.go' | grep -v _test

# transaction correctness
grep -rn 'return .*NewServiceError' internal/eval_hub/storage/sql/*.go | grep -v _test

# forbidden suppressions
grep -rn '#nosec\|gosec:disable' --include='*.go' .

# generated docs touched without the source
git diff --name-only "$(git merge-base origin/main HEAD)"...HEAD -- docs/

# new route without an identity check
grep -n 'canContinueRequest' internal/eval_hub/server/server.go

# version-bump completeness
git diff "$(git merge-base origin/main HEAD)"...HEAD -- VERSION cmd/eval_hub/main.go Containerfile docs/src/openapi.yaml
```

## 12. Cross-repo adapter and catalog coupling

Some eval-hub changes only work with an adapter image built from
`eval-hub/eval-hub-contrib`. Provider YAML (`config/providers/*.yaml`), benchmark
fixtures (`tests/benchmarks/testdata`), the fixture generator
(`tests/benchmarks/generate`) and the FVT jsonnet payloads (`tests/features`) all
encode the adapter contract, so a PR touching them can depend on an unmerged or
unreleased adapter change. The dependency is usually stated in prose in the PR
body, for example "deploy its images together with these catalog changes" or "the
related adapter changes are in contrib PR #263".

Treat that sentence as a **review target, not as context**. A deploy-order note
is the author telling you the change is not self-contained.

- [ ] For every contrib PR named in the body, check merge state and scope:

      ```bash
      gh api repos/eval-hub/eval-hub-contrib/pulls/<contrib-pr> --jq '{state, merged, title}'
      gh api --paginate repos/eval-hub/eval-hub-contrib/pulls/<contrib-pr>/files --jq '.[].filename'
      ```

      A closed-but-unmerged predecessor of a newer open PR means the dependency is
      still pending. A framework the body claims is covered but that does not
      appear in the file list is a finding on its own.
- [ ] For each changed catalog/fixture surface, read the adapter that runs
      **today** on the contrib default branch, not the one in the pending PR:

      ```bash
      f=$(mktemp)
      if curl -fsSL -o "$f" \
        "https://raw.githubusercontent.com/eval-hub/eval-hub-contrib/main/adapters/<framework>/main.py"; then
        head -n 3 "$f"                     # it is the adapter, not an error page
        grep -nE 'secret_ref|<removed_param>|read_model_auth_key' "$f"
      else
        echo 'FETCH FAILED: contract unverified, not "parameter removed"' >&2
      fi
      ```

      `-f` (with `-L`) turns an HTTP error, a moved adapter, or a redirect that
      lands on nothing into a **fetch failure**, and the grep only reads a
      downloaded file: a missing match proves a parameter was dropped only when
      the fetch succeeded. A parameter this PR stops declaring (or stops emitting
      from a fixture) must already be consumed by that code, or the change is only
      correct after the adapter ships.
- [ ] Compare `config/providers/<framework>.yaml` with
      `adapters/<framework>/provider.yaml` on the contrib default branch. The two
      files are near-copies. A parameter eval-hub stops declaring while contrib
      still declares it (or the reverse) is catalog drift: report it and say which
      file a future sync would resurrect it from.
- [ ] Classify how a contract mismatch fails, because that decides the severity:
      the old adapter **rejects** the legacy input (loud, safe to ship ahead),
      **ignores** it and falls back to the primary connection (silent credential
      or endpoint substitution, High), or **accepts** it unchanged (no risk).
      Quote the adapter line that proves the behaviour.
- [ ] Check the failure is reachable from CI. A misroute that only affects a
      benchmark excluded from the default `KIND_BENCHMARK_RUN` (`Makefile`, the
      `KIND_BENCHMARK_RUN ?=` line) or from the default `FVT_TAGS` is untested.
- [ ] Check whether the dependency can be pinned at all:
      `grep -n 'image:' config/providers/*.yaml`. Floating `:latest` tags plus no
      digest/version field mean "deploy together" is unenforceable and
      unverifiable; say so and ask how the release is gated.
- [ ] Check the PR text is accurate about direction and behaviour (merged vs
      pending, reject vs ignore). A wrong claim about the adapter contract
      misleads the release manager and the migration notes.

Probes:

```bash
gh pr view <n> --json body --jq .body | grep -n -iE 'contrib|adapter image|deploy its images'
gh api repos/eval-hub/eval-hub-contrib/pulls/<contrib-pr> --jq '{state, merged}'

# Fetch each catalog first, then grep the downloaded file. `curl -s ... | grep`
# reports a 404 body, an unfollowed redirect, or a transport failure as "no
# match", which reads as catalog drift. -fsSL fails on HTTP >= 400, follows
# redirects, and keeps a failed fetch separate from a grep no-match.
probe() {  # probe <path under adapters/> <extended regex>
  local f
  f=$(mktemp) || return 1
  if curl -fsSL -o "$f" \
    "https://raw.githubusercontent.com/eval-hub/eval-hub-contrib/main/adapters/$1"; then
    head -n 3 "$f"
    grep -nE "$2" "$f" || echo "no match in $1 (fetched OK)"
  else
    echo "FETCH FAILED: $1 — contract unverified, not drift" >&2
  fi
}

probe deepeval/main.py 'eval_model_url'
probe ragas/provider.yaml 'name: judge_url'

git grep -n 'image:' HEAD -- config/providers
```

