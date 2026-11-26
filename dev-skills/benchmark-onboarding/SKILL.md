---
name: benchmark-onboarding
description: >-
  Onboard an evaluation benchmark from upstream task links into the appropriate
  eval-hub repositories, then validate its dependencies, data, tokenizer, and
  API behavior on connected and disconnected OpenShift environments. Use when
  adding a benchmark, not for general provider reviews.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Benchmark Onboarding

Use this skill when a user provides upstream benchmark links and asks to add or
validate the benchmark in eval-hub. The full workflow updates the required
repositories, builds and deploys the affected image, runs EvalHub API scenarios,
writes a Markdown QA report, and opens the required PRs. Never merge a PR.

## Workflow

1. Read the supplied source pages and the current instructions, catalog, adapter,
   test conventions, and PR templates in `eval-hub/eval-hub-contrib` and
   `eval-hub/eval-hub`.
2. Check whether the benchmark, tests, or a matching open PR already exist. Map
   the source task to the actual EvalHub provider and its task ID. Do not create
   duplicate catalog entries or empty PRs. If it is already supported, validate
   the existing path and report that no benchmark change is needed.
3. Run the [access and resource preflight](references/workflow.md#access-and-resource-preflight).
   Resolve the cluster, tenant, registry, model endpoint, and fixture locations
   from the request and existing configuration. Reuse the configured access and
   provision missing test resources before submitting jobs. Ask only when a
   required decision, credential, or approval cannot be resolved.
4. For each repository that needs changes, start from current `main` on a fresh
   branch. Update the benchmark catalog/adapter and generate focused API
   scenarios that cover every applicable option and parameter in connected and
   disconnected modes. Read [workflow.md](references/workflow.md) for source,
   image, and test requirements.
5. Build for the target cluster architecture, deploy with a unique image tag,
   and run the API scenarios with a small but real evaluation. Verify dataset
   loading, tokenizer loading, result metrics, and offline asset use. For a
   disconnected run, set the provider's offline controls and install a scoped
   egress allowlist before the job starts. Follow
   [egress-policy.md](references/egress-policy.md) and record its enforcement
   boundary. Do not treat an accepted job as a passing evaluation; inspect the
   terminal API and Kubernetes states.
6. Write the report using [report-template.md](references/report-template.md).
   Analyze each failure from API, init-container, adapter, sidecar, and cluster
   evidence. Embed the full report in a collapsible section in each contrib PR
   description using the wrapper in [workflow.md](references/workflow.md#reporting-and-prs).
   Cross-link the related eval-hub PR. Follow each repository's commit and PR
   conventions.

## Working rules

- An onboarding request authorizes routine steps in the agreed repositories and
  test environment. Carry them through without asking for confirmation at each
  step. Respect the tool host's approvals and any limits in the request.
- Test the same provider and benchmark ID that users submit through EvalHub.
- Test only options the task/provider actually supports. Record unsupported or
  inapplicable options with the reason; do not send meaningless combinations.
- Reuse existing model-auth Secret references when present. If a required Secret
  is missing, create it only from credentials supplied by the user or an
  approved credential source. Never print or copy secret values into requests,
  logs, reports, commits, or PR descriptions.
- Do not assume a cluster already has the secrets, PVCs, ConfigMaps, or service
  fixtures named by the test payloads. Check resource names and namespaces, then
  create the missing resources from approved credentials and cluster settings
  before running API scenarios. Never create placeholder credentials and call
  the resulting run a valid integration test.
- Check image architecture against cluster nodes; use unique test tags and
  record the image digest. Remove transient resources after saving evidence.
- A disconnected pass requires staged dataset and tokenizer assets and an
  egress-restricted evaluation path. If the fixture is absent, report the exact
  missing asset and leave the disconnected result failed or blocked.
- Standard Kubernetes NetworkPolicy is pod-scoped, and containers in a Pod
  share a network namespace. A pod allowlist blocks unapproved Internet and
  Hugging Face egress, but destinations allowed for the sidecar are also
  reachable by the adapter. Never claim per-container enforcement from a
  NetworkPolicy. If the requirement demands exclusive sidecar egress, pause the
  run and discuss a separate-pod, service-mesh, or CNI-specific design.
- Set Hugging Face offline flags in the evaluation subprocess as well as
  enforcing network policy. Treat the flags as application behavior, not a
  network boundary. Do not allow broad public egress; add only configured
  services and the minimum ports required by the run.
- Open PRs only for repositories with a real diff. If a required test fails,
  include the failure analysis and mark the PR draft when the defect blocks
  acceptance.
