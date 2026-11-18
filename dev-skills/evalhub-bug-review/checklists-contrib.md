# eval-hub-contrib bug-review checklists (§13–§22)

Detailed probes for Step 4 of [SKILL.md](SKILL.md) when the diff is in
`eval-hub/eval-hub-contrib`. This repository is not the Go service: there is no
OpenAPI, no SQL storage, no `make lint`, no `gofmt`. An adapter is a Python
package that eval-hub runs as a job container, plus catalog metadata
(`provider.yaml`) that eval-hub reads to decide *whether and how* to run it.

Use [checklists.md](checklists.md) §1–§12 only for `eval-hub` (Go) diffs.

Layout reminder:

| Path | Role |
|---|---|
| `adapters/<name>/main.py` | `FrameworkAdapter.run_benchmark_job`; the whole job |
| `adapters/<name>/provider.yaml` | catalog entry eval-hub loads: id, runtime, benchmarks, parameters, `agent:` hints |
| `adapters/<name>/meta/job.json` | sample `JobSpec` used by tests and docs |
| `adapters/<name>/tests/` | pytest suite; `conftest.py` puts the adapter dir on `sys.path` |
| `adapters/<name>/Containerfile` | image; `ENTRYPOINT` must match `provider.yaml` |
| `adapters/<name>/requirements*.txt`, `constraints.txt`, `requirements.lock` | pins; inspect/lighteval are gated on the Red Hat index |
| `collections/*.yaml` | cross-adapter benchmark bundles by `provider_id` |
| `docs/model-role-auth.md` | the credential/role contract for judge and auxiliary models |
| `.github/workflows/test-<name>.yml`, `Makefile` | CI and local wiring per adapter |

Where a probe uses `origin/main`, substitute the default branch
(`gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'`).

## 13. Adapter contract and JobPhase lifecycle

References: `adapters/lighteval/main.py:100` (`run_benchmark_job`), README
"JobPhase Lifecycle" (phases, status format, artifact gating), CONTRIBUTING
(`metrics_schema`).

- [ ] `run_benchmark_job(self, config: JobSpec, callbacks: JobCallbacks) ->
      JobResults` keeps its signature. eval-hub drives the adapter through the
      SDK, so a changed parameter list or return type is a **High** contract
      break even when the adapter's own tests pass.
- [ ] Phases are emitted in order: `INITIALIZING` → `LOADING_DATA` →
      `RUNNING_EVALUATION` → `POST_PROCESSING` → `PERSISTING_ARTIFACTS`. A
      missing or reordered phase makes progress wrong or violates the server's
      fixed phase set.
- [ ] `COMPLETED` is **never** emitted manually — `callbacks.report_results()`
      does it. A manual `COMPLETED` produces a terminal status the server did
      not expect, and results may never arrive.
- [ ] `PERSISTING_ARTIFACTS` is reported **only** when `config.exports.oci` is
      set, and the `create_oci_artifact` call sits inside the same guard. A
      phase with nothing to persist, or an artifact call without the phase, is a
      **Medium**.
- [ ] Only `status` and `phase` survive the SDK. `progress`, `message`,
      `current_step` written into `JobStatusUpdate` are silently dropped, so
      code that relies on them for observability is broken.
- [ ] Failure path: report `JobStatusUpdate(status=JobStatus.FAILED,
      error_message=MessageInfo(message=..., message_code=...))` **and** re-raise
      so the SDK finalizes. `ErrorInfo` is deprecated. A failure that skips the
      callback leaves the job running until it times out.
- [ ] `JobResults` is complete: `id`, `benchmark_id`, `benchmark_index`,
      `model_name`, `results`, `metrics_schema`, `overall_score`,
      `num_examples_evaluated`, `duration_seconds`, `completed_at`. Copy/paste of
      `benchmark_index` or `model_name` from a sibling adapter silently
      attributes results to the wrong benchmark.
