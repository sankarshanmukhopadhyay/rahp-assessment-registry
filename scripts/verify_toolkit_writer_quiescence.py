#!/usr/bin/env python3
"""Read-only pre-POST check for active inventoried Toolkit issue writer workflows.

A clean observation is not a cross-repository lock. The operator must separately
stop future affected dispatches and drain pre-existing, older publisher runs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import registry_intake
from audit_toolkit_issue_writers import EXTERNAL_EXPECTED

# Only workflows that actually invoke the canonical external case publisher
# can create competing Toolkit cases. DPIP lifecycle and review workers retain
# Toolkit-local, historical issue-number consumer duties; these are governed
# separately and cannot be counted as Registry first-case writers.
CURRENT_WRITERS = {
    name: spec for name, spec in EXTERNAL_EXPECTED.items()
    if spec["publisher"] > 0
}

TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
API = "https://api.github.com/repos/" + TOOLKIT
# Reuse the audited current writer inventory rather than maintaining a second
# list that can silently miss renamed live workflows. Retired workflow paths
# remain blocking because historical dispatched/in-flight runs may still exist.
HISTORICAL_WRITERS = frozenset({
    ".github/workflows/dtg-portfolio-materiality-handoff.yml",
    ".github/workflows/instance-watch.yml",
})
WRITERS = frozenset(
    {f".github/workflows/{name}" for name in CURRENT_WRITERS}
) | HISTORICAL_WRITERS
NONTERMINAL = ("queued", "in_progress", "waiting", "requested", "pending")


class QuiescenceError(ValueError):
    pass


def evaluate(fetch):
    active = []
    checked = 0
    seen_ids = set()
    for status in NONTERMINAL:
        expected_total = None
        observed = 0
        for page in range(1, 101):
            url = (API + "/actions/runs?status=" + status +
                   "&per_page=100&page=" + str(page))
            response = fetch(url)
            if (not isinstance(response, dict) or
                    not isinstance(response.get("workflow_runs"), list)):
                raise QuiescenceError("Toolkit Actions run inventory unavailable")
            total = response.get("total_count")
            if type(total) is not int or total < 0:
                raise QuiescenceError("Toolkit Actions total_count unavailable or invalid")
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise QuiescenceError("Toolkit Actions inventory changed during pagination")
            rows = response["workflow_runs"]
            if len(rows) > 100 or observed + len(rows) > expected_total:
                raise QuiescenceError("Toolkit Actions inventory page invalid")
            checked += len(rows)
            observed += len(rows)
            for run in rows:
                if not isinstance(run, dict):
                    raise QuiescenceError("invalid active-run record")
                path = run.get("path")
                run_id = run.get("id")
                if (type(run_id) is not int or run_id < 1 or
                        not isinstance(path, str) or run.get("status") != status or
                        run_id in seen_ids):
                    raise QuiescenceError("inconsistent or repeated Toolkit run identity")
                seen_ids.add(run_id)
                if path in WRITERS:
                    active.append({"id": run_id, "workflow": path, "status": status})
            if len(rows) < 100:
                if observed != expected_total:
                    raise QuiescenceError("incomplete Toolkit Actions run inventory")
                break
        else:
            raise QuiescenceError("Toolkit Actions inventory exceeds pagination bound")
    return {"schema": "rahp-toolkit-writer-quiescence/v1",
            "checked_nonterminal_runs": checked,
            "writer_workflows": sorted(WRITERS),
            "active_writer_runs": sorted(active, key=lambda x: x["id"]),
            "quiescent_at_observation": not active,
            "exclusive_lock_established": False,
            "cutover_authorized": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-quiescent", action="store_true")
    args = parser.parse_args()
    result = {"schema": "rahp-toolkit-writer-quiescence/v1",
              "quiescent_at_observation": False,
              "exclusive_lock_established": False,
              "cutover_authorized": False}
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN")
        if not token:
            raise QuiescenceError("authenticated Toolkit Actions reader unavailable")
        result = evaluate(lambda url: registry_intake.request("GET", url, token))
    except (QuiescenceError, registry_intake.IntakeError, OSError, ValueError) as exc:
        result["error"] = str(exc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not result["quiescent_at_observation"]:
        print("BLOCKED: Toolkit writer quiescence not established", file=sys.stderr)
        return 1 if args.require_quiescent else 0
    print("Toolkit writer quiescence observed; no cross-repository lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
