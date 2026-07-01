---
name: evalhub
description: "Use when evaluating AI/ML models, running benchmarks, checking evaluation status, listing providers or collections, or performing model quality and safety assessments. Covers EvalHub provider discovery, benchmark execution, job lifecycle, and Evaluation-Driven Development (EDD) workflows."
user-invocable: true
---

# EvalHub Skill

Run AI/ML model evaluations against an EvalHub service. Supports provider discovery, benchmark execution, job lifecycle management, and Evaluation-Driven Development (EDD) workflows.

All provider and collection knowledge comes from the API at runtime. Do not hardcode provider names, benchmark IDs, or categories — always discover them dynamically.

## Rules

- **Prefer MCP over scripts** — if the `evalhub` MCP server is connected (its tools appear as `mcp__evalhub__*`), use MCP tools and resources for all operations. Fall back to Python scripts only when MCP is unavailable or for operations with no MCP equivalent (logs, health check).
- **Use ONLY the provided scripts when not using MCP** — never write custom Python, jq, or inline code to process results. The scripts already format output.
- **Minimise API calls** — one round of two parallel reads (`evalhub://providers` + `evalhub://collections` via MCP, or `--agent` scripts) gives you ALL agent metadata. Do not fetch individual providers afterwards.
- **No health check** — skip `evalhub_check.py` unless the user reports connectivity problems.
- **Suppress stderr** — always append `2>/dev/null` to script invocations to hide TLS and SDK diagnostic output.
- **Be concise** — answer the user's question directly. Do not narrate each tool or script invocation.

## Prerequisites

Three environment variables must be set:

| Variable | Purpose | Example |
|----------|---------|---------|
| `EVALHUB_BASE_URL` | EvalHub API base URL | `https://evalhub.apps.cluster.example.com` |
| `EVALHUB_TOKEN` | Bearer token for auth | `sha256~...` (from `oc whoami -t`) |
| `EVALHUB_TENANT` | Namespace / tenant | `eval-test` |

If variables are missing, ask the user. For OpenShift clusters, the token is typically obtained with `oc whoami -t`.

## Provider and Collection Discovery

Providers and collections expose structured agent metadata via the API. Use these fields to make context-aware recommendations.

### Discovery Strategy

**For most questions, a single round of two parallel calls is enough:**

```bash
# Run BOTH in parallel — this is the default starting point
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --agent 2>/dev/null
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py --agent 2>/dev/null
```

The `--agent` output contains the COMPLETE agent metadata block for every provider/collection (evaluates, target_type, summary, recommended_when, hints, result_interpretation, complements). Do not make additional calls to fetch individual providers — everything you need is already in this output.

**Only add filters when the user's intent clearly maps to one:**

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --target-type agent 2>/dev/null
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --evaluates safety 2>/dev/null
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py --evaluates safety 2>/dev/null
```

**Fetch a single provider only when the user explicitly asks for its benchmark list:**

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py PROVIDER_ID 2>/dev/null
```

### How to Use Agent Metadata

Each provider and collection may include an `agent` block with these fields:

| Field | Purpose |
|-------|---------|
| `evaluates` | Semantic tags — match against user intent (e.g. user says "safety" -> filter for `safety` tag) |
| `target_type` | What the provider evaluates: `model`, `agent`, or `inference_server` |
| `summary` | Concise description for presenting to the user |
| `recommended_when` | Natural-language conditions for when to suggest this provider |
| `hints` | Operational guidance for constructing valid job requests |
| `result_interpretation` | How to read and present results to the user |
| `complements` | IDs of providers/collections that pair well — suggest after a run |

When the user asks to evaluate something:

1. **Match intent to `evaluates` tags**: user says "check safety" -> `--evaluates safety`
2. **Check `target_type`**: user says "my agent" -> `--target-type agent`
3. **Read `hints`** before constructing the job: model naming, required secrets, parameters
4. **Use `result_interpretation`** when presenting results: metric direction, baselines
5. **Suggest `complements`** after a run: "consider also running X for a complete picture"

### Recommending Collections vs Individual Benchmarks

- Prefer **collections** when the user wants a comprehensive assessment ("evaluate my model", "check safety")
- Use **individual benchmarks** when the user names a specific benchmark or wants a quick check
- Collections have curated weights and pass thresholds — they represent expert-designed evaluation suites

## MCP Mode (preferred)

When the `evalhub` MCP server is connected, its tools are available as `mcp__evalhub__*` in the tool list. **Always prefer MCP over Python scripts** — it requires no `uv` or Python and is lower latency.

### MCP tools (write/action operations)

| Tool | Purpose | Replaces |
|------|---------|---------|
| `mcp__evalhub__submit_evaluation` | Submit a new evaluation job | `evalhub_eval.py` |
| `mcp__evalhub__get_job_status` | Get job status and progress | `evalhub_status.py JOB_ID` |
| `mcp__evalhub__cancel_job` | Cancel a running or pending job | `evalhub_status.py JOB_ID --cancel` |

### MCP resources (discovery and read operations)

Use `ReadMcpResourceTool` with server `evalhub`:

| URI | Replaces |
|-----|---------|
| `evalhub://providers` | `evalhub_providers.py --agent` |
| `evalhub://benchmarks` | `evalhub_providers.py --benchmarks` |
| `evalhub://collections` | `evalhub_collections.py --agent` |
| `evalhub://jobs` | `evalhub_status.py --list` |
| `evalhub://server-version` | — |