- [ ] Durations are measured from a start time taken after validation and are
      reported even on partial success; a zero/negative duration is a **Low**
      smell that usually hides a misplaced `start_time`.
- [ ] `__main__` reads `EVALHUB_JOB_SPEC_PATH` (default `/meta/job.json`) and
      `LOG_LEVEL`; the `Containerfile` `ENTRYPOINT` matches
      `provider.yaml` `runtime.k8s.entrypoint`.
- [ ] A new adapter ships all of: `main.py`, `provider.yaml`, `meta/job.json`,
      `tests/`, `Containerfile`, `requirements.txt`, `requirements-test.txt`.

Probes:

```bash
grep -n 'JobPhase\.' adapters/<name>/main.py
grep -n 'report_status\|report_results' adapters/<name>/main.py
grep -n 'COMPLETED\|ErrorInfo' adapters/<name>/main.py
grep -n 'PERSISTING_ARTIFACTS' -A4 -B4 adapters/<name>/main.py
```

## 14. Provider catalog: provider.yaml, benchmarks, parameters

CI runs `.github/scripts/validate_provider.py`, which only checks that a **new**
adapter directory has a `provider.yaml` that parses as YAML. There is no schema
or semantic validation, so everything below is the reviewer's job.

- [ ] Every adapter that ships an image has a `provider.yaml`. Today
      `adapters/guidellm/` and `adapters/pyrit/` have none — an adapter without
      one cannot be loaded by eval-hub at all. Adding one is a feature; deleting
      or renaming one is a **High** catalog break.
- [ ] `id` is what eval-hub, collections and users address. Note the ids that do
      not match their directory: `adapters/clear/` is `ibm-clear`,
      `adapters/lm-eval/` is `lm-eval`, `evalhub-post-processor/` is
      `evalhub-internal`. Renaming one breaks `collections/*.yaml`
      (`provider_id`) and eval-hub's `config/providers/<name>.yaml`.
- [ ] Every `benchmarks[].id` is dispatchable by the adapter's `benchmark_id`
      → task/preset mapping. A benchmark declared but rejected at runtime is a
      **High** (users select it and the job fails); one supported but undeclared
      is **Medium** (unreachable feature).
- [ ] `benchmarks[].metrics` names match the `EvaluationResult.metric_name`
      values the adapter emits and the collection's `primary_score.metric`. A
      renamed metric breaks dashboards and pass/fail thresholds.
- [ ] `parameters[].name` are the keys actually read from `config.parameters`. A
      documented parameter nobody reads is a silent no-op — **High** when it
      controls cost or scope (`max_samples`, `num_examples`, `limit`,
      `request_timeout`), **Low** otherwise.
- [ ] `runtime.k8s.image` matches the published name. CI maps
      `clear`→`community-ibm-clear`,
      `evalhub-post-processor`→`evalhub-post-processor`, everything
      else→`community-<dir>`; `tooleval` ships a second image
      `community-toolbench-server`. A mismatch means eval-hub pulls a tag that
      does not exist.
- [ ] `runtime.k8s` has `cpu_request`, `memory_request`, `cpu_limit`,
      `memory_limit` the framework can actually run in. A framework that loads
      model weights with `memory_limit: 2Gi` fails at runtime, not in CI.
- [ ] The optional `agent:` block stays truthful: `evaluates`,
      `recommended_when`, `summary` (benchmark counts and capability claims),
      `complements`, `hints`. A summary or hint that still advertises a benchmark
      count or capability the adapter no longer supports misroutes agent
      selection — **Medium**.
- [ ] `type:` is present and is a value eval-hub accepts. `builtin` accounts for
      10 adapters and `community` for 7 (`databench`, `followbench`, `ifbench`,
      `inspect`, `lighteval`, `lm-eval`, `promptfoo`), while CONTRIBUTING lists
      `type` as **required** and says `builtin`. `evalhub-post-processor` ships
      without a `type:` today. Do not report that as this PR's bug; do check that
      a **new or changed** entry is valid.
