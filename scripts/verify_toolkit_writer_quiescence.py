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

TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
API = "https://api.github.com/repos/" + TOOLKIT
WRITERS = frozenset({
    ".github/workflows/cross-spec-pressure-test.yml",
    ".github/workflows/distributed-resilience-assessment.yml",
    ".github/workflows/dpip-lifecycle.yml",
    ".github/workflows/dtg-portfolio-materiality-handoff.yml",
    ".github/workflows/instance-watch.yml",
    ".github/workflows/review-workers.yml",
})
NONTERMINAL = ("queued", "in_progress", "waiting", "requested", "pending")


class QuiescenceError(ValueError):
    pass


def evaluate(fetch):
    active = []
    checked = 0
    for status in NONTERMINAL:
        for page in range(1, 101):
            url = (API + "/actions/runs?status=" + status +
                   "&per_page=100&page=" + str(page))
            response = fetch(url)
            if (not isinstance(response, dict) or
                    not isinstance(response.get("workflow_runs"), list)):
                raise QuiescenceError("Toolkit Actions run inventory unavailable")
            rows = response["workflow_runs"]
            if len(rows) > 100:
                raise QuiescenceError("Toolkit Actions inventory page invalid")
            checked += len(rows)
            for run in rows:
                if not isinstance(run, dict):
                    raise QuiescenceError("invalid active-run record")
                path = run.get("path")
                if path in WRITERS:
                    if run.get("status") != status or not isinstance(run.get("id"), int):
                        raise QuiescenceError("inconsistent active Toolkit writer identity")
                    active.append({"id": run["id"], "workflow": path, "status": status})
            if len(rows) < 100:
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
