# eval-hub-skills

[![Lint](https://github.com/ruivieira/eval-hub-skills/actions/workflows/lint.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/lint.yml)
[![Test](https://github.com/ruivieira/eval-hub-skills/actions/workflows/test.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/test.yml)
[![Validate](https://github.com/ruivieira/eval-hub-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/ruivieira/eval-hub-skills/actions/workflows/validate.yml)

Agent Skills for EvalHub, following the [agentskills.io](https://agentskills.io) open format.

These skills enable AI coding agents (Claude Code, Copilot, Codex, etc.) to discover and execute EvalHub model evaluations during development sessions.

## Skills

| Skill | Description |
|-------|-------------|
| `evalhub` | Full skill — discovery, evaluation, job lifecycle, and EDD workflows |
| `evalhub-discovery` | Discover providers, benchmarks, and collections; read agent metadata |
| `evalhub-eval` | Submit evaluation jobs against benchmarks or collections |
| `evalhub-jobs` | Monitor, wait on, cancel, and fetch logs for evaluation jobs |

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (scripts use PEP 723 inline metadata for auto-dependency resolution)
- Network access to an EvalHub service
- `EVALHUB_BASE_URL`, `EVALHUB_TOKEN`, `EVALHUB_TENANT` environment variables

### Install via Claude Code plugin (recommended)

```bash
/plugin marketplace add eval-hub/eval-hub-skills
/plugin install evalhub@evalhub
```

The skill is then available as `/evalhub:evalhub` in any Claude Code session.

### Install locally (development)

Clone the repo and symlink the skills into `~/.claude/skills/`:

```bash
git clone https://github.com/eval-hub/eval-hub-skills
cd eval-hub-skills
make install-all   # installs all four skills
```

To install only the primary skill:

```bash
make install
```

Changes to the skill source are reflected immediately without reinstalling.

### Uninstall

```bash
make uninstall-all   # remove all skills
make uninstall       # remove primary skill only
```

### Update

```bash
make update-all
```

### Validate

```bash
make check
```

## Configuration

Set these environment variables before using the skill:

```bash
export EVALHUB_BASE_URL="https://evalhub.apps.cluster.example.com"
export EVALHUB_TOKEN="$(oc whoami -t)"
export EVALHUB_TENANT="eval-test"
```

Optionally, for clusters with self-signed certificates:

```bash
export EVALHUB_INSECURE=true
```

## Usage

Once installed, the skill is automatically discovered by Claude Code. Ask naturally in any session.

### Example: discover what providers are available

> **You:** What evaluation providers are available?

The skill fetches live metadata from the API and summarises each provider:

```
Available providers:

- AgentDojo — Test agent resilience to prompt injection across realistic tool-use
  scenarios. Targets: agent. Evaluates: agent-safety, prompt-injection,
  tool-use-security.

- LM Evaluation Harness — Comprehensive evaluation framework with 180 benchmarks
  covering math, science, coding, safety, reasoning, and more.

- Garak — LLM vulnerability scanner and red-teaming framework.

- GuideLLM — Performance benchmarking for LLM inference servers.

- SWE-bench — Software engineering benchmark using real-world GitHub issues.

- Lighteval — Lightweight LLM evaluation from Hugging Face.
```

---

### Example: find providers for a specific use case

> **You:** Which providers can evaluate my agent for prompt injection?

```json
[
  {
    "id": "agentdojo",
    "name": "AgentDojo",
    "summary": "Test agent resilience to prompt injection across realistic tool-use scenarios",
    "target_type": "agent",
    "evaluates": ["agent-safety", "prompt-injection", "tool-use-security"]
  }
]
```

> **Claude:** AgentDojo is the right fit here. It runs your agent through realistic
> tool-use scenarios (workspace, Slack, banking, travel) and measures both utility
> (task completion) and security (injection resistance). The model must support
> tool/function calling via an OpenAI-compatible API.

---

### Example: list available evaluation collections

> **You:** What evaluation suites are available?

```json
[
  {
    "id": "standard-llm-evals-v1",
    "name": "Standard LLM Evaluation Suite v1",
    "category": "general"
  },
  {
    "id": "reasoning-v1",
    "name": "Reasoning v1",
    "category": "reasoning"
  },
  {
    "id": "coding-v1",
    "name": "Coding v1",
    "category": "code"
  },
  {
    "id": "instruction-following-v1",
    "name": "Instruction Following v1",
    "category": "instruction_following"
  },
  {
    "id": "long-context-v1",
    "name": "Long Context v1",
    "category": "long_context"
  },
  {
    "id": "toxicity-and-ethical-principles",
    "name": "Toxicity and Ethical Principles",
    "category": "safety"
  }
]
```

---

### Example: submit an evaluation job

> **You:** Run the standard LLM eval suite against my model at
> `http://vllm-svc:8000/v1` (model name: `mistral-7b-instruct`).

```json
{
  "resource": {
    "id": "eval-mistral-7b-instruct-a3f2c1",
    "created_at": "2026-06-07T14:23:11Z"
  },
  "name": "eval-mistral-7b-instruct",
  "state": "pending"
}
```

> **Claude:** Job submitted. ID: `eval-mistral-7b-instruct-a3f2c1`. The standard
> suite covers instruction following, reasoning, math, coding, and long-context tasks.
> It runs multiple benchmarks with 3 seeds each — expect it to take 30–60 minutes.
> Say "check the status" or "wait for it to finish" when you're ready.

---

### Example: check job status

> **You:** What's the status of my eval jobs?

```json
[
  {
    "id": "eval-mistral-7b-instruct-a3f2c1",
    "name": "eval-mistral-7b-instruct",
    "state": "running",
    "created_at": "2026-06-07T14:23:11Z"
  }
]
```

---

### Example: EDD — measure impact before and after a change

> **You:** I'm about to refactor my model's safety guardrails. What should I
> run before and after to measure the impact?

> **Claude:** I'd suggest this before/after plan using the live providers:
>
> **Before:** Run `toxicity-and-ethical-principles` (covers toxic content,
> truthfulness, and HHH alignment) and `garak` (vulnerability scan for known
> attack patterns) to establish a baseline.
>
> **After:** Run the same two suites. Diff the scores — a regression in
> `toxigen` or `truthfulqa_mc1` means the refactor weakened a safety property.
>
> Want me to kick off the baseline run now?

## License

Apache-2.0
