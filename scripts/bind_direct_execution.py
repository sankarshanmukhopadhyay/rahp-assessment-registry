#!/usr/bin/env python3
"""Bind a source-qualified direct Registry case to an actual canonical Toolkit run.

No issue-number substitution, external result authentication, specialist delivery
or Registry assurance import is authorized by a matching binding receipt.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bind_registry_execution import canonical_bytes, digest

SCHEMA = "rahp-registry-direct-execution-binding/v1"
REGISTRY = "sankarshanmukhopadhyay/rahp-assessment-registry"
TOOLKIT_REVISION = "70298566dc897669e22bf37759843d6b7c0597d2"
SHA = re.compile(r"^[0-9a-f]{40}$")
ISSUE = re.compile(r"^https://github[.]com/" + REGISTRY + r"/issues/[1-9][0-9]*$")


class DirectBindingError(ValueError):
    pass


def create_binding(case, spec, ledger, result, *, toolkit_revision):
    if not all(isinstance(x, dict) for x in (case, spec, ledger, result)):
        raise DirectBindingError("case, spec, ledger and result must be objects")
    if toolkit_revision != TOOLKIT_REVISION:
        raise DirectBindingError("canonical Toolkit execution pin differs")
    case_id = case.get("case_id")
    source = case.get("source") or {}
    owners = case.get("owners") or {}
    if not isinstance(case_id, str) or not case_id or not isinstance(source, dict) or not isinstance(owners, dict):
        raise DirectBindingError("case identity or source missing")
    if owners.get("admission") != "direct" or owners.get("handoff") != "not_applicable" or (
            owners.get("historical_source_issue") is not None):
        raise DirectBindingError("direct intake cannot impersonate historical Toolkit transfer")
    owner_url = owners.get("current_active_issue")
    if not isinstance(owner_url, str) or not ISSUE.fullmatch(owner_url):
        raise DirectBindingError("Registry administrative owner URL absent or foreign")
    if (owners.get("registry") != REGISTRY or
            owners.get("execution") != "sankarshanmukhopadhyay/rahp-toolkit"):
        raise DirectBindingError("case owner and engine authority conflict")
    pin = {"repository": source.get("repository"), "revision": source.get("revision")}
    if not isinstance(pin["repository"], str) or not isinstance(pin["revision"], str) or not SHA.fullmatch(pin["revision"]):
        raise DirectBindingError("case source pin missing")
    if spec.get("target") != pin or (spec.get("subject") or {}).get("id") != case_id:
        raise DirectBindingError("canonical execution target/subject differs from Registry case")
    open_ids = {x.get("id") for x in case.get("residuals", []) if isinstance(x, dict) and x.get("status") == "open"}
    required = (spec.get("assurance_contract") or {}).get("required_evidence")
    if not isinstance(required, list) or len(required) != len(set(required)) or set(required) != open_ids or not required:
        raise DirectBindingError("open residuals and required evidence do not match")
    if ledger != {"requirements": []}:
        raise DirectBindingError("no independently verified target-native evidence has been admitted")
    if case.get("assessment", {}).get("determination") != "not_assessed" or case.get("referrals"):
        raise DirectBindingError("unverified case cannot import determination or specialist referral")
    if (result.get("schema") != "rahp-assurance-run-state/v1"
            or result.get("subject") != spec["subject"]
            or result.get("source_pins") != [pin]
            or result.get("correlation_key") != (spec.get("run") or {}).get("lineage_prefix")):
        raise DirectBindingError("canonical result source/subject/execution correlation mismatch")
    if (result.get("terminal") is not True or result.get("outcome") != "INDETERMINATE"
            or result.get("reason_code") != "evidence-required"
            or result.get("state") != "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED"
            or result.get("evidence") or not result.get("residuals")):
        raise DirectBindingError("unsupported assurance elevation or contradictory result")
    lineage = result.get("lineage") or {}
    if not isinstance(lineage, dict) or lineage.get("clean_room") is not True or (
            lineage.get("historical_inputs_used") is not False or lineage.get("run") != spec.get("run")):
        raise DirectBindingError("canonical clean-room run lineage absent")
    aid = result.get("assessment_id")
    if not isinstance(aid, str) or not aid:
        raise DirectBindingError("canonical assessment identity absent")
    scope = {
        "case_id": case_id, "registry_case_url": owner_url,
        "source_finding_id": source["finding_id"], "source_pins": [pin],
        "toolkit_revision": toolkit_revision,
        "toolkit_assessment_id": aid, "toolkit_correlation_key": result["correlation_key"],
        "historical_toolkit_issue_number": None,
    }
    return {
        "schema": SCHEMA, "binding_key": "rahp-execution:" + digest(scope)[:32], **scope,
        "result_sha256": digest(result), "result_outcome": "INDETERMINATE",
        "result_reason_code": "evidence-required",
        "case_determination_imported": False,
        "external_specialist_authenticated": False,
        "delivery_acknowledged": False,
        "controller_cutover_qualified": False,
    }


def verify_binding(receipt, case, spec, ledger, result, *, toolkit_revision):
    expected = create_binding(case, spec, ledger, result, toolkit_revision=toolkit_revision)
    if not isinstance(receipt, dict) or canonical_bytes(receipt) != canonical_bytes(expected):
        raise DirectBindingError("direct execution binding differs from exact canonical result")
    return expected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("case", "spec", "ledger", "result", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--toolkit-revision", required=True)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    try:
        case, spec, ledger, result = [json.loads(
            getattr(args, name).read_text(encoding="utf-8"))
            for name in ("case", "spec", "ledger", "result")]
        if args.verify:
            existing = json.loads(args.out.read_text(encoding="utf-8"))
            receipt = verify_binding(existing, case, spec, ledger, result,
                                     toolkit_revision=args.toolkit_revision)
        else:
            receipt = create_binding(case, spec, ledger, result,
                                     toolkit_revision=args.toolkit_revision)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("INVALID direct Registry execution binding:", exc, file=sys.stderr)
        return 1
    print("Bound", receipt["binding_key"], "(no assurance or specialist import)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
