#!/usr/bin/env python3
"""Read-only canonical Toolkit consumer-eligibility preflight for group #272.

This preflight deliberately does not turn an administrative Registry case into
a Toolkit execution, and does not run effectful combined/DPIP workers.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import registry_intake as intake

TK = "sankarshanmukhopadhyay/rahp-toolkit"
REVISION = "35035303c830c68e7cb759195fb223b0ff9e4255"
API = "https://api.github.com/repos/" + TK + "/issues/"
PREFIX = "https://github.com/" + TK + "/issues/"
GROUP = "dtg:portfolio:combined:spec-dependency-alignment"
MARKER = "<!-- rahp-assessment-key:" + GROUP + " -->"
NUMBERS = (272, 615, 282, 826, 837)


class ConsumerGateError(ValueError):
    pass


def canonical_consumers(toolkit: Path):
    tools = toolkit / "tools"
    if not all((tools / (name + ".py")).is_file()
               for name in ("combined_review_worker", "dpip_handoff",
                            "dpip_return_reconcile")):
        raise ConsumerGateError("pinned canonical Toolkit consumer files unavailable")
    try:
        actual = subprocess.check_output(
            ["git", "-C", str(toolkit), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConsumerGateError("Toolkit consumer revision unavailable") from exc
    if actual != REVISION:
        raise ConsumerGateError("canonical Toolkit consumer revision is not pinned")
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return (importlib.import_module("combined_review_worker"),
            importlib.import_module("dpip_handoff"))


def evaluate(intent, issues, combined, dpip):
    """Exercise actual eligibility selectors, never their effectful run() paths."""
    if not isinstance(intent, dict) or intent.get("assessment_key") != GROUP:
        raise ConsumerGateError("source intent does not bind the reviewed group")
    if (intent.get("toolkit_current_issue_url") != PREFIX + "272"
            or intent.get("toolkit_historical_issue_url") != PREFIX + "615"
            or intent.get("protected_issue_urls") != [
                PREFIX + str(n) for n in (282, 826, 837)]):
        raise ConsumerGateError("source intent changed Toolkit issue namespaces")
    ids = intent.get("source_finding_ids")
    if (not isinstance(ids, list) or len(ids) != 4 or
            ids != sorted(set(ids)) or
            not all(isinstance(i, str) and re.fullmatch(r"[0-9a-f]{20}", i)
                    for i in ids) or
            not re.fullmatch(r"[0-9a-f]{64}",
                             str(intent.get("source_group_sha256", "")))):
        raise ConsumerGateError("canonical group membership/digest invalid")
    if set(issues) != set(NUMBERS):
        raise ConsumerGateError("Toolkit consumer issue inventory incomplete")
    for number in NUMBERS:
        issue = issues[number]
        if (not isinstance(issue, dict) or type(issue.get("number")) is not int
                or issue["number"] != number
                or issue.get("html_url") != PREFIX + str(number)
                or issue.get("state") not in ("open", "closed")
                or "pull_request" in issue
                or not isinstance(issue.get("labels"), list)):
            raise ConsumerGateError("invalid live Toolkit issue namespace or state")
    current, historical = issues[272], issues[615]
    if (current["state"] != "open" or historical["state"] != "closed"
            or MARKER not in (current.get("body") or "")
            or MARKER not in (historical.get("body") or "")
            or any(fid not in (current.get("body") or "") for fid in ids)):
        raise ConsumerGateError("historical/current Toolkit group identity no longer matches")
    combined_eligible = combined.is_combined(current)
    dpip_eligible = (dpip.issue_has_label(current, dpip.REQUESTED)
                     and not dpip.issue_has_label(current, dpip.COMPLETE))
    labels = combined.label_names(current)
    # A combined-review/DPIP task could still be legitimate internal Toolkit
    # execution; it cannot become Registry authority by number substitution.
    return {
        "schema": "rahp-registry-group-consumer-gate/v1",
        "state": "consumer_migration_blocked",
        "toolkit_consumer_revision": REVISION,
        "source_group_sha256": intent["source_group_sha256"],
        "source_toolkit_issue": PREFIX + "272",
        "historical_toolkit_issue": PREFIX + "615",
        "protected_toolkit_issues": [PREFIX + str(n) for n in (282, 826, 837)],
        "combined_review_worker_eligible": bool(combined_eligible),
        "dpip_handoff_eligible": bool(dpip_eligible),
        "dpip_lifecycle_issue_eligible": bool(
            labels & {"assurance:dpip-open", "assurance:dpip-complete"}),
        "registry_case_execution_adapter_qualified": False,
        "registry_to_toolkit_issue_number_dispatch_authorized": False,
        "specialist_return_controller_reconciled": False,
        "cutover_authorized": False,
        "assurance_determination": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--toolkit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-migrated", action="store_true",
                        help="block effectful Registry successor publication until a real consumer adapter is accepted")
    args = parser.parse_args()
    receipt = {"schema": "rahp-registry-group-consumer-gate/v1",
               "state": "indeterminate", "cutover_authorized": False}
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN")
        if not token:
            raise ConsumerGateError("authenticated Toolkit issue reader unavailable")
        combined, dpip = canonical_consumers(args.toolkit.resolve())
        intent = json.loads(args.manifest.read_text(encoding="utf-8"))
        issues = {number: intake.request("GET", API + str(number), token)
                  for number in NUMBERS}
        receipt = evaluate(intent, issues, combined, dpip)
    except (OSError, TypeError, ValueError, KeyError, ImportError,
            intake.IntakeError) as exc:
        receipt["error"] = str(exc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    if receipt["state"] == "indeterminate":
        print("BLOCKED: canonical Toolkit consumer evidence unavailable",
              file=sys.stderr)
        return 1
    if args.require_migrated and not receipt["registry_case_execution_adapter_qualified"]:
        print("BLOCKED: no accepted Registry-to-Toolkit controller/reviewer/DPIP consumer adapter",
              file=sys.stderr)
        return 1
    print("Observed canonical Toolkit consumer eligibility; no dispatch or cutover")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
