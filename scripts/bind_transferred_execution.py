#!/usr/bin/env python3
"""Bind an accepted monitored Registry case to one canonical Toolkit execution.

Read-only source/execution correlation. This does not admit a specialist
referral, authorize an issue-number adapter, or accept an assurance outcome.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bind_registry_execution import canonical_bytes, digest

SCHEMA = "rahp-registry-transferred-execution-binding/v1"
REGISTRY = "sankarshanmukhopadhyay/rahp-assessment-registry"
TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
ENGINE_REVISION = "70298566dc897669e22bf37759843d6b7c0597d2"
CASE_ID = "RAHP-AR-DTG-0002"
KEY = "dtg:portfolio:combined:spec-dependency-alignment"
TK_ISSUE = f"https://github.com/{TOOLKIT}/issues/272"
REG_ISSUE = f"https://github.com/{REGISTRY}/issues/88"
HEX40 = re.compile(r"^[a-f0-9]{40}$")


class TransferBindingError(ValueError):
    pass


def bind(case, transfer_ledger, spec, evidence_ledger, result, *,
         engine_revision, transfer_ledger_revision):
    """Require the exact accepted administrative owner, not a numeric alias."""
    if not all(isinstance(v, dict) for v in
               (case, transfer_ledger, spec, evidence_ledger, result)):
        raise TransferBindingError("all inputs must be JSON objects")
    if engine_revision != ENGINE_REVISION or not HEX40.fullmatch(str(transfer_ledger_revision)):
        raise TransferBindingError("canonical engine or Toolkit ledger revision not pinned")
    if transfer_ledger.get("schema") != "rahp-registry-transfers/v1":
        raise TransferBindingError("unsupported Toolkit authority ledger")
    rows = transfer_ledger.get("transfers")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise TransferBindingError("exactly one accepted Toolkit source owner expected")
    transfer = rows[0]
    if any((transfer.get(k) != v) for k, v in {
        "state": "accepted_group", "assessment_key": KEY,
        "toolkit_issue_url": TK_ISSUE, "registry_issue_url": REG_ISSUE
    }.items()):
        raise TransferBindingError("source ownership is not the accepted group")
    source = case.get("source")
    owners = case.get("owners")
    if (case.get("case_id") != CASE_ID or not isinstance(source, dict)
            or not isinstance(owners, dict)
            or owners.get("registry") != REGISTRY
            or owners.get("execution") != TOOLKIT
            or owners.get("handoff") != "accepted"
            or owners.get("current_active_issue") != REG_ISSUE
            or owners.get("historical_source_issue") != TK_ISSUE):
        raise TransferBindingError("Registry case and Toolkit execution namespaces conflict")
    if (source.get("revision") != transfer.get("monitor_revision")
            or source.get("group_sha256") != transfer.get("group_sha256")
            or source.get("observed_on") != transfer.get("snapshot_date")
            or source.get("finding_ids") != transfer.get("finding_ids")
            or source.get("finding_id") not in transfer.get("finding_ids", [])):
        raise TransferBindingError("case source identity differs from accepted group")
    if (not isinstance(source.get("repository"), str)
            or not HEX40.fullmatch(source["revision"])
            or not re.fullmatch(r"[0-9a-f]{64}", str(source["group_sha256"]))
            or not isinstance(source["finding_ids"], list)
            or len(source["finding_ids"]) != 4
            or source["finding_ids"] != sorted(set(source["finding_ids"]))):
        raise TransferBindingError("incomplete accepted monitored source pins")
    open_residuals = [x.get("id") for x in case.get("residuals", [])
                      if isinstance(x, dict) and x.get("status") == "open"]
    contract = spec.get("assurance_contract")
    required = contract.get("required_evidence") if isinstance(contract, dict) else None
    if (not open_residuals or len(open_residuals) != len(set(open_residuals))
            or required != open_residuals):
        raise TransferBindingError("required execution evidence and case residuals differ")
    pin = {"repository": source["repository"], "revision": source["revision"]}
    if (spec.get("target") != pin
            or (spec.get("subject") or {}).get("id") != CASE_ID
            or spec.get("subject", {}).get("type") != "monitored-source-materiality"
            or spec.get("subject", {}).get("components") != source["finding_ids"]
            or not isinstance(spec.get("run"), dict)
            or spec["run"].get("lineage_prefix") !=
               f"registry:{CASE_ID}:{source['group_sha256']}"):
        raise TransferBindingError("canonical execution scope does not bind the source group")
    if evidence_ledger != {"requirements": []}:
        raise TransferBindingError("target-native evidence was not admitted in this bounded replay")
    if (case.get("assessment", {}).get("determination") != "not_assessed"
            or case.get("referrals") != []):
        raise TransferBindingError("case has unsupported assurance or specialist state")
    if (result.get("schema") != "rahp-assurance-run-state/v1"
            or result.get("subject") != spec["subject"]
            or result.get("source_pins") != [pin]
            or result.get("correlation_key") != spec["run"]["lineage_prefix"]
            or result.get("terminal") is not True
            or result.get("outcome") != "INDETERMINATE"
            or result.get("reason_code") != "evidence-required"
            or result.get("state") != "TERMINAL_INDETERMINATE_EVIDENCE_REQUIRED"
            or result.get("evidence")
            or not result.get("residuals")):
        raise TransferBindingError("canonical result is absent, contradictory or elevated")
    lineage = result.get("lineage")
    if (not isinstance(lineage, dict) or lineage.get("clean_room") is not True
            or lineage.get("historical_inputs_used") is not False
            or lineage.get("run") != spec["run"]
            or not isinstance(result.get("assessment_id"), str)
            or not result["assessment_id"]):
        raise TransferBindingError("canonical run identity/clean-room lineage absent")
    scope = {
        "case_id": CASE_ID, "registry_case_url": REG_ISSUE,
        "historical_toolkit_issue_url": TK_ISSUE,
        "source_group_sha256": source["group_sha256"],
        "source_finding_ids": source["finding_ids"],
        "source_pins": [pin],
        "toolkit_transfer_ledger_revision": transfer_ledger_revision,
        "toolkit_engine_revision": engine_revision,
        "toolkit_execution_id": result["assessment_id"],
        "toolkit_correlation_key": result["correlation_key"],
    }
    return {
        "schema": SCHEMA, "binding_key": "rahp-execution:" + digest(scope)[:32],
        **scope, "result_sha256": digest(result),
        "result_outcome": "INDETERMINATE",
        "result_reason_code": "evidence-required",
        "case_determination_imported": False,
        "source_transfer_authority_extended": False,
        "registry_to_toolkit_dispatch_authorized": False,
        "specialist_return_authenticated": False,
        "controller_cutover_qualified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for item in ("case", "transfer-ledger", "spec", "evidence-ledger", "result", "out"):
        p.add_argument("--" + item, type=Path, required=True)
    p.add_argument("--engine-revision", required=True)
    p.add_argument("--transfer-ledger-revision", required=True)
    a = p.parse_args()
    try:
        values = [json.loads(getattr(a, field).read_text(encoding="utf-8"))
                  for field in ("case", "transfer_ledger", "spec", "evidence_ledger", "result")]
        receipt = bind(*values, engine_revision=a.engine_revision,
                       transfer_ledger_revision=a.transfer_ledger_revision)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"INVALID transferred execution binding: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {receipt['binding_key']} (evidence-required; no transfer authority extension)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
