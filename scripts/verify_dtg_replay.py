#!/usr/bin/env python3
"""Verify the integrity and scope of source-pinned DTG routing replay outputs."""
import argparse
import hashlib
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_replay(findings, routed, combined, dpip, unresolved, *, toolkit_revision,
                    monitor_revision, snapshot_date):
    failures = []
    if not SHA.fullmatch(toolkit_revision) or not SHA.fullmatch(monitor_revision):
        failures.append("toolkit and monitor must be pinned to immutable commit IDs")
    if not DAY.fullmatch(snapshot_date):
        failures.append("invalid snapshot date")
    for name, records in (("findings", findings), ("routing", routed),
                          ("combined", combined), ("dpip", dpip), ("unresolved", unresolved)):
        if not isinstance(records, list):
            failures.append(f"{name}: expected JSON array")
    if failures:
        return failures, {}
    ids = {x.get("finding_id") for x in findings if isinstance(x, dict)}
    if not ids:
        failures.append("empty snapshot is not proof of routing parity")
    if None in ids:
        failures.append("source snapshot includes missing finding ID")
    if len(ids) != len(findings):
        failures.append("source finding IDs are duplicated")
    for item in routed:
        if not isinstance(item, dict) or not isinstance(item.get("finding"), dict):
            failures.append("routing item missing source finding")
            continue
        if item["finding"].get("finding_id") not in ids:
            failures.append("routing item does not originate in pinned source")
        if not isinstance(item.get("outcome"), str) or not item["outcome"]:
            failures.append("routing outcome missing")
    for group, items in (("combined", combined), ("dpip", dpip)):
        for item in items:
            if not isinstance(item, dict) or not item.get("assessment_key") or not item.get("body"):
                failures.append(f"{group}: generated event missing body or key")
    for item in unresolved:
        if not isinstance(item, dict) or item.get("finding_id") not in ids:
            failures.append("unresolved finding not in pinned source")
    canonical = json.dumps(findings, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    summary = {
        "schema": "rahp-registry-dtg-replay-evidence/v1",
        "source": {
            "repository": "sankarshanmukhopadhyay/dtg-portfolio-monitor",
            "revision": monitor_revision,
            "snapshot_date": snapshot_date,
            "digest_sha256": hashlib.sha256(canonical).hexdigest(),
        },
        "engine": {
            "repository": "sankarshanmukhopadhyay/rahp-toolkit",
            "revision": toolkit_revision,
            "role": "canonical pinned routing implementation",
        },
        "counts": {
            "source_findings": len(findings),
            "routed": len(routed),
            "combined": len(combined),
            "dpip": len(dpip),
            "unresolved": len(unresolved),
        },
        "effects": {
            "issues_created": 0,
            "assurance_determination": "not_assessed",
            "target_runtime_tested": False,
            "fresh_monitor_coverage": False,
        },
        "qualification": "historical pinned replay, not production cutover or assurance PASS",
    }
    return failures, summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for label in ("findings", "routing", "combined", "dpip", "unresolved"):
        p.add_argument("--" + label, required=True, type=Path)
    p.add_argument("--monitor-revision", required=True)
    p.add_argument("--toolkit-revision", required=True)
    p.add_argument("--snapshot-date", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    inputs = [json.loads(getattr(args, k).read_text(encoding="utf-8"))
              for k in ("findings", "routing", "combined", "dpip", "unresolved")]
    errors, report = validate_replay(
        *inputs, toolkit_revision=args.toolkit_revision,
        monitor_revision=args.monitor_revision, snapshot_date=args.snapshot_date)
    if errors:
        for error in errors:
            print("INVALID:", error)
        raise SystemExit(1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS source-pinned historical DTG routing replay structural checks (not assurance PASS)")


if __name__ == "__main__":
    main()
