#!/usr/bin/env python3
"""Generate CI runtime telemetry (median/p95) from GitHub Actions history."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://api.github.com"
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 5
MAX_BACKOFF_SECONDS = 30.0


@dataclass(frozen=True)
class JobSample:
    workflow_name: str
    job_name: str
    duration_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--workflows",
        nargs="+",
        required=True,
        help="Exact workflow names to monitor",
    )
    parser.add_argument(
        "--runs-per-workflow",
        type=int,
        default=30,
        help="Completed runs to inspect per workflow",
    )
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Only include jobs with name starting with [required]",
    )
    parser.add_argument(
        "--baseline-json",
        default="",
        help="Optional baseline json for regression detection",
    )
    parser.add_argument(
        "--regression-threshold-pct",
        type=float,
        default=35.0,
        help="Fail when p95 exceeds baseline by this percentage",
    )
    parser.add_argument(
        "--regression-min-absolute-seconds",
        type=float,
        default=20.0,
        help="Only fail if p95 regression also exceeds this absolute delta in seconds",
    )
    parser.add_argument("--output-json", required=True, help="Path to output json report")
    parser.add_argument("--output-md", required=True, help="Path to output markdown report")
    return parser.parse_args()


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _compute_retry_delay(attempt: int, retry_after_header: str | None = None) -> float:
    retry_after = _parse_retry_after(retry_after_header)
    if retry_after is not None:
        return min(retry_after, MAX_BACKOFF_SECONDS)
    base = min(float(2**attempt), MAX_BACKOFF_SECONDS)
    # Small jitter to avoid synchronized retries across runners.
    return base + random.uniform(0.0, 0.5)


def github_get(path: str, token: str, params: Dict[str, str] | None = None) -> dict:
    query = f"?{urlencode(params)}" if params else ""
    req = Request(f"{API_BASE}{path}{query}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    max_retries_raw = os.getenv("GITHUB_API_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))
    try:
        max_retries = max(1, int(max_retries_raw))
    except ValueError:
        max_retries = DEFAULT_MAX_RETRIES

    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            should_retry = exc.code in RETRYABLE_HTTP_CODES and attempt < (max_retries - 1)
            if not should_retry:
                raise
            delay = _compute_retry_delay(attempt, exc.headers.get("Retry-After"))
            print(
                (
                    f"[warn] github_get retryable HTTP {exc.code} "
                    f"for {path}{query} (attempt {attempt + 1}/{max_retries - 1}, "
                    f"sleep={delay:.2f}s)"
                ),
                file=sys.stderr,
            )
            time.sleep(delay)
        except URLError as exc:
            if attempt >= (max_retries - 1):
                raise
            delay = _compute_retry_delay(attempt)
            print(
                (
                    f"[warn] github_get network error for {path}{query}: {exc.reason} "
                    f"(attempt {attempt + 1}/{max_retries - 1}, sleep={delay:.2f}s)"
                ),
                file=sys.stderr,
            )
            time.sleep(delay)

    raise RuntimeError("github_get exhausted retries unexpectedly")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def percentile(values: Iterable[float], p: float) -> float:
    data = sorted(values)
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    rank = math.ceil((p / 100.0) * len(data)) - 1
    rank = max(0, min(rank, len(data) - 1))
    return data[rank]


def fetch_workflow_id(repo: str, workflow_name: str, token: str) -> int:
    page = 1
    while True:
        payload = github_get(
            f"/repos/{repo}/actions/workflows",
            token,
            params={"per_page": "100", "page": str(page)},
        )
        workflows = payload.get("workflows", [])
        if not workflows:
            break
        for workflow in workflows:
            if workflow.get("name") == workflow_name:
                return int(workflow["id"])
        page += 1
    raise RuntimeError(f"Workflow not found: {workflow_name}")


def fetch_completed_runs(repo: str, workflow_id: int, token: str, limit: int) -> List[dict]:
    runs: List[dict] = []
    page = 1
    while len(runs) < limit:
        payload = github_get(
            f"/repos/{repo}/actions/workflows/{workflow_id}/runs",
            token,
            params={
                "status": "completed",
                "per_page": "100",
                "page": str(page),
            },
        )
        page_runs = payload.get("workflow_runs", [])
        if not page_runs:
            break
        runs.extend(page_runs)
        page += 1
    return runs[:limit]


def fetch_run_jobs(repo: str, run_id: int, token: str) -> List[dict]:
    jobs: List[dict] = []
    page = 1
    while True:
        payload = github_get(
            f"/repos/{repo}/actions/runs/{run_id}/jobs",
            token,
            params={"per_page": "100", "page": str(page)},
        )
        page_jobs = payload.get("jobs", [])
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        if len(page_jobs) < 100:
            break
        page += 1
    return jobs


def collect_samples(
    repo: str,
    workflows: List[str],
    token: str,
    runs_per_workflow: int,
    required_only: bool,
) -> List[JobSample]:
    samples: List[JobSample] = []
    for workflow_name in workflows:
        workflow_id = fetch_workflow_id(repo, workflow_name, token)
        runs = fetch_completed_runs(repo, workflow_id, token, runs_per_workflow)
        for run in runs:
            run_id = int(run["id"])
            jobs = fetch_run_jobs(repo, run_id, token)
            for job in jobs:
                job_name = job.get("name", "")
                if required_only and not job_name.startswith("[required]"):
                    continue
                started_at = job.get("started_at")
                completed_at = job.get("completed_at")
                if not started_at or not completed_at:
                    continue
                duration = (parse_ts(completed_at) - parse_ts(started_at)).total_seconds()
                if duration < 0:
                    continue
                samples.append(
                    JobSample(
                        workflow_name=workflow_name,
                        job_name=job_name,
                        duration_seconds=duration,
                    )
                )
    return samples


def build_metrics(samples: List[JobSample]) -> Dict[str, dict]:
    by_key: Dict[str, List[float]] = {}
    for sample in samples:
        key = f"{sample.workflow_name}::{sample.job_name}"
        by_key.setdefault(key, []).append(sample.duration_seconds)

    metrics: Dict[str, dict] = {}
    for key, values in by_key.items():
        values_sorted = sorted(values)
        metrics[key] = {
            "samples": len(values_sorted),
            "median_seconds": round(float(statistics.median(values_sorted)), 2),
            "p95_seconds": round(float(percentile(values_sorted, 95.0)), 2),
            "min_seconds": round(float(values_sorted[0]), 2),
            "max_seconds": round(float(values_sorted[-1]), 2),
        }
    return metrics


def load_baseline(path: str) -> Dict[str, dict]:
    if not path:
        return {}
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("metrics", {})


def detect_regressions(
    metrics: Dict[str, dict],
    baseline_metrics: Dict[str, dict],
    threshold_pct: float,
    min_absolute_seconds: float,
) -> List[Tuple[str, float, float]]:
    regressions: List[Tuple[str, float, float]] = []
    factor = 1.0 + (threshold_pct / 100.0)
    for key, current in metrics.items():
        baseline = baseline_metrics.get(key)
        if not baseline:
            continue
        baseline_p95 = float(baseline.get("p95_seconds", 0.0))
        current_p95 = float(current.get("p95_seconds", 0.0))
        if baseline_p95 <= 0.0:
            continue
        absolute_delta = current_p95 - baseline_p95
        if current_p95 > baseline_p95 * factor and absolute_delta >= min_absolute_seconds:
            regressions.append((key, baseline_p95, current_p95))
    return regressions


def write_json(path: str, payload: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def write_markdown(path: str, payload: dict, regressions: List[Tuple[str, float, float]]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    lines: List[str] = []
    lines.append("# CI Runtime Telemetry")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{payload['generated_at_utc']}`")
    lines.append(f"- Repo: `{payload['repo']}`")
    lines.append(f"- Workflows: `{', '.join(payload['workflows'])}`")
    lines.append(f"- Runs per workflow: `{payload['runs_per_workflow']}`")
    lines.append(f"- Regression threshold (p95): `+{payload['regression_threshold_pct']}%`")
    lines.append(
        f"- Regression minimum absolute delta: `+{payload['regression_min_absolute_seconds']}s`"
    )
    lines.append("")
    lines.append("| Workflow | Job | Samples | Median (s) | P95 (s) | Min (s) | Max (s) |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    for key in sorted(payload["metrics"].keys()):
        workflow_name, job_name = key.split("::", 1)
        metric = payload["metrics"][key]
        lines.append(
            f"| {workflow_name} | {job_name} | {metric['samples']} | "
            f"{metric['median_seconds']} | {metric['p95_seconds']} | "
            f"{metric['min_seconds']} | {metric['max_seconds']} |"
        )

    lines.append("")
    lines.append("## Regression Check")
    if not regressions:
        lines.append("")
        lines.append("- No p95 regressions detected against baseline threshold.")
    else:
        lines.append("")
        lines.append("- Regressions detected:")
        for key, baseline_p95, current_p95 in regressions:
            workflow_name, job_name = key.split("::", 1)
            lines.append(
                f"  - `{workflow_name} / {job_name}`: baseline p95={baseline_p95}s, current p95={current_p95}s"
            )
    lines.append("")

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    samples = collect_samples(
        repo=args.repo,
        workflows=args.workflows,
        token=token,
        runs_per_workflow=args.runs_per_workflow,
        required_only=args.required_only,
    )
    metrics = build_metrics(samples)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo": args.repo,
        "workflows": args.workflows,
        "runs_per_workflow": args.runs_per_workflow,
        "regression_threshold_pct": args.regression_threshold_pct,
        "regression_min_absolute_seconds": args.regression_min_absolute_seconds,
        "metrics": metrics,
    }

    baseline_metrics = load_baseline(args.baseline_json)
    regressions = detect_regressions(
        metrics=metrics,
        baseline_metrics=baseline_metrics,
        threshold_pct=args.regression_threshold_pct,
        min_absolute_seconds=args.regression_min_absolute_seconds,
    )

    write_json(args.output_json, payload)
    write_markdown(args.output_md, payload, regressions)

    print(f"Metrics keys: {len(metrics)}")
    print(f"Regressions: {len(regressions)}")
    if regressions:
        print("p95 regression threshold exceeded for at least one monitored job", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
