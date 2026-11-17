#!/usr/bin/env python3
"""Qualify an exact monitored owner candidate without changing authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
import registry_intake as intake

ROOT = Path(__file__).resolve().parents[1]
KEY = "dtg:portfolio:combined:spec-dependency-alignment"
MARKER = "<!-- rahp-assessment-key:" + KEY + " -->"
MONITOR_SHA = "7e2813c8daf867a21e4064513cc83612726aeb44"
TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
URL = "https://github.com/" + TOOLKIT + "/issues/"

class CandidateError(ValueError):
    pass

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()

def qualify(spec, events, evidence, owner, historical, protected, registry_issues, open_toolkit_issues):
    required = {"schema", "key", "monitor_revision", "snapshot_date",
                "repository", "finding_ids", "active_toolkit_issue",
                "historical_toolkit_issue", "protected_toolkit_issues",
                "status", "independent_review_accepted", "registry_owner_accepted",
                "toolkit_writer_exclusion_accepted"}
    if not isinstance(spec, dict) or set(spec) != required or any([
        spec["schema"] != "rahp-registry-monitored-owner-candidate/v1",
        spec["key"] != KEY, spec["monitor_revision"] != MONITOR_SHA,
        spec["snapshot_date"] != "2026-11-16",
        spec["repository"] != "trustoverip/dtgwg-trust-tasks-tf",
        spec["active_toolkit_issue"] != 272,
        spec["historical_toolkit_issue"] != 615,
        spec["protected_toolkit_issues"] != [282, 826, 837],
        spec["status"] != "candidate_only",
        spec["independent_review_accepted"] is not False,
        spec["registry_owner_accepted"] is not False,
        spec["toolkit_writer_exclusion_accepted"] is not False,
    ]):
        raise CandidateError("candidate source, owners or authorization changed")
    ids = spec["finding_ids"]
    if (not isinstance(ids, list) or len(ids) != 4 or ids != sorted(set(ids))
            or not all(isinstance(i, str) and re.fullmatch("[0-9a-f]{20}", i) for i in ids)):
        raise CandidateError("expected four distinct sorted source finding IDs")
    if not isinstance(events, list):
        raise CandidateError("canonical grouped events missing")
    matches = [x for x in events if isinstance(x, dict) and x.get("assessment_key") == KEY]
    if len(matches) != 1:
        raise CandidateError("exactly one source group required")
    event = matches[0]
    observations = event.get("source_observations")
    if (not isinstance(observations, list) or len(observations) != 4
            or sorted(x.get("finding_id") for x in observations if isinstance(x, dict)) != ids
            or any(x.get("repository") != spec["repository"] for x in observations)):
        raise CandidateError("source group does not match all four monitored findings")
    if (not isinstance(evidence, dict) or
            evidence.get("schema") != "rahp-registry-release-tag-source-qualification/v1"
            or evidence.get("verification") != "live-annotated-tag-reference-and-object"
            or evidence.get("cutover_authorized") is not False
            or evidence.get("ownership_transfer_accepted") is not False):
        raise CandidateError("source evidence was not qualified")
    qualification = evidence.get("group_source_qualification") or {}
    groups = qualification.get("groups") if isinstance(qualification, dict) else None
    if (not isinstance(groups, list) or
            qualification.get("source_provenance_qualified") is not True or
            qualification.get("cutover_authorized") is not False):
        raise CandidateError("whole-group coverage is not qualified")
    verified = [x for x in groups if isinstance(x, dict) and x.get("assessment_key") == KEY]
    if (len(verified) != 1 or verified[0].get("finding_count") != 4
            or verified[0].get("observed_commit_findings") != 1
            or verified[0].get("supplemental_annotated_tag_findings") != 3
            or verified[0].get("case_owner_accepted") is not False):
        raise CandidateError("source coverage or owner claims differ")
    for issue, number, state in ((owner, 272, "open"), (historical, 615, "closed")):
        if (not isinstance(issue, dict) or issue.get("number") != number
                or issue.get("html_url") != URL + str(number)
                or issue.get("state") != state or "pull_request" in issue
                or MARKER not in (issue.get("body") or "")):
            raise CandidateError("live Toolkit owner or historical wrapper differs")
    body = owner.get("body") or ""
    if any(("finding=" + fid not in body and "@" + fid not in body
            and chr(96) + fid + chr(96) not in body) for fid in ids):
        raise CandidateError("active Toolkit issue missing a grouped finding")
    if (not isinstance(protected, list) or len(protected) != 3 or
            any(not isinstance(x, dict) or x.get("number") != number or
                x.get("html_url") != URL + str(number) or
                x.get("state") not in ("open", "closed") or "pull_request" in x
                for x, number in zip(protected, (282, 826, 837)))):
        raise CandidateError("protected independent residual issue unavailable")
    if not isinstance(open_toolkit_issues, list):
        raise CandidateError("complete live Toolkit open-issue inventory required")
    active = []
    for entry in open_toolkit_issues:
        if not isinstance(entry, dict):
            raise CandidateError("malformed Toolkit issue inventory")
        if "pull_request" in entry:
            continue
        if entry.get("state") != "open" or not isinstance(entry.get("number"), int):
            raise CandidateError("Toolkit active issue inventory is not open-only")
        if MARKER in (entry.get("body") or ""):
            active.append(entry)
    if (len(active) != 1 or active[0].get("number") != 272 or
            active[0].get("html_url") != owner["html_url"]):
        raise CandidateError("multiple, missing or changed open Toolkit assessment-key owners")
    if not isinstance(registry_issues, list):
        raise CandidateError("complete Registry owner snapshot required")
    index = intake.index_issues(registry_issues)
    if KEY in index:
        raise CandidateError("Registry key already owned; reconcile instead of new transfer")
    return {
        "schema": "rahp-registry-monitored-owner-candidate-receipt/v1",
        "key": KEY, "candidate_sha256": digest(spec),
        "source_group_sha256": digest(event),
        "source_evidence_sha256": digest(evidence),
        "finding_ids": ids,
        "active_toolkit_issue": URL + "272",
        "historical_toolkit_issue": URL + "615",
        "protected_residuals": [URL + str(n) for n in (282, 826, 837)],
        "current_source_qualified": True,
        "live_toolkit_owner_observed": True,
        "registry_key_unclaimed_when_checked": True,
        "independent_review_accepted": False,
        "registry_owner_accepted": False,
        "current_observation_acknowledged": False,
        "toolkit_writers_fenced": False,
        "consumer_migration_qualified": False,
        "cutover_authorized": False,
    }

def all_open_toolkit_issues(token, *, fetch=None):
    """Read all open issues; pagination absence or API failure cannot prove uniqueness."""
    fetch = fetch or (lambda url: intake.request("GET", url, token))
    collected = []
    for page in range(1, 101):
        url = ("https://api.github.com/repos/" + TOOLKIT +
               "/issues?state=open&per_page=100&page=" + str(page))
        rows = fetch(url)
        if not isinstance(rows, list):
            raise CandidateError("Toolkit open-owner inventory unavailable")
        collected.extend(rows)
        if len(rows) < 100:
            return collected
    raise CandidateError("Toolkit open-owner inventory exceeds bounded pagination")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--combined", required=True, type=Path)
    p.add_argument("--evidence", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN")
        if not token:
            raise CandidateError("GitHub read token required")
        spec = json.loads(args.candidate.read_text(encoding="utf-8"))
        events = json.loads(args.combined.read_text(encoding="utf-8"))
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        def read(num):
            return intake.request("GET", "https://api.github.com/repos/" +
                                  TOOLKIT + "/issues/" + str(num), token)
        output = qualify(spec, events, evidence, read(272), read(615),
                         [read(n) for n in (282, 826, 837)], intake.read_all(token),
                         all_open_toolkit_issues(token))
    except (OSError, ValueError, KeyError, TypeError, intake.IntakeError) as exc:
        print("UNQUALIFIED monitored owner:", exc, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("Qualified candidate only; zero ownership or publication effects")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
