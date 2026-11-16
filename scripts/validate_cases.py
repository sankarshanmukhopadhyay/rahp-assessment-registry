#!/usr/bin/env python3
"""Structural registry guardrail; no RAHP assurance determination is produced."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
LIFECYCLES = {"proposed", "active", "waiting_external", "superseded", "closed"}
EVIDENCE = {"unverified", "partially_verified", "verified", "unavailable", "contradictory"}
DETERMINATIONS = {"not_assessed", "PASS", "FAIL", "NOT_APPLICABLE", "INDETERMINATE"}
CHANGES = {"new", "preserved", "strengthened", "weakened", "uncertain"}


def validate(case):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)

    for key in ("schema_version", "case_id", "title", "subject", "proposition", "source",
                "owners", "lifecycle", "assessment", "evidence", "residuals", "reassessment"):
        require(key in case, f"missing {key}")
    if errors:
        return errors

    require(isinstance(case["case_id"], str) and bool(case["case_id"].strip()), "empty case_id")
    require(case["lifecycle"].get("state") in LIFECYCLES, "invalid lifecycle")
    require(case["evidence"].get("state") in EVIDENCE, "invalid evidence state")
    require(case["assessment"].get("determination") in DETERMINATIONS, "invalid determination")
    require(case["assessment"].get("change_classification") in CHANGES, "invalid classification")
    require(bool(case["source"].get("repository") and case["source"].get("revision")
                 and case["source"].get("finding_id")), "missing source pin")
    require(bool(case["owners"].get("registry") and case["owners"].get("upstream")),
            "missing authoritative ownership")
    require(isinstance(case["residuals"], list), "residuals must be an array")

    if case["assessment"].get("determination") == "PASS":
        require(case["evidence"].get("state") == "verified", "PASS requires verified evidence")
        require(bool(case["assessment"].get("basis")), "PASS requires an attributable basis")
        require(bool(case["evidence"].get("sources")), "PASS requires cited evidence")
    if case["lifecycle"].get("state") == "closed":
        require(case["owners"].get("handoff") == "accepted" or not case["residuals"],
                "closed case with residuals requires accepted handoff")
        require(all(r.get("status") == "transferred" and r.get("owner")
                    for r in case["residuals"]), "closed case cannot retain open residuals")
    if case["owners"].get("handoff") == "not_accepted":
        require(case["lifecycle"].get("state") not in ("closed", "superseded"),
                "unaccepted handoff cannot be terminal")
    return errors


def run(root=CASES):
    paths = sorted(root.rglob("*.json"))
    if not paths:
        return ["no case records found"]
    issues, seen = [], set()
    for path in paths:
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            issues.append(f"{path}: invalid JSON: {exc}")
            continue
        errors = validate(case)
        ident = case.get("case_id")
        if ident in seen:
            errors.append("duplicate case_id")
        seen.add(ident)
        issues.extend(f"{path}: {error}" for error in errors)
    return issues


if __name__ == "__main__":
    failures = run()
    for item in failures:
        print(item)
    if failures:
        raise SystemExit(1)
    print("Registry case structural validation: PASS (not assurance PASS)")
