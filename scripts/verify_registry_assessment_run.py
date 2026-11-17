#!/usr/bin/env python3
"""Qualify a pinned Registry-initiated canonical Toolkit run, without importing PASS."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLKIT_REVISION = "70298566dc897669e22bf37759843d6b7c0597d2"
CASE_ID = "RAHP-AR-DTG-0001"
REQUIREMENTS = {"DTG-0001-R1", "DTG-0001-R2"}


class QualificationError(ValueError):
    pass


def check(case, spec, ledger, result):
    if not all(isinstance(x, dict) for x in (case, spec, ledger, result)):
        raise QualificationError("documents must be objects")
    source = case.get("source", {})
    owners = case.get("owners", {})
    contract = spec.get("assurance_contract", {})
    target = spec.get("target", {})
    if case.get("case_id") != CASE_ID or spec.get("subject", {}).get("id") != CASE_ID:
        raise QualificationError("Registry case and canonical subject mismatch")
    if owners.get("current_active_issue") != (
        "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/4"
    ) or owners.get("handoff") != "accepted":
        raise QualificationError("Registry owner not accepted")
    if target.get("repository") != source.get("repository") or target.get("revision") != source.get("revision"):
        raise QualificationError("canonical run source pin disagrees with Registry case")
    if set(contract.get("required_evidence", [])) != {r.get("id") for r in case.get("residuals", [])}:
        raise QualificationError("required evidence does not match open Registry residuals")
    if set(contract.get("required_evidence", [])) != REQUIREMENTS:
        raise QualificationError("unexpected residual identity")
    if any(r.get("status") != "open" for r in case["residuals"]):
        raise QualificationError("case residual status changed; reassess run contract")
    if ledger.get("requirements") != []:
        raise QualificationError("pilot ledger unexpectedly claims target-native observations")
    if result.get("schema") != "rahp-assurance-run-state/v1":
        raise QualificationError("non-canonical RAHP result schema")
    if result.get("subject") != spec.get("subject"):
        raise QualificationError("canonical result subject differs from Registry proposition")
    if result.get("source_pins") != [{"repository": target["repository"], "revision": target["revision"]}]:
        raise QualificationError("canonical result source pins changed")
    if result.get("correlation_key") != spec.get("run", {}).get("lineage_prefix"):
        raise QualificationError("execution correlation key not preserved")
    if result.get("outcome") != "INDETERMINATE" or result.get("reason_code") != "evidence-required":
        raise QualificationError("missing native evidence did not remain INDETERMINATE/evidence-required")
    if result.get("state") != "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED":
        raise QualificationError("unqualified assurance state transition")
    if result.get("evidence") or not result.get("residuals"):
        raise QualificationError("evidence/result contradiction")
    if case.get("assessment", {}).get("determination") != "not_assessed":
        raise QualificationError("Registry case cannot silently import or promote controller result")
    return {
        "schema": "rahp-registry-canonical-run-qualification/v1",
        "case_id": CASE_ID,
        "result_assessment_id": result.get("assessment_id"),
        "source_pin": target,
        "canonical_toolkit_revision": TOOLKIT_REVISION,
        "result_outcome": "INDETERMINATE",
        "evidence_state": "missing-native-consumer-evidence",
        "registry_assessment_imported": False,
        "controller_cutover_qualified": False,
        "external_effects": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = [json.loads(path.read_text(encoding="utf-8"))
                for path in (args.case, args.spec, args.ledger, args.result)]
        receipt = check(*data)
    except (ValueError, OSError) as exc:
        print(f"INVALID Registry canonical run: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("PASS source-pinned canonical Toolkit run reconciliation: evidence-required; not assurance PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
