# Benchmark source, implementation, and validation workflow

## Source and support audit

For every supplied link, identify the benchmark ID, framework task name, pinned
framework version, dataset repository/subset/split, license or access gate,
custom dataset code, tokenizer, scoring type, metrics, expected direction, and
model endpoint requirements. Read the task configuration used by the pinned
framework release; a high-level README can omit loader behavior and defaults.

Build a support matrix before editing:

| Surface | What to verify |
| --- | --- |
| Source task | Task ID, config, dataset repo/subset/split, custom code, license/access |
| Contrib adapter | Provider ID, task mapping, declared parameters, requirements, container base |
| EvalHub catalog | Provider and benchmark IDs, metrics, score direction, threshold, runtime image |
| API tests | Request parameters, annotations, result assertions, offline assets |

Check both repositories and their open PRs first. The same framework may be
exposed through distinct providers (for example, the native
`lm_evaluation_harness` runtime and the contrib `lm-eval` adapter). Use the
provider the user intends to add; do not assume one provider's registration
updates the other.

## Cluster test resource preflight

Before submitting a job, derive its dependencies from the request fixture,
provider runtime, test-data reference, init containers, and model endpoint. In
the target namespace, check for the referenced model-auth Secret, disconnected
dataset-source Secret, registry pull Secret when required, PVC, ConfigMaps,
and in-cluster model/service endpoints. Check resource names and metadata only;
never dump Secret data. A Secret referenced by the job must exist in the job's
namespace and contain the keys required by the runtime.

Create missing PVCs using a storage class available on the cluster and enough
capacity for the dataset, tokenizer, cache, and temporary writable copy. Wait
for the claim to bind, stage the exact assets, and verify expected paths and
file counts before the API request. Create missing namespace-scoped Secret
references from credentials already supplied by the user or an approved
credential source. If credentials, storage capacity, or a required endpoint are
unavailable, stop before submitting the evaluation and report the specific
dependency; do not invent credentials or use a placeholder Secret.

Record which test resources were created and their namespaces. Remove temporary
PVCs, staging Jobs, ConfigMaps, and test-only providers after preserving the
report. Keep a fixture in the shared test bucket only when the repository's
disconnected FVTs depend on that exact prefix.

If the task is already present, compare its metadata and tests against the
source. Reuse existing coverage and report any gap. Add only missing or incorrect
pieces. Do not create a benchmark PR merely to attach a report when no code or
test change is needed.

## Changes across repositories