- [ ] `collections/*.yaml` benchmark ids exist in the named provider. The Korean
      collections use `provider_id: lm_evaluation_harness`, which is the
      LMEvalJob-based provider in eval-hub, **not** `adapters/lm-eval/`'s
      `id: lm-eval` — check the pair against the right source before calling it
      drift.

Probes:

```bash
# catalog overview: id, type, benchmark count per adapter
uv run --quiet --with pyyaml python - <<'PY'
import pathlib, yaml
for p in sorted(pathlib.Path("adapters").glob("*/provider.yaml")):
    d = yaml.safe_load(p.read_text()) or {}
    print(p.parent.name, "id=", d.get("id"), "type=", d.get("type"),
          "benchmarks=", len(d.get("benchmarks") or []))
PY
grep -n 'benchmark_id' adapters/<name>/main.py | head -20   # dispatch
grep -n 'parameters' adapters/<name>/main.py | head -20     # consumed keys
grep -n '^id:' adapters/*/provider.yaml
grep -n 'provider_id' collections/*.yaml
```

## 15. Credentials, secret roles, offline and staged assets

Reference: `docs/model-role-auth.md` (normative), `evalhub.adapter.read_model_auth_key`,
`resolve_model_credentials`, `adapters/atif/judge_auth.py`,
`adapters/inspect/_preflight.py`, `_hf_offline.py` in the adapters that stage
assets.

- [ ] Credentials come from the job's `model.auth.secret_ref` through
      `read_model_auth_key(...)` / `resolve_model_credentials(...)`. A new
      `os.getenv("<ROLE>_API_KEY")`-style fallback re-opens the silent
      credential-substitution bug that PRs #263, #297 and #304 removed.
- [ ] Role semantics are preserved: `<role>_api-key` selects the credential,
      `<role>_url` selects the upstream; key without URL = primary URL with the
      role credential; URL without key = **error**; neither = primary URL and
      the primary `api-key`. A change here changes behaviour for every adapter
      listed in the model-role table.
- [ ] Legacy inline connection parameters (`eval_model_url`, `judge_url`,
      `endpoint_url`, `inference_url`, `*_base_url`, `*_api_key`) stay
      **ignored**: not honoured, and never fatal. Honouring one silently routes
      a judge call at the target endpoint.
- [ ] Connector fields are stripped from framework model-option dicts before the
      framework sees them (the doc guarantees this), so a key cannot leak into
      framework logs or a subprocess CLI.
- [ ] Local mode uses an absolute `file:///…` auth directory; a relative path or
      a home-directory default breaks local jobs (and `--local` is the only
      path developers can run without a cluster).
- [ ] Secrets never reach logs, exception text, `JobResults.evaluation_metadata`
      or a child process's command line. Grep for f-string logging of the key,
      token, or full auth dict.
- [ ] TLS-skip switches (`verify=False`,
      `MLFLOW_TRACKING_INSECURE_TLS`, `InsecureSkipVerify` equivalents) come
      from explicit configuration with a safe default, never unconditionally.
