#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""Create an EvalHub evaluation job."""

import argparse
import json
import os


def get_client():
    from evalhub import SyncEvalHubClient

    return SyncEvalHubClient(
        base_url=os.environ.get("EVALHUB_BASE_URL", ""),
        auth_token=os.environ.get("EVALHUB_TOKEN"),
        tenant=os.environ.get("EVALHUB_TENANT"),
        insecure=os.environ.get("EVALHUB_INSECURE", "").lower() in ("1", "true"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an EvalHub evaluation job")
    parser.add_argument(
        "--json", dest="json_file", help="Submit a pre-built JSON request body from file"
    )
    parser.add_argument("--model-url", help="Model inference endpoint URL")
    parser.add_argument("--model-name", help="Model name")
    parser.add_argument("--model-secret", help="Kubernetes secret name for model auth")
    parser.add_argument("--provider", help="Provider ID (discover with evalhub_providers.py)")
    parser.add_argument(
        "--benchmark", action="append", dest="benchmarks", help="Benchmark ID (repeatable)"
    )
    parser.add_argument("--collection", help="Collection ID (alternative to --benchmark)")
    parser.add_argument("--name", help="Job name (auto-generated if omitted)")
    parser.add_argument("--description", help="Job description")
    parser.add_argument("--tag", action="append", dest="tags", help="Tag (repeatable)")
    parser.add_argument(
        "--num-examples", type=int, help="Limit benchmark to N examples (for quick iteration)"
    )
    parser.add_argument("--threshold", type=float, help="Pass/fail threshold (0.0-1.0)")
    parser.add_argument("--experiment-name", help="MLflow experiment name")
    parser.add_argument("--queue", help="Kueue queue name for job scheduling")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print request JSON without submitting"
    )
    args = parser.parse_args()

    client = get_client() if not args.dry_run else None

    if args.json_file:
        with open(args.json_file) as f:
            request_data = json.load(f)
        from evalhub import JobSubmissionRequest

        request = JobSubmissionRequest(**request_data)
    else:
        if not args.model_url or not args.model_name:
            parser.error("--model-url and --model-name are required (unless using --json)")
        if not args.benchmarks and not args.collection:
            parser.error("At least one --benchmark or --collection is required")

        from evalhub import JobSubmissionRequest, ModelConfig, BenchmarkConfig, CollectionRef

        model_auth = None
        if args.model_secret:
            from evalhub.models.api import ModelAuth

            model_auth = ModelAuth(secret_ref=args.model_secret)

        model = ModelConfig(url=args.model_url, name=args.model_name, auth=model_auth)

        benchmarks = None
        collection = None

        if args.benchmarks:
            if not args.provider:
                parser.error("--provider is required when using --benchmark")
            benchmarks = []
            for bench_id in args.benchmarks:
                config = BenchmarkConfig(id=bench_id, provider_id=args.provider)
                if args.num_examples:
                    config.parameters = {"num_examples": args.num_examples}
                if args.threshold is not None:
                    from evalhub.models.api import PassCriteria

                    config.pass_criteria = PassCriteria(threshold=args.threshold)
                benchmarks.append(config)

        if args.collection:
            collection = CollectionRef(id=args.collection)

        job_name = args.name or f"eval-{args.model_name}"

        experiment = None
        if args.experiment_name:
            from evalhub import ExperimentConfig

            experiment = ExperimentConfig(name=args.experiment_name)

        pass_criteria = None
        if args.threshold is not None and not args.benchmarks:
            from evalhub.models.api import PassCriteria

            pass_criteria = PassCriteria(threshold=args.threshold)

        queue = None
        if args.queue:
            from evalhub.models.api import QueueConfig

            queue = QueueConfig(name=args.queue)

        request = JobSubmissionRequest(
            name=job_name,
            description=args.description,
            model=model,
            benchmarks=benchmarks,
            collection=collection,
            tags=args.tags,
            experiment=experiment,
            pass_criteria=pass_criteria,
            queue=queue,
        )

    if args.dry_run:
        data = request.model_dump() if hasattr(request, "model_dump") else vars(request)
        print(json.dumps(data, indent=2, default=str))
        return

    job = client.jobs.submit(request)  # type: ignore[union-attr]
    result = job.model_dump() if hasattr(job, "model_dump") else vars(job)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
