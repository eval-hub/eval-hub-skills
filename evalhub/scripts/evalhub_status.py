#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["eval-hub-sdk[client] @ file:///home/rui/Sync/code/experiments/features/eval-service/poc/eval-hub-sdk"]
# ///
"""Get EvalHub job status, list jobs, or cancel a job."""

import argparse
import json
import os
import sys


def get_client():
    from evalhub import SyncEvalHubClient

    return SyncEvalHubClient(
        base_url=os.environ.get("EVALHUB_BASE_URL", ""),
        auth_token=os.environ.get("EVALHUB_TOKEN"),
        tenant=os.environ.get("EVALHUB_TENANT"),
        insecure=os.environ.get("EVALHUB_INSECURE", "").lower() in ("1", "true"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Get EvalHub job status")
    parser.add_argument("job_id", nargs="?", help="Job ID to check")
    parser.add_argument(
        "--wait", action="store_true", help="Poll until job reaches a terminal state"
    )
    parser.add_argument(
        "--timeout", type=float, default=600, help="Timeout in seconds for --wait (default: 600)"
    )
    parser.add_argument(
        "--interval", type=float, default=10, help="Poll interval in seconds (default: 10)"
    )
    parser.add_argument("--cancel", action="store_true", help="Cancel the job")
    parser.add_argument("--list", action="store_true", dest="list_jobs", help="List all jobs")
    parser.add_argument(
        "--status",
        help="Filter by status when listing (pending, running, completed, failed, cancelled)",
    )
    parser.add_argument("--limit", type=int, help="Max jobs to return when listing")
    args = parser.parse_args()

    client = get_client()

    if args.list_jobs:
        from evalhub import JobStatus

        status_filter = None
        if args.status:
            status_filter = JobStatus(args.status)
        jobs = client.jobs.list(status=status_filter, limit=args.limit)
        result = []
        for j in jobs:
            entry = {
                "id": j.resource.id if hasattr(j, "resource") else getattr(j, "id", None),
                "name": j.name,
                "state": j.state.value if hasattr(j.state, "value") else str(j.state),
            }
            if hasattr(j, "resource") and hasattr(j.resource, "created_at"):
                entry["created_at"] = str(j.resource.created_at)
            result.append(entry)
        print(json.dumps(result, indent=2, default=str))
        return

    if not args.job_id:
        parser.error("job_id is required (or use --list)")

    if args.cancel:
        try:
            client.jobs.cancel(args.job_id)
            print(json.dumps({"cancelled": True, "job_id": args.job_id}))
        except Exception as e:
            print(
                json.dumps({"cancelled": False, "job_id": args.job_id, "error": str(e)}),
                file=sys.stderr,
            )
            sys.exit(1)
        return

    if args.wait:
        try:
            job = client.jobs.wait_for_completion(
                args.job_id,
                timeout=args.timeout,
                poll_interval=args.interval,
            )
        except TimeoutError:
            print(
                json.dumps({"error": f"Job {args.job_id} did not complete within {args.timeout}s"}),
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        job = client.jobs.get(args.job_id)

    result = job.model_dump() if hasattr(job, "model_dump") else vars(job)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
