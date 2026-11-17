#!/usr/bin/env python3
"""Audit all current Toolkit workflow issue-write authorities before Registry cutover.

This is a conservative, read-only *inventory* of publication and issue-number
consumers, not a declaration that a successful scan authorizes migration.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED = {
    "cross-spec-pressure-test.yml": {"publisher": 1, "incident": 0, "consumer": []},
    "distributed-resilience-assessment.yml": {"publisher": 1, "incident": 0, "consumer": []},
    "dpip-lifecycle.yml": {
        "publisher": 0, "incident": 0,
        "consumer": ["tools/dpip_handoff.py", "tools/dpip_return_reconcile.py",
                     "tools/dpip_lifecycle_reconcile.py", "tools/evidence_provenance_router.py"],
    },
    "dtg-portfolio-materiality-handoff.yml": {
        "publisher": 3, "incident": 0, "consumer": ["tools/dpip_handoff.py"],
    },
    "instance-watch.yml": {
        "publisher": 4, "incident": 1, "consumer": ["tools/dtg_repository_review_worker.py"],
    },
    "review-workers.yml": {
        "publisher": 0, "incident": 0,
        "consumer": ["tools/combined_review_worker.py", "tools/dtg_repository_review_worker.py"],
    },
}
PUBLISHER = "tools/publish_assessment_issues.py"
INCIDENT = "tools/publish_dtg_controller_incidents.py"
ISSUE_WRITE = re.compile(r"(?m)^\s*issues:\s*write\s*(?:#.*)?$")
UNCONTROLLED = re.compile(
    r"\bgh\s+issue\s+(?:create|edit|close|reopen|comment)\b|"
    r"api[.]github[.]com/repos/[^ \n]+/issues|"
    r"\bgithub[.]rest[.]issues[.](?:create|update|createComment)\b"
)


def count_effectful_invocations(body: str, script: str) -> int:
    """Count entrypoint commands; multi-line preflights never write GitHub issues.

    Match the actual command's continuation lines so an unrelated later
    --check-transfers flag cannot suppress a real publisher invocation.
    """
    lines = body.splitlines()
    count = 0
    for index, line in enumerate(lines):
        if script not in line:
            continue
        command = line.strip()
        next_index = index
        # In a YAML folded block ('run: >-'), successive equally-indented
        # lines are one shell command even without an explicit backslash.
        previous = next((item.strip() for item in reversed(lines[:index])
                         if item.strip()), "")
        folded = previous in ("run: >-", "run: >", "run: >+")
        indentation = len(line) - len(line.lstrip())
        while next_index + 1 < len(lines):
            continued = command.rstrip().endswith(chr(92))
            following = lines[next_index + 1]
            follow_indent = len(following) - len(following.lstrip())
            if not continued and not (folded and following.strip()
                                      and follow_indent >= indentation):
                break
            next_index += 1
            command = command.rstrip().removesuffix(chr(92)) + " " + following.strip()
        if "--self-test" in command:
            continue
        if script == PUBLISHER and "--check-transfers" in command:
            continue
        count += 1
    return count


def audit(workflow_directory: Path, toolkit_revision: str):
    if not re.fullmatch(r"[0-9a-f]{40}", toolkit_revision):
        raise ValueError("Toolkit revision must be a pinned 40-character commit")
    if not workflow_directory.is_dir():
        raise ValueError("actual Toolkit workflow directory required")
    workflows = list(workflow_directory.glob("*.yml")) + list(
        workflow_directory.glob("*.yaml"))
    if not workflows:
        raise ValueError("Toolkit workflow inventory is empty")
    findings, problems = [], []
    seen = set()
    for path in sorted(workflows):
        if not path.is_file() or path.is_symlink():
            raise ValueError("unexpected Toolkit workflow path")
        body = path.read_text(encoding="utf-8")
        name = path.name
        if name in seen:
            raise ValueError("duplicate workflow name")
        seen.add(name)
        # Self-tests and --check-transfers are read-only even when written
        # as multi-line commands; count only effectful publication call sites.
        count_pub = count_effectful_invocations(body, PUBLISHER)
        count_inc = count_effectful_invocations(body, INCIDENT)
        has_write = bool(ISSUE_WRITE.search(body))
        uncontrolled = bool(UNCONTROLLED.search(body))
        spec = EXPECTED.get(name)
        if uncontrolled:
            problems.append(f"{name}: unclassified direct issue API writer")
        if spec is None:
            if has_write or count_pub or count_inc:
                problems.append(f"{name}: unknown issue-write workflow")
            continue
        expected_consumers = spec["consumer"]
        missing = [item for item in expected_consumers if item not in body]
        if not has_write:
            problems.append(f"{name}: expected issue write permission missing")
        if count_pub != spec["publisher"] or count_inc != spec["incident"]:
            problems.append(f"{name}: issue publisher call-site drift")
        if missing:
            problems.append(f"{name}: issue-number or specialist consumer drift")
        findings.append({
            "workflow": name,
            "issues_write_permission": has_write,
            "publisher_calls": count_pub,
            "incident_publisher_calls": count_inc,
            "downstream_issue_consumers": expected_consumers,
            "migration_disposition": "needs_explicit_authority_transfer",
            "source_authority": "toolkit_main",
        })
    for name in EXPECTED:
        if name not in seen:
            problems.append(f"{name}: expected workflow absent")
    # A clean inventory means discovery matches this baseline. It does NOT
    # mean Toolkit has stopped external issue publication or that Registry can.
    report = {
        "schema": "rahp-toolkit-issue-producer-inventory/v1",
        "toolkit_revision": toolkit_revision,
        "workflow_count": len(workflows),
        "known_operational_issue_workflows": sorted(EXPECTED),
        "producer_call_count": sum(v["publisher_calls"] for v in findings),
        "incident_call_count": sum(v["incident_publisher_calls"] for v in findings),
        "workflows": findings,
        "inventory_drift": problems,
        "inventory_complete": not problems,
        "toolkit_development_only": False,
        "registry_issue_publication_authorized": False,
        "specialist_return_migrated": False,
        "cutover_authorized": False,
    }
    return problems, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit-workflows", type=Path, required=True)
    parser.add_argument("--toolkit-revision", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    errors, receipt = audit(args.toolkit_workflows, args.toolkit_revision)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    for error in errors:
        print("INVENTORY DRIFT:", error)
    if errors:
        return 1
    print("PASS Toolkit publication authority inventory; external publication remains active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