- [ ] Offline/disconnected execution: staged datasets, Hugging Face cache,
      LightEval task registry and NLTK data are resolved through the adapter's
      `_hf_offline`-style helpers (`TEST_DATA_DIR`, `ensure_*`). A new network
      fetch at import time or before `LOADING_DATA` breaks disconnected pods and
      the `local` CI jobs (PRs #289–#298 were exactly this).
- [ ] `EVALHUB_MODE` (`k8s` / `local`) gates behaviour that genuinely differs; a
      branch keyed on the wrong mode changes production pods while passing local
      tests.

Probes:

```bash
grep -rn 'API_KEY\|_TOKEN\|SECRET' adapters/<name>/main.py | grep -i 'getenv'
grep -rn 'read_model_auth_key\|resolve_model_credentials' adapters/<name>/main.py
grep -rn 'verify=\|INSECURE\|insecure' adapters/<name>/main.py
grep -rn 'EVALHUB_MODE' adapters/<name>/main.py
grep -rn 'TEST_DATA_DIR\|_hf_offline\|NLTK' adapters/<name>/main.py | head -20
```

## 16. Subprocess and process lifecycle

Reference: `adapters/guidellm/subprocess_utils.py`,
`adapters/nemo-guardrails/main.py:850-875` (`_stop_server` and the
`managed_server` contextmanager, the canonical teardown pattern),
`adapters/inspect/_execution.py:478`, `adapters/lm-eval/_execution.py:222`.

- [ ] Every `subprocess.run` has a `timeout`, inspects the exit code, and logs
      captured stdout/stderr. A run that parses results after a non-zero exit
      reports stale or partial numbers as success — **High**.
- [ ] `subprocess.Popen` children are stopped on success, failure and
      cancellation: teardown in `finally`, process-group kill (not just the
      parent), and a bounded wait before `kill()`. An orphaned server keeps the
      pod alive and poisons the next benchmark in a multi-benchmark job.
- [ ] Child environments are an explicit `os.environ.copy()` (or a fresh dict),
      not mutation of the parent's environment with one job's secret — the
      parent env is shared with later benchmarks and with MLflow uploads.
- [ ] Parallelism/worker knobs respect the container's CPU limit (PR #300 capped
      GuideLLM workers); unbounded workers thrash or OOM the pod.
- [ ] Work/temp directories live somewhere writable by the non-root UID
      (`/tmp`, `HOME=/tmp` in the image) and are removed in `finally` **after**
      artifacts are persisted.
- [ ] File handles for captured logs are closed on every path, including when
      `Popen` fails before exec.

Probes:

```bash
grep -n 'subprocess.run\|subprocess.Popen' adapters/<name>/*.py
grep -n 'timeout=' adapters/<name>/main.py | head -20
grep -n 'finally' -A6 adapters/<name>/main.py | head -40
grep -n 'terminate\|killpg\|kill()' adapters/<name>/*.py
```

## 17. Results: metrics, scores, artifacts, MLflow and OCI

References: CONTRIBUTING ("Annotating metric result types"),
`adapters/lighteval/main.py:227-251` (artifact gating and annotations),
`callbacks.mlflow.save(...)` / `callbacks.report_results(...)` in every adapter
that exports.

- [ ] `metrics_schema` is built alongside the `EvaluationResult` list with the
      right `ResultType` (`NUMERIC`, `CATEGORICAL`, `ARRAY_ORDERED`,
      `ARRAY_UNORDERED`, `TIME_SERIES`). A distribution emitted as `NUMERIC` (or
      the reverse) renders wrong in the UI without erroring.
- [ ] Metric names are stable across releases (PR #288 stabilised math metric
      names). A rename silently breaks `collections/*.yaml`
      `primary_score.metric`, pass/fail thresholds and historical comparison.
- [ ] `overall_score` handles zero results, zero examples and NaN/inf: no
      `ZeroDivisionError`, no `None` where a float is expected, and no NaN
      reaching the API.
- [ ] Result parsing tolerates framework schema drift loudly: a missing key or
      renamed field fails with context; it does not emit `0.0` or skip the metric
      silently.
- [ ] `create_oci_artifact(OCIArtifactSpec(files_path=...))` is given a directory
      that contains **all** files the results reference. `files[0].parent`
      silently drops siblings written elsewhere (per-sample JSONL, calibration
      subsets).
- [ ] OCI annotations keep the `io.github.eval-hub.{benchmark,model,job_id}`
      keys and the `created` timestamp; losing them breaks artifact lookup and
      provenance.
