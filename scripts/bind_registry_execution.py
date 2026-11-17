#!/usr/bin/env python3
"""Bind one Registry case to an attributable, pinned Toolkit result artifact.

This is a read-only execution correlation receipt, not a delegation,
specialist-return authentication or Registry assurance-import decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from verify_registry_assessment_run import check as qualify_pilot, TOOLKIT_REVISION

SCHEMA = "rahp-registry-execution-binding/v1"
HEX40 = re.compile(r"^[a-f0-9]{40}$")


class BindingError(ValueError):
    pass


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def create_binding(case, spec, ledger, result, *, toolkit_revision):
    if not HEX40.fullmatch(str(toolkit_revision)):
        raise BindingError("Toolkit revision must be an immutable 40-hex commit")
    if toolkit_revision != TOOLKIT_REVISION:
        raise BindingError("Toolkit contract revision is not the qualified pin")
    # Use the already qualified Registry pilot's existing negative-evidence
    # contract, never a locally reimplemented assurance decision.
    try:
        qualified = qualify_pilot(case, spec, ledger, result)
    except (ValueError, TypeError, KeyError) as exc:
        raise BindingError(f"canonical run qualification failed: {exc}") from exc
    aid = result.get("assessment_id")
    if not isinstance(aid, str) or not aid.strip():
        raise BindingError("canonical result has no assessment identity")
    if result.get("terminal") is not True:
        raise BindingError("canonical assessment result is not terminal")
    pins = result.get("source_pins")
    if not isinstance(pins, list) or not pins:
        raise BindingError("canonical result source pins missing")
    lineage = result.get("lineage")
    if not isinstance(lineage, dict) or lineage.get("clean_room") is not True:
        raise BindingError("expected canonical clean-room execution lineage missing")
    if lineage.get("historical_inputs_used") is not False:
        raise BindingError("historical evidence reuse not excluded")
    scope = {
        "case_id": qualified["case_id"],
        "registry_case_url": case["owners"]["current_active_issue"],
        "source_finding_id": case["source"]["finding_id"],
        "source_pins": pins,
        "toolkit_revision": toolkit_revision,
        "toolkit_assessment_id": aid,
        "toolkit_correlation_key": result["correlation_key"],
    }
    return {
        "schema": SCHEMA,
        "binding_key": "rahp-execution:" + digest(scope)[:32],
        **scope,
        "result_sha256": digest(result),
        "result_outcome": result["outcome"],
        "result_reason_code": result["reason_code"],
        "result_state": result["state"],
        "result_artifact": "build/registry-assessment/result.json",
        "case_determination_imported": False,
        "external_specialist_authenticated": False,
        "delivery_acknowledged": False,
        "controller_cutover_qualified": False,
    }


def verify_binding(observed, case, spec, ledger, result, *, toolkit_revision):
    if not isinstance(observed, dict) or set(observed) != set(create_binding(
            case, spec, ledger, result, toolkit_revision=toolkit_revision)):
        raise BindingError("execution binding fields missing or unexpected")
    expected = create_binding(case, spec, ledger, result,
                              toolkit_revision=toolkit_revision)
    if canonical_bytes(observed) != canonical_bytes(expected):
        raise BindingError("execution binding mismatches exact qualified source/result")
    return expected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--toolkit-revision", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--verify", action="store_true", help="verify existing receipt without rewriting it")
    a = p.parse_args()
    try:
        case, spec, ledger, result = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (a.case, a.spec, a.ledger, a.result)
        ]
        if a.verify:
            observed = json.loads(a.out.read_text(encoding="utf-8"))
            binding = verify_binding(observed, case, spec, ledger, result,
                                     toolkit_revision=a.toolkit_revision)
        else:
            binding = create_binding(case, spec, ledger, result,
                                     toolkit_revision=a.toolkit_revision)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(binding, sort_keys=True, indent=2) + "\n",
                             encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"INVALID execution binding: {exc}", file=sys.stderr)
        return 1
    print(f"PASS {binding['binding_key']} (case binding only; no assurance import)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
