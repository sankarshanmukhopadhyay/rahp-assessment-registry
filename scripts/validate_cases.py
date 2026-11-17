#!/usr/bin/env python3
"""Structural registry guardrail; no RAHP assurance determination is produced."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
LIFECYCLES = {"proposed", "active", "waiting_external", "superseded", "closed"}
EVIDENCE = {"unverified", "partially_verified", "verified", "unavailable", "contradictory"}
DETERMINATIONS = {"not_assessed", "PASS", "FAIL", "NOT_APPLICABLE", "INDETERMINATE"}
CHANGES = {"new", "preserved", "strengthened", "weakened", "uncertain"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")


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
    require(isinstance(case["lifecycle"], dict) and case["lifecycle"].get("state") in LIFECYCLES, "invalid lifecycle")
    require(isinstance(case["evidence"], dict) and case["evidence"].get("state") in EVIDENCE, "invalid evidence state")
    require(isinstance(case["assessment"], dict) and case["assessment"].get("determination") in DETERMINATIONS, "invalid determination")
    require(isinstance(case["assessment"], dict) and case["assessment"].get("change_classification") in CHANGES, "invalid classification")
    require(isinstance(case["source"], dict) and bool(case["source"].get("repository") and case["source"].get("revision")
                 and case["source"].get("finding_id")), "missing source pin")
    if isinstance(case["source"], dict) and case["source"].get("revision"):
        require(isinstance(case["source"]["revision"], str)
                and SHA40.fullmatch(case["source"]["revision"]) is not None,
                "source revision must be immutable 40-hex commit")
    require(isinstance(case["owners"], dict) and bool(case["owners"].get("registry") and case["owners"].get("upstream")),
            "missing authoritative ownership")
    require(isinstance(case["residuals"], list), "residuals must be an array")
    if errors:
        return errors


    referrals = case.get("referrals", [])
    require(isinstance(referrals, list), "referrals must be an array")
    if isinstance(referrals, list):
        for idx, route in enumerate(referrals):
            prefix = f"referrals[{idx}]"
            if not isinstance(route, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            role = route.get("role")
            allowed = {"specialist_assessor": "rahp-assessor-result/v1",
                       "evidence_producer": "rahp-evidence-producer-result/v1"}
            require(role in allowed, f"{prefix}: unknown role")
            if role in allowed:
                require(route.get("contract") == allowed[role], f"{prefix}: contract/role mismatch")
            require(isinstance(route.get("repository"), str) and bool(route.get("repository")),
                    f"{prefix}: missing producer repository")
            require(isinstance(route.get("issue_url"), str)
                    and route.get("issue_url", "").startswith("https://github.com/"),
                    f"{prefix}: missing canonical source issue")
            require(route.get("status") in {"requested", "accepted", "returned", "blocked"},
                    f"{prefix}: invalid status")
            if route.get("status") == "returned":
                require(isinstance(route.get("result_url"), str)
                        and route.get("result_url", "").startswith("https://"),
                        f"{prefix}: returned result must cite source URI")
                require(isinstance(route.get("result_revision"), str)
                        and bool(route.get("result_revision")),
                        f"{prefix}: returned result requires source revision")
                if isinstance(route.get("result_revision"), str):
                    require(SHA40.fullmatch(route["result_revision"]) is not None,
                            f"{prefix}: returned result revision must be immutable 40-hex commit")
            if isinstance(route.get("repository"), str) and isinstance(route.get("issue_url"), str):
                repo = route["repository"]
                require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) is not None
                        and re.fullmatch(r"https://github[.]com/" + re.escape(repo)
                                             + r"/issues/[1-9][0-9]*", route["issue_url"]) is not None,
                        f"{prefix}: source issue URL must match producer repository")

    if case["assessment"].get("determination") != "not_assessed":
        imported = case["assessment"].get("imported_result")
        require(isinstance(imported, dict) and bool(imported.get("uri") and imported.get("assessment_id")
                and imported.get("source_revision") and imported.get("determination") == case["assessment"].get("determination")),
                "RAHP determination requires matching attributable imported result reference")
        if isinstance(imported, dict) and imported.get("source_revision"):
            require(isinstance(case["source"], dict)
                    and imported["source_revision"] == case["source"].get("revision"),
                    "imported RAHP result source revision must match case source revision")

    if case["assessment"].get("determination") == "PASS":
        require(case["evidence"].get("state") == "verified", "PASS requires verified evidence")
        require(bool(case["assessment"].get("basis")), "PASS requires an attributable basis")
        require(bool(case["evidence"].get("sources")), "PASS requires cited evidence")
    if case["lifecycle"].get("state") in ("closed", "superseded"):
        require(case["owners"].get("handoff") == "accepted" or not case["residuals"],
                "terminal case with residuals requires accepted handoff")
        require(all(isinstance(r, dict) and r.get("status") == "transferred" and r.get("owner")
                    for r in case["residuals"]), "terminal case cannot retain open residuals")
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
