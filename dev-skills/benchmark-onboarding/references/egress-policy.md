# Disconnected evaluation egress policy

Install a narrowly scoped egress policy before the evaluation pod is created.
Use the job's unique provider or execution labels when available; avoid a
benchmark-only selector in a shared tenant if another evaluation could match.
Inspect every existing Egress policy that selects the same pods. Kubernetes
policies are additive, so a matching allow-all policy can defeat a new
deny-by-default allowlist. If the CNI or cluster policy layer cannot enforce
the intended boundary, do not claim public egress is blocked.

Start from deny-by-default egress and allow only:

- Cluster DNS over UDP/TCP 53 and, where the CNI evaluates traffic after
  Service translation, the DNS pod's target port (inspect the DNS Service and
  pod before choosing). Some clusters also require allowing the DNS Service
  ClusterIP as well as its backing pods.
- The configured model endpoint.
- The in-cluster EvalHub callback endpoint.
- MLflow and OCI endpoints only when enabled for this evaluation.
- A data-source endpoint only when the evaluation pod's init container must
  fetch the fixture. Prefer staging the fixture on a PVC so this is unnecessary.

Select destinations by namespace and pod labels for in-cluster Services. A
standard Kubernetes NetworkPolicy cannot select a Service using its DNS name;
for external services, use a stable approved CIDR or an FQDN-aware egress
gateway supported by the cluster. Do not substitute a broad `0.0.0.0/0` or
`::/0` rule. Verify the cluster CNI enforces NetworkPolicy before relying on it.

Set the evaluation subprocess's Hugging Face Hub, datasets, and Transformers
offline flags when using staged data. Keep them enabled for the complete
`lm_eval` subprocess, including task imports and tokenizer loading. These flags
reduce accidental lookups but do not replace the network policy.

Kubernetes NetworkPolicy selects Pods. Containers in a Pod share the pod
network namespace, so the policy also applies to sidecar traffic. This allows
the sidecar to reach configured endpoints while blocking unapproved public
destinations, but it does not isolate the adapter from endpoints that the
policy allows. Record that limitation. For exclusive sidecar egress, a separate
proxy Pod, service mesh, or CNI-specific per-container mechanism requires a
separate architecture review and an explicit verification plan.

For the test report, record the exact selector, allowed endpoints and ports,
whether a pre-staged PVC avoided fixture downloads, policy status before job
creation, the adapter's offline flags, and the result of a harmless blocked
Hugging Face/Internet connectivity probe. Do not claim per-container packet
filtering based only on a pod-scoped policy.
