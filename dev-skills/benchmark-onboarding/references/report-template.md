# Benchmark QA report: `<benchmark_id>`

## Summary

**Result:** `<PASS | FAIL | BLOCKED | PARTIAL>`

**Provider / benchmark:** `<provider_id> / <benchmark_id>`

**Run date:** `<UTC timestamp>`

Summarize what passed and what remains unverified. Do not call a run successful
when the evaluation job did not reach `completed`.

## Source and implementation

| Item | Value |
| --- | --- |
| Upstream task link | `<URL>` |
| Dataset repo / subset / split | `<repo> / <subset> / <split>` |
| Tokenizer | `<repo or staged path>` |
| Framework and dependency versions | `<versions>` |
| Contrib branch / commit | `<branch and SHA, or N/A>` |
| EvalHub branch / commit | `<branch and SHA, or N/A>` |
| Image | `<reference, platform, digest>` |

## Cluster resources provisioned

| Namespace | Resource | Purpose / source | Cleanup |
| --- | --- | --- | --- |
| `<namespace>` | `<PVC, Secret reference, ConfigMap, service, or N/A>` | `<purpose; never include Secret data>` | `<removed, retained shared fixture, or N/A>` |

## Scenario results

| Scenario / annotation | Mode | Parameters exercised | API / job result | Evidence |
| --- | --- | --- | --- | --- |
| `<case>` | Connected | `<values>` | `<status and metrics>` | `<job ID/log path>` |
| `<case>` | Disconnected | `<values and test_data_ref>` | `<status and metrics>` | `<job ID/log path>` |

List the parameter-coverage matrix or link to it. Note values that are
unsupported and why.

### Egress controls

| Item | Evidence |
| --- | --- |
| Policy selector and enforcement scope | `<labels; pod-scoped or stronger mechanism>` |
| Allowed destinations | `<DNS, model, EvalHub, MLflow, OCI, fixture endpoints actually configured>` |
| Hugging Face / general Internet | `<blocked probe or other evidence>` |
| Adapter offline flags | `<flags and runtime evidence>` |
| Boundary | `<state whether allowed sidecar destinations are also reachable by the adapter>` |

## Failure analysis

| Test | Symptom | Evidence | Cause and confidence | Impact / next action |
| --- | --- | --- | --- | --- |
| `<case>` | `<observed failure>` | `<API, init, adapter, sidecar, or cluster evidence>` | `<analysis>` | `<fix or prerequisite>` |

Use `None` when no test failed.

## Limitations and PRs

- `<missing cluster, fixture, credential, or other limitation>`
- Contrib PR: `<URL or no code change required>`
- EvalHub PR: `<URL or no code change required>`
