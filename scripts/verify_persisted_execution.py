#!/usr/bin/env python3
"""Verify a Git-persisted Registry execution against the canonical pinned Toolkit run.

This is case-scoped artifact integrity and reproducibility, not independent
specialist authentication, assurance acceptance, or an append-only audit log.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bind_registry_execution import BindingError, TOOLKIT_REVISION, verify_binding
from verify_registry_assessment_run import check as qualify_pilot

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/dtg/network-answer-proof-2026-11.json"
SPEC = ROOT / "ops/assessments/network-answer-pilot.spec.json"
LEDGER = ROOT / "ops/assessments/network-answer-pilot.ledger.json"
RECORDS = ROOT / "ops/executions"
HISTORICAL_RUN = "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/43988780802"


class RecordError(ValueError):
    pass


def check_record(record, case, spec, ledger, *, actual_result=None):
    if not isinstance(record, dict) or set(record) != {
        "schema", "source_workflow_run", "result", "binding", "qualification"
    }:
        raise RecordError("unexpected record keys")
    if record["schema"] != "rahp-registry-canonical-execution-record/v1":
        raise RecordError("unsupported execution record schema")
    if record["source_workflow_run"] != HISTORICAL_RUN:
        raise RecordError("unqualified provenance/run reference")
    result, binding = record["result"], record["binding"]
    if not isinstance(result, dict) or not isinstance(binding, dict):
        raise RecordError("record result and binding must be objects")
    try:
        verify_binding(binding, case, spec, ledger, result, toolkit_revision=TOOLKIT_REVISION)
    except (BindingError, TypeError, KeyError) as exc:
        raise RecordError("canonical execution binding invalid: " + str(exc)) from exc
    qualified = qualify_pilot(case, spec, ledger, result)
    if qualified != record["qualification"]:
        raise RecordError("stored qualification differs from the canonical validator")
    if any(binding.get(k) is not False for k in (
        "case_determination_imported", "external_specialist_authenticated",
        "delivery_acknowledged", "controller_cutover_qualified"
    )):
        raise RecordError("unsupported assurance, delivery or cutover claim")
    if actual_result is not None and result != actual_result:
        raise RecordError("stored canonical result differs from fresh controller execution")
    return binding["binding_key"]


def validate_all(root=RECORDS):
    paths = sorted(root.glob("*/*.json"))
    if not paths:
        raise RecordError("no persisted execution records")
    case = json.loads(CASE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    keys = set()
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        key = check_record(record, case, spec, ledger)
        if key in keys:
            raise RecordError("duplicate persisted canonical execution key")
        keys.add(key)
        if path.parent.name != record["binding"]["case_id"]:
            raise RecordError("record directory mismatches Registry case identity")
        if path.stem != record["result"]["assessment_id"].replace(":", "-"):
            raise RecordError("record filename mismatches Toolkit execution identity")
    return len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual-result", type=Path, help="fresh canonical engine result to compare")
    args = parser.parse_args()
    try:
        count = validate_all()
        if args.actual_result:
            actual = json.loads(args.actual_result.read_text(encoding="utf-8"))
            path = RECORDS / "RAHP-AR-DTG-0001/rahp-369ffe8e6f037e6235d5.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            case = json.loads(CASE.read_text(encoding="utf-8"))
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
            check_record(record, case, spec, ledger, actual_result=actual)
    except (RecordError, BindingError, OSError, ValueError, TypeError, KeyError) as exc:
        print("INVALID persisted canonical Registry execution:", exc, file=sys.stderr)
        return 1
    print(f"PASS {count} Git-persisted canonical execution(s), no assurance import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
