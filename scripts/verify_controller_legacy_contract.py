#!/usr/bin/env python3
"""Read-only compatibility preflight against an immutable canonical Toolkit revision.

This checks legacy identity contracts; it does not authorize or execute RAHP, DPIP
or Interop Lab work, and it does not validate a specialist's authority.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TOOLKIT_REVISION = "70298566dc897669e22bf37759843d6b7c0597d2"
TOOLKIT_REPOSITORY = "sankarshanmukhopadhyay/rahp-toolkit"
REGISTRY_CASE = "RAHP-AR-DTG-0001"
REGISTRY_ISSUE = "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4"
HISTORICAL_ISSUE = "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1203"
SOURCE_REVISION = "303174f8ca630ca14ddc2cbf5abcb0d10e205c38"
SOURCE_FINDING = "4cdb4f9a7399aea0a55a"


class PreflightError(ValueError):
    pass


def historical_pilot(case: dict) -> dict:
    """Classify the reviewed pilot, explicitly refusing an active controller anchor."""
    if not isinstance(case, dict):
        raise PreflightError("case is not an object")
    owners = case.get("owners")
    source = case.get("source")
    assessment = case.get("assessment")
    lifecycle = case.get("lifecycle")
    if not all(isinstance(x, dict) for x in (owners, source, assessment, lifecycle)):
        raise PreflightError("case source, ownership, lifecycle or assessment is malformed")
    if case.get("case_id") != REGISTRY_CASE:
        raise PreflightError("unexpected case identity")
    if owners.get("current_active_issue") != REGISTRY_ISSUE or owners.get("handoff") != "accepted":
        raise PreflightError("registry pilot ownership is not accepted")
    if owners.get("historical_source_issue") != HISTORICAL_ISSUE:
        raise PreflightError("historic Toolkit issue identity changed")
    if owners.get("execution") != TOOLKIT_REPOSITORY:
        raise PreflightError("canonical Toolkit authority changed")
    if source.get("revision") != SOURCE_REVISION or source.get("finding_id") != SOURCE_FINDING:
        raise PreflightError("source revision or finding identity changed")
    if not re.fullmatch(r"[a-f0-9]{40}", source["revision"]):
        raise PreflightError("source revision is not immutable")
    if lifecycle.get("state") != "active":
        raise PreflightError("pilot case is not active")
    if assessment.get("determination") != "not_assessed" or assessment.get("imported_result"):
        raise PreflightError("pilot has unsupported RAHP determination")
    if case.get("referrals") != []:
        raise PreflightError("pilot now contains referrals; reassess active controller status")
    return {
        "case_id": REGISTRY_CASE,
        "registry_case_url": REGISTRY_ISSUE,
        "historical_toolkit_issue_url": HISTORICAL_ISSUE,
        "legacy_issue_number": 1203,
        "source_repository": source.get("repository"),
        "source_revision": SOURCE_REVISION,
        "finding_id": SOURCE_FINDING,
        "controller_anchor": "historical_only",
        "active_execution_id": None,
        "eligible_for_dispatch": False,
    }


def check_contract(case: dict, toolkit: Path) -> dict:
    pilot = historical_pilot(case)
    if not (toolkit / "tools" / "dpip_handoff.py").is_file():
        raise PreflightError("canonical Toolkit checkout missing")
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(toolkit), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PreflightError("cannot establish Toolkit revision") from exc
    if revision != TOOLKIT_REVISION:
        raise PreflightError("Toolkit revision does not match immutable contract pin")

    sys.path.insert(0, str(toolkit / "tools"))
    import dpip_handoff
    import dpip_return_reconcile

    payload = {
        "source_change": {
            "repository": pilot["source_repository"],
            "revision": pilot["source_revision"],
            "monitor_fingerprint": pilot["finding_id"],
        },
        "affected_interactions": ["C3"],
        "question": "Does an observed material change require a bounded privacy examination?",
    }
    if dpip_handoff.validate_payload(payload):
        raise PreflightError("canonical Toolkit rejected source-pinned legacy fixture")

    legacy_marker, legacy_digest = dpip_handoff.identity(1203, payload)
    repeat_marker, repeat_digest = dpip_handoff.identity(1203, payload)
    substituted_marker, substituted_digest = dpip_handoff.identity(4, payload)
    if (legacy_marker, legacy_digest) != (repeat_marker, repeat_digest):
        raise PreflightError("legacy identity not stable on replay")
    if legacy_marker == substituted_marker or legacy_digest != substituted_digest:
        raise PreflightError("issue-number identity and semantic digest no longer separated")
    if dpip_handoff.referral_marker(1203, payload) == dpip_handoff.referral_marker(4, payload):
        raise PreflightError("legacy referral marker lost source issue binding")

    source = dpip_handoff.source_data(TOOLKIT_REPOSITORY, {"number": 1203}, payload)
    if source.get("issue") != 1203 or source.get("repository") != TOOLKIT_REPOSITORY:
        raise PreflightError("legacy handoff source issue provenance changed")
    if source.get("changed_artifact") != {
        "repository": pilot["source_repository"], "revision": pilot["source_revision"]
    }:
        raise PreflightError("source revision changed in canonical handoff")
    if dpip_return_reconcile.reconciliation_marker(1203, 147) == (
        dpip_return_reconcile.reconciliation_marker(4, 147)
    ):
        raise PreflightError("legacy return reconciliation lost source issue binding")
    if dpip_return_reconcile.parse_return([]) is not None:
        raise PreflightError("missing DPIP return was treated as an actual return")

    return {
        "schema": "rahp-registry-controller-legacy-preflight/v1",
        "toolkit_revision": revision,
        "pilot": pilot,
        "legacy_contract": {
            "source_issue_number": 1203,
            "registry_issue_number": 4,
            "source_issue_identity_is_semantically_distinct": True,
            "semantic_digest_preserved_across_issue_number_substitution": True,
            "repeated_legacy_identity_is_stable": True,
            "missing_return_is_not_a_return": True,
        },
        "assurance_determination": "not_assessed",
        "controller_cutover_qualified": False,
        "specialist_return_authenticated": False,
        "publication_or_external_effects": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        result = check_contract(case, args.toolkit.resolve())
    except (OSError, ValueError, ImportError) as exc:
        print(f"INVALID controller legacy preflight: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PASS legacy Toolkit controller identity preflight; no dispatch or assurance PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
