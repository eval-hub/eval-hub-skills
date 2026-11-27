# Local test environment profile

Configure the target once and reuse it for benchmark requests. Resolve the
profile before switching to a clone or worktree.

1. Use the profile path named in the prompt or in
   `BENCHMARK_ONBOARDING_PROFILE`, in that order. Resolve a relative path
   from the session's starting directory.
2. If neither is set, use the nearest `.evalhub/benchmark-onboarding.json`
   in the starting directory or its parents.
3. Apply explicit prompt overrides to profile values. Fill missing settings
   from unambiguous current configuration. Ask for the specific setting if
   a required target is still missing or ambiguous.

Use a local JSON file with settings like these:

```json
{
  "kube_context": "example-test-context",
  "tenant": "evalhub-test",
  "evalhub_url": "https://evalhub-test.example.org",
  "evalhub_service_url": "https://evalhub.evalhub-test.svc.cluster.local:8443",
  "test_image_repository": "quay.io/example/evalhub-adapter-test",
  "model": {
    "name": "example-model",
    "url": "http://model.inference.svc.cluster.local:8000/v1",
    "auth_secret_ref": "model-auth"
  },
  "test_data_s3": {
    "bucket": "evalhub-test-fixtures",
    "endpoint_url": "http://minio.storage.svc.cluster.local:9000",
    "secret_ref": "test-data-s3"
  }
}
```

Use `evalhub_url` for API requests and `evalhub_service_url` to identify the
callback service for the allowlist. Tag images uniquely in
`test_image_repository`. Use `model.auth_secret_ref` for the EvalHub
`model.auth.secret_ref` field, and use the bucket and S3 Secret for the
benchmark-specific test-data reference. The S3 endpoint is an input to the
disconnected egress check. Discover its backing Service and ports on the
cluster. If the run uses a PVC fixture, use the configured claim from the
test harness or provision a test claim in the target tenant.

Validate that the context, tenant, and referenced endpoints agree with the
logged-in environment before changing resources. Pass the selected context
to cluster commands, and keep cluster, registry, and GitHub credentials in
their existing credential stores. Store resource references only in the
profile. Keep deployment-specific profiles local to the workspace and outside
commits and PRs.
