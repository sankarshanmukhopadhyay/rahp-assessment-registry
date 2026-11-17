#!/usr/bin/env python3
"""Verify local historical Toolkit locator and accepted Registry succession.

This is source-controlled metadata coverage, not live GitHub availability,
archive completeness after capture, or independent gate acceptance.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/"
REGISTRY = "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/"
SNAPSHOT_SCHEMA = "rahp-toolkit-issue-metadata-archive/v1"


class LocatorError(ValueError):
    pass


def verify(root=ROOT):
    root = Path(root)
    manifest = json.loads((root / "archive/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != SNAPSHOT_SCHEMA or manifest.get("source_repository") != (
            "sankarshanmukhopadhyay/rahp-toolkit"):
        raise LocatorError("unsupported source metadata archive")
    partitions = manifest.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        raise LocatorError("archive partitions absent")
    source = {}
    open_count = closed_count = 0
    for part in partitions:
        path = part.get("path") if isinstance(part, dict) else None
        if not isinstance(path, str) or not re.fullmatch(
                r"archive/snapshots/toolkit-issues-[0-9]{4}-[0-9]{2}-[0-9]{2}-p[1-9][0-9]*[.]json", path):
            raise LocatorError("invalid archive partition reference")
        records = json.loads((root / path).read_text(encoding="utf-8"))
        if not isinstance(records, list) or len(records) != part.get("expected_issues"):
            raise LocatorError("archive partition count mismatch: " + path)
        for record in records:
            if not isinstance(record, dict):
                raise LocatorError("non-object source issue metadata")
            number = record.get("number")
            if (type(number) is not int or number <= 0
                    or record.get("url") != TOOLKIT + str(number)
                    or record.get("state") not in ("open", "closed")):
                raise LocatorError("unqualified source issue locator")
            if number in source:
                raise LocatorError("duplicate historical source number: " + str(number))
            source[number] = record
            open_count += record["state"] == "open"
            closed_count += record["state"] == "closed"
    if (len(source) != manifest.get("total_issues")
            or {"open": open_count, "closed": closed_count} != manifest.get("state_counts")):
        raise LocatorError("archive total or state counts contradict snapshot")
    assigned_history, assigned_successors = {}, {}
    count_direct = count_accepted = 0
    for case_path in sorted((root / "cases").rglob("*.json")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        owners = case.get("owners", {})
        if not isinstance(owners, dict):
            raise LocatorError("case owners must be an object")
        if owners.get("handoff") != "accepted":
            if owners.get("admission") == "direct":
                if owners.get("historical_source_issue") is not None:
                    raise LocatorError("direct case cannot claim a historical Toolkit issue")
                count_direct += 1
            continue
        historical = owners.get("historical_source_issue")
        successor = owners.get("current_active_issue")
        if not isinstance(historical, str) or not re.fullmatch(
                re.escape(TOOLKIT) + r"[1-9][0-9]*", historical):
            raise LocatorError("accepted case lacks canonical historical issue")
        if not isinstance(successor, str) or not re.fullmatch(
                re.escape(REGISTRY) + r"[1-9][0-9]*", successor):
            raise LocatorError("accepted case lacks canonical Registry successor")
        number = int(historical.removeprefix(TOOLKIT))
        record = source.get(number)
        if record is None:
            raise LocatorError("accepted history not represented in source locator: " + historical)
        if record.get("registry_successor") != successor:
            raise LocatorError("historical locator lacks accepted successor mapping")
        if historical in assigned_history or successor in assigned_successors:
            raise LocatorError("ambiguous historical issue or Registry successor ownership")
        assigned_history[historical] = case.get("case_id")
        assigned_successors[successor] = case.get("case_id")
        count_accepted += 1
    return {"schema": "rahp-history-locator-qualification/v1",
            "source_issues": len(source), "open": open_count,
            "closed": closed_count, "accepted_succession": count_accepted,
            "direct_cases_excluded": count_direct,
            "live_source_resolvability_verified": False,
            "full_content_mirror_required": False,
            "independent_gate_accepted": False}


def main():
    try:
        report = verify()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("INVALID historical locator:", exc)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