**Waiting for completion via MCP:** poll `mcp__evalhub__get_job_status` until state is `completed`, `failed`, `cancelled`, or `partially_failed`.

### Fall back to Python scripts when

- MCP is not connected (`mcp__evalhub__*` tools are absent from the tool list)
- Fetching job logs — `evalhub_logs.py JOB_ID` (no MCP equivalent yet)
- Health check — `evalhub_check.py` (skip unless the user reports connectivity problems)

## Core Operations

### Check Health

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_check.py
```

### List Providers

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py                  # summary with evaluates, target_type
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py PROVIDER_ID      # single provider full details
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --agent          # full agent metadata
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --benchmarks     # all benchmarks
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --target-type model
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --evaluates safety
```

### List Benchmarks

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --benchmarks
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --benchmarks --provider PROVIDER_ID
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py --benchmarks --category CATEGORY
```

### List Collections

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py COLLECTION_ID
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py --agent
uv run ~/.claude/skills/evalhub/scripts/evalhub_collections.py --evaluates CAPABILITY
```

### Create an Evaluation Job

With individual benchmarks (discover provider and benchmark IDs first):

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_eval.py \
  --model-url http://model-server:8000/v1 \
  --model-name my-model \
  --provider PROVIDER_ID \
  --benchmark BENCHMARK_ID
```

With a collection:

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_eval.py \
  --model-url http://model-server:8000/v1 \
  --model-name my-model \
  --collection COLLECTION_ID
```

From a JSON file:

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_eval.py --json request.json
```

Optional flags: `--name`, `--tag`, `--num-examples N`, `--threshold 0.7`, `--experiment-name`, `--queue`.

### Get Job Status

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py JOB_ID
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py JOB_ID --wait
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py JOB_ID --wait --timeout 600
```

Job states: `pending` -> `running` -> `completed` | `failed` | `cancelled` | `partially_failed`.

### List Jobs

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py --list
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py --list --status running
```

### Get Job Logs

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_logs.py JOB_ID
```

### Cancel a Job

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_status.py JOB_ID --cancel
```

## Interpreting Results

After a job completes, fetch the provider to read its agent metadata:

```bash
uv run ~/.claude/skills/evalhub/scripts/evalhub_providers.py PROVIDER_ID
```

Use `agent.result_interpretation` to explain scores (metric direction, baselines, score ranges). Use `agent.complements` to suggest follow-up evaluations. Do not write custom code to process or filter the JSON — read the output directly.

## Evaluation-Driven Development (EDD)

EDD is the AI equivalent of TDD. The cycle:

1. **Define Criteria** — Discover providers/collections using `--evaluates` and `--target-type`. Read `recommended_when` and `hints` to select the right evaluation.
2. **Measure Scores** — Run the evaluation. Use `result_interpretation` to explain results to the user.
3. **Iterate** — Use `complements` to suggest follow-up evaluations. Refine model/prompts and re-evaluate.

See [references/EDD.md](references/EDD.md) for the complete workflow guide.

## Using the SDK Directly

All scripts use the `eval-hub-sdk` Python package. For inline usage:

```python
from evalhub import SyncEvalHubClient, JobSubmissionRequest, ModelConfig, BenchmarkConfig

client = SyncEvalHubClient(
    base_url="https://evalhub.apps.example.com",
    auth_token="sha256~...",
    tenant="eval-test",
)

# Discover providers with agent metadata
providers = client.providers.list()
for p in providers:
    if p.agent:
        print(f"{p.resource.id}: {p.agent.summary}")
        print(f"  evaluates: {p.agent.evaluates}")
        print(f"  target_type: {p.agent.target_type}")

# Submit a job (use IDs discovered from the API)
job = client.jobs.submit(JobSubmissionRequest(
    name="my-eval",
    model=ModelConfig(url="http://model:8000/v1", name="my-model"),
    benchmarks=[BenchmarkConfig(id="BENCHMARK_ID", provider_id="PROVIDER_ID")],
))

# Wait for completion
result = client.jobs.wait_for_completion(job.resource.id, timeout=600)
```

## Gotchas

- **Token expiry**: OpenShift tokens expire. If you get 401 errors, ask the user to refresh with `oc whoami -t`.
- **Tenant required**: Every API call (except health) requires `EVALHUB_TENANT`. This maps to the Kubernetes namespace.
- **Base URL format**: Use the root URL without `/api/v1` suffix. The SDK appends the API path automatically.
- **Model URL**: Must be an OpenAI-compatible inference endpoint (e.g. vLLM, TGI). Include the `/v1` path if required by the server.
- **Long-running jobs**: Evaluation jobs can take minutes to hours. Use `--wait` with `--timeout` to avoid indefinite polling.
- **`num_examples`**: For quick iteration, pass `--num-examples 10` to run a subset of a benchmark.
- **Agent metadata availability**: Not all providers/collections may have agent metadata yet. Fall back to `description` and `category` fields when `agent` is absent.
- **Always discover first**: Never assume a provider or benchmark exists — always list from the API before referencing by ID.

## Reference

- [Full API reference](references/API.md) — endpoints, schemas, query parameters
- [EDD workflow guide](references/EDD.md) — Evaluation-Driven Development steps
- [Job template](assets/eval-job-template.json) — template for the evaluation job request body