Read repository `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, provider examples,
PR templates, and commit-message rules before editing. Keep one fresh branch per
repository, based on its current `main`; inspect the diff and check for an open
equivalent PR before publishing.

In `eval-hub-contrib`, update the adapter's provider definition, task registry
or generator inputs, dependency pins, runtime code, and adapter tests only as
required by the source task. Verify that every declared option is implemented
and that task metadata comes from the same pinned framework release used in the
image. Keep dataset scripts and `trust_remote_code` behavior explicit.

In `eval-hub`, update the matching provider/catalog entries, collection entries
when requested by the catalog design, API feature data, expected-result fields,
and asset stagers or manifests required by disconnected testing. Keep the
provider ID and benchmark ID consistent with contrib. Follow the test helpers
already in `tests/features`; do not invent a parallel schema or fixture format.

## Parameter coverage

Read the provider schema, adapter parameter handling, and upstream task config.
Create a table for every applicable parameter with its declared type/default,
supported values, test payload, and expected behavior. Include each meaningful
enum value and both sides of relevant booleans. Cover valid boundaries and
document invalid values only where the API promises validation. Use focused
cases or pairwise combinations to avoid an unbounded Cartesian product, while
still asserting every applicable parameter at least once.

Separate task options from runtime controls. A task's dataset subset, split,
few-shot count, and tokenizer can be benchmark-specific; model URL, batch size,
timeouts, offline references, and authentication may be provider/runtime
controls. Do not include generation-only fields in a log-likelihood task unless
the adapter consumes them.

## API scenarios and cluster validation

Read `eval-hub/tests/features/README.md` and nearby scenarios for the current
tags and payload helpers. Add focused connected and disconnected scenarios with
the repository's `@connected`, `@disconnected`, `@cluster`, and provider/evaluation
annotations as appropriate. Use the Jsonnet benchmark helper when available so
connected tokenizer defaults and disconnected `test_data_ref` behavior match
the test harness.

For connected runs, submit through the EvalHub API using the intended provider,
model endpoint, and an existing auth Secret reference. Confirm the request is
accepted, the job and benchmark reach a terminal successful state, the dataset
and tokenizer load, expected metrics and metadata are returned, and the sample
limit is honored.

For disconnected runs, stage the exact dataset cache and tokenizer at the
fixture location expected by the adapter. Ensure the evaluation job is subject
to the disconnected or egress-restricted path while the administrative staging
step can access its source. Prefer a pre-staged PVC when the evaluation pod must
have no public egress; an S3 or remote fixture source must be explicitly
allowlisted for the init container and is shared with every container in the
pod. A physical disconnected cluster needs pre-staged assets; an `hf_offline`
flag without local assets does not prove offline support.

Before the evaluation Job is created, install an egress allowlist scoped to the
test provider or unique benchmark pod labels. Permit cluster DNS and only the
configured model, EvalHub callback, MLflow, OCI, and fixture endpoints the run
needs. If those services are external, use a stable approved CIDR or the
cluster's FQDN-aware egress gateway; standard NetworkPolicy does not select a
Service by DNS name. Keep Hugging Face and general Internet destinations out of
the allowlist. Inspect the generated pod labels and policy selection before
submitting the API request, then verify the policy is effective while the job
runs. Inspect the pod's resolver configuration and the cluster DNS Service
target ports; the CNI may evaluate DNS egress against the Service IP, the DNS
pods, or a translated target port. Allow the working in-cluster DNS path only.
The sidecar proxy URL should be local to the pod, and the `lm_eval`
subprocess should have Hugging Face Hub, datasets, and Transformers offline
flags enabled when using staged assets.

NetworkPolicy applies to the pod as a whole, and all its containers share a
network namespace. Therefore it can block unapproved Internet/Hugging Face
traffic and permit the sidecar's configured destinations, but it cannot prove
that the adapter process itself is unable to connect directly to those same
allowed destinations. State this limitation in the report. If a user requires
sidecar-only external access, stop before claiming that guarantee and discuss a
separate-pod proxy, service-mesh, or CNI-specific enforcement design.

If an init container fails before the adapter starts, capture its logs and
Kubernetes Job state because the EvalHub API may not receive a terminal event.

When the provider exposes an offline control such as `hf_offline`, set it for
the disconnected case and assert the returned metadata reports it. For
EvalHub's benchmark FVTs, use the shared `benchmark()` helper so the offline
case receives its benchmark-scoped S3 `test_data_ref` and `/test_data/tokenizer`
path. Confirm the init container downloaded files and the adapter loaded the
dataset from the staged path with downloads disabled.

Build with the repository's image target and inspect the selected cluster node
architecture (`kubernetes.io/arch`). Rebuild for the target platform if the
local Podman host produced a different architecture. Use a unique test image
tag, verify its digest, deploy through the established test workflow, and
record the actual image running in the evaluation pod. Do not overwrite shared
`latest` or production tags.

For a successful disconnected case, record both application-level offline
flags and network-policy evidence. A blocked Hugging Face probe from the pod
proves that the pod cannot reach that destination; it does not prove which
container attempted a connection. Do not report container-specific network
isolation unless the cluster provides and the test verifies a per-container
enforcement mechanism.

## Reporting and PRs

Use [report-template.md](report-template.md). Preserve test timestamps, provider
and benchmark IDs, image digest/platform, request parameter matrix, dataset and
tokenizer source, API/Kubernetes states, and sanitized relevant log excerpts.
For failures, separate benchmark defects from missing credentials, missing
offline fixtures, model endpoint problems, and test infrastructure failures;
state the evidence and confidence for each cause.

Add the full QA report under the contrib PR template's testing section. Wrap
it in a GitHub Markdown disclosure block, with blank lines around the report
so its headings, tables, and lists render inside the block.

```markdown
<details>
<summary>Expand the benchmark QA report</summary>

<!-- Replace this comment with the completed Markdown report. -->

</details>
```

Keep the full report in the PR body even if a copy exists in the repository.
After publishing, check that the contrib PR description contains the
collapsible report. Cross-link the contrib and eval-hub PRs so reviewers can
find the report from either repository. If a repository has no required
change, explain that in the report and skip opening a PR for it. Keep bearer
tokens, model keys, Hugging Face tokens, and Secret contents out of the report.
