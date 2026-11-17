#!/usr/bin/env python3
"""Read-only audit of source findings, generated publication keys, and Toolkit owner."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
import registry_intake
from registry_materiality_intake import checked_source, GIT_COMMIT

URL = "https://api.github.com/repos/sankarshanmukhopadhyay/rahp-toolkit/issues/"
ROW = re.compile(r"^\|\s*\x60([0-9a-f]{20})\x60\s*\|", re.M)
MARKER = re.compile(r"<!-- rahp-assessment-key:([^<>]+) -->")


class LineageError(ValueError):
    pass


def group_keys(routed, combined, dpip):
    groups = {}
    for item in routed:
        if item["outcome"] in ("combined", "dpip"):
            groups.setdefault((item["outcome"], item["rule_id"]), set()).add(
                item["finding"]["finding_id"])
    keys = {}
    for kind, events in (("combined", combined), ("dpip", dpip)):
        if not isinstance(events, list):
            raise LineageError("generated events must be arrays")
        for event in events:
            if not isinstance(event, dict):
                raise LineageError("invalid publication event")
            ids = ROW.findall(event.get("body") or "")
            key = event.get("assessment_key")
            if not ids or len(ids) != len(set(ids)) or not isinstance(key, str) or not key:
                raise LineageError("missing or ambiguous publication identity")
            matches = [g for g, members in groups.items()
                       if g[0] == kind and members == set(ids)]
            if len(matches) != 1 or matches[0] in keys:
                raise LineageError("publication event does not uniquely match a routed group")
            keys[matches[0]] = key
    if set(keys) != set(groups) or len(set(keys.values())) != len(keys):
        raise LineageError("missing or duplicate generated publication event")
    return keys


def qualify(candidate, findings, routed, combined, dpip, issue, comments):
    if (not isinstance(candidate, dict)
            or set(candidate) != {"schema", "toolkit_owner_issue", "finding_ids"}
            or candidate["schema"] != "rahp-toolkit-transfer-candidate/v1"):
        raise LineageError("unrecognized candidate schema")
    ids = candidate["finding_ids"]
    if (not isinstance(ids, list) or not ids
            or any(not isinstance(x, str) or not re.fullmatch(r"[0-9a-f]{20}", x)
                   for x in ids) or len(set(ids)) != len(ids)):
        raise LineageError("invalid or duplicate candidate finding")
    num = candidate["toolkit_owner_issue"]
    if (type(num) is not int or num <= 0 or not isinstance(issue, dict)
            or issue.get("number") != num or issue.get("state") != "open"
            or issue.get("html_url") !=
                f"https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/{num}"):
        raise LineageError("invalid verified candidate owner")
    if not isinstance(comments, list) or any(
            not isinstance(x, dict) or not isinstance(x.get("body"), str)
            for x in comments):
        raise LineageError("malformed owner comments")
    checked_source(findings, routed)
    keys = group_keys(routed, combined, dpip)
    by_id = {x["finding_id"]: x for x in findings}
    by_route = {x["finding"]["finding_id"]: x for x in routed}
    texts = [issue.get("body") or ""] + [x["body"] for x in comments]
    owner_keys = set(MARKER.findall(issue.get("body") or ""))
    records = []
    for fid in ids:
        finding = by_id.get(fid)
        route = by_route.get(fid)
        pins = []
        for url in (finding or {}).get("evidence_urls") or []:
            match = GIT_COMMIT.fullmatch(url) if isinstance(url, str) else None
            if match and match.group(1) == finding.get("repository"):
                pins.append(match.group(2))
        key = (keys.get((route["outcome"], route["rule_id"]))
               if route and route["outcome"] in ("combined", "dpip") else None)
        mentioned = any(re.search(r"(?<![0-9a-f])" + fid + r"(?![0-9a-f])", s)
                        for s in texts)
        blockers = []
        if finding is None:
            blockers.append("source_finding_absent")
        if route is None:
            blockers.append("source_not_routed")
        if not pins:
            blockers.append("immutable_source_commit_absent")
        if not mentioned:
            blockers.append("candidate_owner_does_not_reference_finding")
        if key and key not in owner_keys:
            blockers.append("generated_publisher_key_not_bound_to_candidate_issue")
        records.append({
            "finding_id": fid,
            "source_repository": finding.get("repository") if finding else None,
            "commit_pins": sorted(set(pins)),
            "route_outcome": route["outcome"] if route else None,
            "route_rule": route["rule_id"] if route else None,
            "publisher_key": key,
            "issue_text_reference": bool(mentioned),
            "owner_has_exact_publisher_marker": bool(key and key in owner_keys),
            "blockers": blockers,
        })
    return {
        "schema": "rahp-toolkit-transfer-lineage-shadow/v1",
        "candidate_owner_issue": num,
        "findings": records,
        "candidate_finding_count": len(records),
        "source_observed_count": sum(r["source_repository"] is not None for r in records),
        "no_commit_pin_count": sum(not r["commit_pins"] for r in records),
        "unbound_publisher_key_count": sum(
            r["publisher_key"] is not None and not r["owner_has_exact_publisher_marker"]
            for r in records),
        "authority_transfer_accepted": False,
        "publisher_suppression_active": False,
        "cutover_authorized": False,
        "issue_writes": 0,
    }


def live_owner(number, token):
    if not token:
        raise LineageError("read-only GitHub token required")
    issue = registry_intake.request("GET", URL + str(number), token)
    comments = []
    for page in range(1, 101):
        batch = registry_intake.request(
            "GET", URL + f"{number}/comments?per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise LineageError("invalid comment listing")
        comments.extend(batch)
        if len(batch) < 100:
            return issue, comments
    raise LineageError("comments pagination limit exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("candidate", "findings", "routing", "combined", "dpip", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    try:
        candidate, findings, routed, combined, dpip = [
            json.loads(getattr(args, field).read_text(encoding="utf-8"))
            for field in ("candidate", "findings", "routing", "combined", "dpip")]
        issue, comments = live_owner(
            candidate["toolkit_owner_issue"], os.environ.get("REGISTRY_INTAKE_TOKEN", ""))
        receipt = qualify(candidate, findings, routed, combined, dpip, issue, comments)
    except (OSError, ValueError, TypeError, KeyError, registry_intake.IntakeError) as exc:
        print("INVALID candidate lineage:", exc, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("Read-only candidate observation:", receipt["source_observed_count"],
          "findings,", receipt["no_commit_pin_count"], "without immutable commit pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
