#!/usr/bin/env python3
"""Aggregate backend xdist canary artifacts into a recurrence report."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set
from xml.etree import ElementTree

FAILED_LINE_RE = re.compile(r"^FAILED\s+(?P<test>\S+)")
SIGNATURE_PATTERNS = [
    re.compile(r"SessionInterrupted:[^\n]*"),
    re.compile(r"INTERNALERROR[^\n]*"),
    re.compile(r"Worker .* crashed[^\n]*"),
    re.compile(r"psycopg2\.errors\.[A-Za-z_]+"),
    re.compile(r"IntegrityError:[^\n]*"),
    re.compile(r"UniqueViolation[^\n]*"),
]


@dataclass(frozen=True)
class FailureEvent:
    test_id: str
    signature: str
    source: str


@dataclass(frozen=True)
class CanaryRun:
    artifact_name: str
    workers: str
    dist: str
    exit_code: int
    duration_seconds: int
    failure_events: List[FailureEvent]
    runtime_signatures: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-dir",
        default="xdist-canary-artifacts",
        help="Directory with downloaded matrix artifacts",
    )
    parser.add_argument("--output-json", required=True, help="Path to output JSON report")
    parser.add_argument("--output-md", required=True, help="Path to output Markdown report")
    return parser.parse_args()


def normalize_signature(text: str) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    if not line:
        return "unknown-signature"
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"0x[0-9a-fA-F]+", "0x*", line)
    line = re.sub(r"\b\d+\b", "#", line)
    return line[:180]


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_junit(path: Path) -> List[FailureEvent]:
    if not path.exists():
        return []

    events: List[FailureEvent] = []
    root = ElementTree.parse(path).getroot()

    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        if classname and name:
            test_id = f"{classname}::{name}"
        else:
            test_id = name or classname or "unknown-test"

        for child in list(testcase):
            tag = child.tag.lower()
            if tag not in {"failure", "error"}:
                continue
            raw_message = child.attrib.get("message", "").strip()
            body = (child.text or "").strip()
            signature = normalize_signature(raw_message or body)
            events.append(FailureEvent(test_id=test_id, signature=signature, source="junit"))

    return events


def parse_log(path: Path) -> tuple[Set[str], Set[str]]:
    content = safe_read_text(path)
    failed_tests: Set[str] = set()
    signatures: Set[str] = set()

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        failed_match = FAILED_LINE_RE.match(line)
        if failed_match:
            failed_tests.add(failed_match.group("test"))

        for pattern in SIGNATURE_PATTERNS:
            matched = pattern.search(line)
            if matched:
                signatures.add(normalize_signature(matched.group(0)))

    return failed_tests, signatures


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def collect_runs(artifacts_dir: Path) -> List[CanaryRun]:
    if not artifacts_dir.exists():
        return []

    runs: List[CanaryRun] = []

    for artifact_path in sorted([item for item in artifacts_dir.iterdir() if item.is_dir()]):
        metadata = load_metadata(artifact_path / "xdist-canary-metadata.json")
        workers = str(metadata.get("workers", "unknown"))
        dist = str(metadata.get("dist", "unknown"))
        exit_code = int(metadata.get("exit_code", 0))
        duration_seconds = int(metadata.get("duration_seconds", 0))

        junit_events = parse_junit(artifact_path / "xdist-canary-junit.xml")
        log_failed_tests, log_signatures = parse_log(artifact_path / "xdist-canary-pytest.log")

        merged_events: Dict[str, FailureEvent] = {event.test_id: event for event in junit_events}
        for test_id in sorted(log_failed_tests):
            merged_events.setdefault(
                test_id,
                FailureEvent(
                    test_id=test_id,
                    signature="failed-from-log-without-junit-entry",
                    source="log",
                ),
            )

        runtime_signatures: Set[str] = set(log_signatures)
        for event in merged_events.values():
            runtime_signatures.add(event.signature)

        if exit_code != 0 and not runtime_signatures:
            runtime_signatures.add("non-zero-exit-without-signature")

        runs.append(
            CanaryRun(
                artifact_name=artifact_path.name,
                workers=workers,
                dist=dist,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                failure_events=sorted(merged_events.values(), key=lambda item: item.test_id),
                runtime_signatures=sorted(runtime_signatures),
            )
        )

    return runs


def build_payload(runs: List[CanaryRun]) -> dict:
    test_counter: Counter[str] = Counter()
    signature_counter: Counter[str] = Counter()
    tests_to_artifacts: Dict[str, List[str]] = defaultdict(list)
    signatures_to_artifacts: Dict[str, List[str]] = defaultdict(list)

    matrix_rows: List[dict] = []
    failed_runs = 0

    for run in runs:
        run_tests = sorted({event.test_id for event in run.failure_events})
        run_signatures = sorted(set(run.runtime_signatures))
        has_failure = run.exit_code != 0 or bool(run_tests)

        if has_failure:
            failed_runs += 1

        for test_id in run_tests:
            test_counter[test_id] += 1
            tests_to_artifacts[test_id].append(run.artifact_name)

        for signature in run_signatures:
            signature_counter[signature] += 1
            signatures_to_artifacts[signature].append(run.artifact_name)

        matrix_rows.append(
            {
                "artifact_name": run.artifact_name,
                "workers": run.workers,
                "dist": run.dist,
                "exit_code": run.exit_code,
                "duration_seconds": run.duration_seconds,
                "status": "failed" if has_failure else "passed",
                "failed_tests_count": len(run_tests),
                "failure_signatures_count": len(run_signatures),
                "failed_tests": run_tests,
                "failure_signatures": run_signatures,
            }
        )

    recurrent_tests = [
        {
            "test_id": test_id,
            "count": count,
            "artifacts": sorted(tests_to_artifacts[test_id]),
        }
        for test_id, count in test_counter.most_common()
    ]

    recurrent_signatures = [
        {
            "signature": signature,
            "count": count,
            "artifacts": sorted(signatures_to_artifacts[signature]),
        }
        for signature, count in signature_counter.most_common()
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_total": len(runs),
        "runs_with_failures": failed_runs,
        "runs_without_failures": max(0, len(runs) - failed_runs),
        "matrix_results": matrix_rows,
        "recurrent_failed_tests": recurrent_tests,
        "recurrent_failure_signatures": recurrent_signatures,
    }


def write_json(path: Path, payload: dict) -> None:
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict) -> None:
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# Backend xdist Canary Report")
    lines.append("")
    lines.append("Non-blocking canary: this workflow is informational and never a required PR gate.")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{payload['generated_at_utc']}`")
    lines.append(f"- Matrix runs: `{payload['runs_total']}`")
    lines.append(f"- Runs with failures: `{payload['runs_with_failures']}`")
    lines.append(f"- Runs without failures: `{payload['runs_without_failures']}`")
    lines.append("")

    lines.append("## Matrix results")
    lines.append("")
    lines.append("| Artifact | Workers | Dist | Exit | Status | Failed tests | Signatures | Duration (s) |")
    lines.append("|---|---:|---|---:|---|---:|---:|---:|")

    for row in payload["matrix_results"]:
        lines.append(
            f"| {row['artifact_name']} | {row['workers']} | {row['dist']} | {row['exit_code']} | "
            f"{row['status']} | {row['failed_tests_count']} | {row['failure_signatures_count']} | "
            f"{row['duration_seconds']} |"
        )

    recurrent_tests = payload["recurrent_failed_tests"]
    lines.append("")
    lines.append("## Recurrent failed tests")
    lines.append("")
    if recurrent_tests:
        for item in recurrent_tests[:20]:
            lines.append(
                f"- `{item['test_id']}`: {item['count']} run(s) "
                f"({', '.join(item['artifacts'])})"
            )
    else:
        lines.append("- No failed tests detected.")

    recurrent_signatures = payload["recurrent_failure_signatures"]
    lines.append("")
    lines.append("## Failure signatures")
    lines.append("")
    if recurrent_signatures:
        for item in recurrent_signatures[:20]:
            lines.append(
                f"- `{item['signature']}`: {item['count']} run(s) "
                f"({', '.join(item['artifacts'])})"
            )
    else:
        lines.append("- No failure signatures detected.")

    lines.append("")
    lines.append("## Triage rule")
    lines.append("")
    lines.append("- Any test/signature recurring in 2+ runs should have a linked stabilization issue.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    runs = collect_runs(artifacts_dir)
    payload = build_payload(runs)

    write_json(output_json, payload)
    write_markdown(output_md, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
