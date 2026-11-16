#!/usr/bin/env python3
"""Verify Registry shadow monitoring against the authoritative pinned Monitor checkout."""
from __future__ import annotations
import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from verify_dtg_replay import validate_replay


def verify_shadow(source, fetched, routing, combined, dpip, unresolved, *,
                  source_date, toolkit_revision, monitor_revision, today=None):
    problems = []
    try:
        observed = date.fromisoformat(source_date)
    except ValueError:
        return ["invalid source date"], {}
    today = today or datetime.now(timezone.utc).date()
    age = (today - observed).days
    if not 0 <= age <= 2:
        problems.append("source snapshot violates canonical two-day UTC freshness")
    if not isinstance(source, list) or not isinstance(fetched, list):
        problems.append("source and fetched snapshots must be arrays")
    elif source != fetched:
        problems.append("fetched snapshot does not match pinned Monitor commit")
    issues, output = validate_replay(
        fetched, routing, combined, dpip, unresolved,
        toolkit_revision=toolkit_revision, monitor_revision=monitor_revision,
        snapshot_date=source_date)
    problems.extend(issues)
    if problems:
        return problems, {}
    output["qualification"] = "live read-only Registry shadow monitoring; not cutover or assurance"
    output["source"]["age_days"] = age
    output["effects"]["fresh_monitor_coverage"] = True
    output["effects"]["issues_created"] = 0
    output["effects"]["target_runtime_tested"] = False
    return [], output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "fetched", "routing", "combined", "dpip", "unresolved"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("source-date", "toolkit-revision", "monitor-revision"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    inputs = [json.loads(getattr(args, name).read_text(encoding="utf-8"))
              for name in ("source", "fetched", "routing", "combined", "dpip", "unresolved")]
    errors, result = verify_shadow(*inputs, source_date=args.source_date,
                                   toolkit_revision=args.toolkit_revision,
                                   monitor_revision=args.monitor_revision)
    if errors:
        for error in errors:
            print("INVALID:", error)
        raise SystemExit(1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS read-only source-matched shadow routing; not RAHP assurance PASS")


if __name__ == "__main__":
    main()