- [ ] MLflow persistence happens **before** `report_results`, and an upload
      failure propagates (PR #309: "propagate upload failures") instead of
      reporting success with missing artifacts.
- [ ] Artifacts are written before the `finally` block deletes the work
      directory; otherwise OCI/MLflow read nothing under load.

Probes:

```bash
grep -n 'metrics_schema\|ResultType' adapters/<name>/main.py | head -20
grep -n 'overall_score' -A6 adapters/<name>/main.py | head -40
grep -n 'create_oci_artifact' -B6 -A10 adapters/<name>/main.py
grep -n 'mlflow.save\|report_results' adapters/<name>/main.py
grep -n 'shutil.rmtree\|finally' adapters/<name>/main.py | head -20
```

## 18. Dependencies, Containerfile and packaging

References: `.github/workflows/verify-requirements.yml`, `.trivyignore`,
`adapters/lighteval/Containerfile`, `.github/workflows/build-images.yml`
(`IMAGE_MAP`).

- [ ] Pins added for `inspect` and `lighteval` exist on the Red Hat index
      (`https://packages.redhat.com/api/pypi/public-rhai/rhoai/3.6/cpu-ubi9/simple/`).
      A pin that only exists on PyPI fails `verify-requirements.yml` — and that
      workflow only covers those two adapters, so for the others check the pin
      by hand.
- [ ] `requirements.txt` changes come with a regenerated `requirements.lock` on
      the same Python (3.12). LightEval installs `--no-deps` from the lock only,
      so a stale lock means the new pin never reaches the image.
- [ ] `Containerfile` `COPY` lines include every module the adapter imports. A
      new helper that works under pytest (adapter dir on `sys.path`) but is not
      copied into the image fails only in the pod.
- [ ] The image runs as non-root at the end (`USER 1001`), caches are created and
      chowned as root before the switch, `PYTHONUNBUFFERED=1` stays, and
      `ENTRYPOINT` matches `provider.yaml`.
- [ ] No unreproducible build-time network fetch, and no dependency bump that
      changes framework behaviour without a note in the PR body.
- [ ] Every new `.trivyignore` entry carries `exp:YYYY-MM-DD`, a reachability
      argument and a removal condition. An entry without them is a **Medium**
      finding (silent CVE suppression).
- [ ] Image name/tag changes stay in sync across `Makefile` (`IMAGE_*`), CI
      `IMAGE_MAP`, `provider.yaml`, README tables, and
      `TOOLBENCH_SERVER_VERSION` for the tooleval pair.
- [ ] `requirements-test.txt` additions are test-only; moving a runtime import
      into it makes the image miss a dependency.

Probes:

```bash
git diff --stat "$(git merge-base origin/main HEAD)"...HEAD -- '*requirements*' '*constraints*'
grep -n 'COPY\|ENTRYPOINT\|USER' adapters/<name>/Containerfile
grep -n 'IMAGE_MAP' -A6 .github/workflows/build-images.yml
sed -n '1,40p' .trivyignore
```

## 19. Tests and CI wiring

References: `adapters/lighteval/tests/conftest.py`, `tests/test_adapter.py`
(`create_autospec(JobCallbacks)`, monkeypatching `_run_lighteval`),
`.github/workflows/test-<name>.yml` (runs `-m "not local"`), `Makefile`
`test-<name>` / `images` / `push-images` / `clean-images` / `tests`.

- [ ] Tests monkeypatch the framework invocation (e.g. `_run_lighteval`) and use
      `create_autospec(JobCallbacks)`; patching the SDK or callback layer instead
      hides the plumbing the test exists to protect.
- [ ] New branches are covered: success path, framework failure (FAILED status
      reported **and** exception re-raised), no OCI config (phase skipped), OCI
      configured (phase + artifact), malformed framework output, zero extracted
      metrics.
- [ ] Marker discipline: `local`, `openai_endpoint`, `integration`. CI runs
      `-m "not local"`, so a new test needing Ollama/vLLM/network must carry the
      marker or the default job fails; conversely a `local` marker on a pure unit
      test hides it from CI.
- [ ] `conftest.py` only extends `sys.path` with the adapter directory; new
      fixtures do not reach into repo-root files that do not exist in the image.
- [ ] A new adapter PR adds `.github/workflows/test-<name>.yml` (missing today
      for `ruler`, `swebench`, `tooleval` and `pyrit`) and `Makefile` targets
      `image-<name>`, `push-<name>`, `clean-<name>`, `test-<name>`, plus the
      aggregate `images`/`push-images`/`clean-images`/`tests` lines and the
      `help` text. Missing wiring means the adapter is never built or tested by
      CI — **Medium**.
- [ ] README tables are updated: a row in "Supported Frameworks" and in "MLflow
      and OCI Export Tracking", with claims matching what the adapter does (see
      PR #310 for native-identity behaviour).
- [ ] `meta/job.json` matches the adapter's parameters and stays a valid,
      runnable sample (tests and docs use it).
- [ ] A `fix(...)` commit includes a regression test for the reported defect;
      state the exact uncovered behaviour rather than asking for "more tests".

Probes:

```bash
ls .github/workflows/test-*.yml
grep -n '^tests:\|^images:\|^push-images:\|^clean-images:' Makefile
grep -n 'monkeypatch.setattr' adapters/<name>/tests/*.py | head -20
grep -rn 'pytest.mark' adapters/<name>/tests/*.py | head -10
git diff --name-only "$(git merge-base origin/main HEAD)"...HEAD -- README.md adapters/<name>/README.md
```

## 20. Cross-repo coupling with eval-hub (the reverse of §12)

A contrib adapter is half of a contract whose other half lives in
`eval-hub/config/providers/<name>.yaml` and its benchmark fixtures. A contrib PR
that changes that contract is only correct after eval-hub follows, so treat a
PR-body sentence like "eval-hub change in PR #N" as a claim to verify.

- [ ] A change to `provider.yaml` `id`, `benchmarks[].id`, `metrics`, or a
      parameter name/default that eval-hub's catalog or FVT fixtures reference
      has a matching eval-hub PR; check its state with
      `gh api repos/eval-hub/eval-hub/pulls/<n> --jq '{state, merged}'`.
- [ ] The two catalogs are not name-identical by design: contrib `ibm-clear`
      vs directory `clear`, `evalhub-internal` vs `evalhub-post-processor`,
      `lm-eval` vs collections' `lm_evaluation_harness`. Compare file contents,
      not names, before declaring drift.
- [ ] `runtime.k8s.image` in `provider.yaml` points at `:latest`, so eval-hub
      picks up whatever merged last. A PR that *requires* new adapter behaviour
      is not deployable in a pinned environment until a `v*` release branch
      publishes a versioned tag (README "Publishing a Versioned Framework
      Image") — say so instead of "merge and it works".
- [ ] Credential-contract changes (role names, secret key conventions, local
      `file:///` auth dir) are mirrored in `docs/model-role-auth.md`, the
      adapter table, and eval-hub's sidecar expectations. A role added in one
      place and not the other is a **High** for the adapters that use it.
- [ ] `collections/*.yaml` entries resolve against a provider that exists in
      eval-hub's `config/collections/` and `config/providers/` (or against
      contrib's own `provider.yaml` when the collection targets a contrib
      adapter). A collection that names a missing benchmark fails at submit
      time.
- [ ] Docs that claim "supported by eval-hub" (README tables, adapter READMEs)
      match what the eval-hub release actually ships; a capability advertised
      before the catalog change merges misleads users.

Probes:

```bash
gh pr view <n> --json body --jq .body | grep -n -iE 'eval-hub PR|contrib|catalog|sidecar'
gh api repos/eval-hub/eval-hub/pulls/<evalhub-pr> --jq '{state, merged}'
# fetch the other half of the contract; -fsSL keeps a 404/moved file separate
# from a grep no-match. Write to a file and only inspect it after curl succeeds,
# so head cannot mask a fetch failure.
tmp=$(mktemp)
if curl -fsSL -o "$tmp" \
  "https://raw.githubusercontent.com/eval-hub/eval-hub/main/config/providers/<name>.yaml"; then
  head -n 30 "$tmp"
else
  echo 'FETCH FAILED: contract unverified, not drift' >&2
fi
rm -f "$tmp"
git grep -n 'image:' -- 'adapters/*/provider.yaml'
git grep -n 'provider_id' -- collections
```

## 21. High-yield quick scan (contrib)

Run these once per review; they surface most recurring adapter defects.

```bash
# <base> is the base branch Step 1 resolved (the PR's baseRefName, or the
# repository's default branch). A working-tree target also includes staged and
# unstaged changes, so an adapter that is not in HEAD yet is still in scope.
mb=$(git merge-base "origin/<base>" HEAD)
git diff --stat "$mb"...HEAD
git diff --stat --cached "$mb"    # staged changes (working-tree target)
git diff --stat                   # unstaged changes (working-tree target)
# which adapters are in scope
{ git diff --name-only "$mb"...HEAD
  git diff --name-only --cached "$mb"
  git diff --name-only
} | grep '^adapters/' | cut -d/ -f2 | sort -u
# catalog drift overview
uv run --quiet --with pyyaml python - <<'PY'
import pathlib, yaml
for p in sorted(pathlib.Path("adapters").glob("*/provider.yaml")):
    d = yaml.safe_load(p.read_text()) or {}
    print(p.parent.name, "id=", d.get("id"), "type=", d.get("type"),
          "benchmarks=", len(d.get("benchmarks") or []))
PY
# adapters missing a catalog entry or CI workflow (pre-existing, but note new ones)
for d in adapters/*/; do n=$(basename "$d"); [ -f "$d/provider.yaml" ] || echo "no provider.yaml: $n"; done
for d in adapters/*/; do n=$(basename "$d"); [ -f ".github/workflows/test-$n.yml" ] || echo "no CI workflow: $n"; done
# JobPhase contract
grep -rn 'PERSISTING_ARTIFACTS\|COMPLETED\|ErrorInfo' adapters/<name>/main.py
# credential fallbacks that must not exist
grep -rn 'getenv' adapters/<name>/main.py | grep -iE 'key|token|secret|url'
# subprocess calls: check each has a timeout and an exit-code check
grep -rn 'subprocess.run' -A6 adapters/<name>/*.py
# packaging vs provider.yaml entrypoint
grep -n 'ENTRYPOINT' adapters/<name>/Containerfile; grep -n 'entrypoint' -A3 adapters/<name>/provider.yaml
# dependency + scan changes
git diff "$mb"...HEAD -- '*requirements*' '*constraints*' .trivyignore
```

## 22. Repository conventions (contrib)

- [ ] Conventional Commits `<type>(<adapter>): <subject>`, validated by
      commitizen (`.cz.toml`, `cz check --rev-range origin/main..HEAD`). Types
      in use: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`.
- [ ] `AGENTS.md` is a symlink to `CLAUDE.md`; editing one edits both, so a
      docs change must not leave contradictory guidance in the other.
- [ ] `Makefile` `help` text, `images`/`push-images`/`clean-images`/`tests`
      aggregates and the README build/test command lists stay in sync when a
      target is added, renamed or removed. A target that exists but is
      unreachable from `make images` silently ships nothing.
- [ ] `.github/workflows/build-all-images.yml`'s adapter matrix, the
      `build-images.yml` change detection and `adapters/` stay in sync: a new
      directory that nobody listed is never published.
- [ ] No committed `__pycache__/`, `.venv/`, `.pytest_cache/` or lockfile churn
      unrelated to the PR's stated purpose.
- [ ] A comment or README section describing behaviour that no longer exists is
      a **Low** finding; report it once, not per line.

