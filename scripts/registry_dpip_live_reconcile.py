#!/usr/bin/env python3
"""Read-only live Registry-targeted DPIP return against canonical Toolkit consumer.

The Registry case must already admit the exact specialist issue. A valid
result remains an observation, not a controller decision or assurance PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import registry_intake as gh
import registry_epoch_journal as journal
import registry_specialist_return as specialist
from verify_dpip_legacy_consumer import TOOLKIT_REV

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/"
CASE_PATH = re.compile(r"cases/[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*[.]json")


class LiveDPIPError(ValueError):
    pass


def read_case(path: str):
    if not isinstance(path, str) or not CASE_PATH.fullmatch(path):
        raise LiveDPIPError("source-controlled canonical case path required")
    source = ROOT / path
    if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT / "cases"):
        raise LiveDPIPError("case file is unavailable or outside Registry cases")
    return json.loads(source.read_text(encoding="utf-8"))


def comments(repo, issue_number, fetch):
    result = []
    for page in range(1, 101):
        rows = fetch(f"{API}{repo}/issues/{issue_number}/comments?per_page=100&page={page}")
        if not isinstance(rows, list):
            raise LiveDPIPError("case/DPIP comment history is not complete")
        result.extend(rows)
        if len(rows) < 100:
            return result
    raise LiveDPIPError("case/DPIP comment history exceeds upper bound")


def verify_live(case, dpip_number, consumer, assessor_contract, *, fetch):
    if type(dpip_number) is not int or dpip_number <= 0:
        raise LiveDPIPError("positive DPIP issue number required")
    # No network fetch can turn a proposed or absent source referral into authority.
    specialist.admitted_referral(case, {"number": dpip_number})
    owner_url = (case.get("owners") or {}).get("current_active_issue")
    prefix = f"https://github.com/{specialist.REGISTRY}/issues/"
    if not isinstance(owner_url, str) or not re.fullmatch(
            re.escape(prefix) + r"[1-9][0-9]*", owner_url):
        raise LiveDPIPError("case has no exact Registry owner")
    owner_number = int(owner_url.removeprefix(prefix))
    registry_issue = fetch(f"{API}{specialist.REGISTRY}/issues/{owner_number}")
    dpip_issue = fetch(f"{API}{specialist.DPIP_REPO}/issues/{dpip_number}")
    source_comments = comments(specialist.REGISTRY, owner_number, fetch)
    target_comments = comments(specialist.DPIP_REPO, dpip_number, fetch)
    observations = journal.from_offered_runs(
        case, registry_issue, source_comments,
        [(dpip_issue, target_comments)], consumer, assessor_contract)
    if len(observations) != 1:
        raise LiveDPIPError("exactly one canonical epoch observation required")
    record = observations[0]
    receipt = journal.reconcile(
        record, registry_issue, read_comments=lambda: comments(
            specialist.REGISTRY, owner_number, fetch))
    return {
        **receipt,
        "case_id": case["case_id"],
        "dpip_issue_url": record["qualified_return"]["dpip_issue_url"],
        "canonical_toolkit_consumer_used": True,
        "specialist_transport_authenticated": False,
        "controller_reconciliation_executed": False,
        "assurance_determination_imported": False,
        "cutover_qualified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--dpip-issue", type=int, required=True)
    parser.add_argument("--toolkit", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = {"schema": "rahp-registry-epoch-journal-receipt/v1",
               "state": "indeterminate", "assurance_determination_imported": False}
    try:
        case = read_case(args.case)
        specialist.admitted_referral(case, {"number": args.dpip_issue})
        revision = subprocess.check_output(
            ["git", "-C", str(args.toolkit), "rev-parse", "HEAD"],
            text=True).strip()
        if revision != TOOLKIT_REV:
            raise LiveDPIPError("Toolkit canonical consumer revision mismatch")
        sys.path.insert(0, str(args.toolkit.resolve() / "tools"))
        import dpip_return_reconcile as consumer
        import assessor_contract
        token = os.getenv("GITHUB_TOKEN", "")
        if not token:
            raise LiveDPIPError("GitHub read token required")
        receipt = verify_live(
            case, args.dpip_issue, consumer, assessor_contract,
            fetch=lambda url: gh.request("GET", url, token))
    except (OSError, ValueError, TypeError, KeyError, ImportError,
            subprocess.CalledProcessError, gh.IntakeError) as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if receipt["state"] == "indeterminate":
        print("INDETERMINATE: no accepted live Registry DPIP return", file=sys.stderr)
        return 1
    print("Read-only Registry DPIP return:", receipt["state"], "(no assurance import)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
