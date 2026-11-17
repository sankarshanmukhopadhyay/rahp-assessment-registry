#!/usr/bin/env python3
"""Read a scoped maintainer disposition for the #272 migration candidate.

A GitHub issue comment from the repository owner may approve or withdraw
governance *scope* acceptance. It cannot grant publication, independent
assurance, specialist authorization or cross-repository writer exclusivity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as intake

REGISTRY = "sankarshanmukhopadhyay/rahp-assessment-registry"
TRACKER = 11
MAINTAINER = "sankarshanmukhopadhyay"
KEY = "dtg:portfolio:combined:spec-dependency-alignment"
MARKER = re.compile(
    r"<!-- rahp-registry-maintainer-scope:v1:(accept|withdraw):([0-9a-f]{64}) -->"
)
SHA = re.compile(r"^[0-9a-f]{64}$")


class MaintainerScopeError(ValueError):
    pass


def canonical_digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()


def scope(receipt):
    """Bind actual as-of qualification, not just the group name or issue number."""
    if not isinstance(receipt, dict) or receipt.get("schema") != (
            "rahp-registry-monitored-owner-candidate-receipt/v1"):
        raise MaintainerScopeError("verified owner candidate receipt required")
    for field in ("candidate_sha256", "source_group_sha256", "source_evidence_sha256"):
        if not isinstance(receipt.get(field), str) or not SHA.fullmatch(receipt[field]):
            raise MaintainerScopeError("missing immutable qualified evidence: " + field)
    if (receipt.get("key") != KEY or receipt.get("active_toolkit_issue") !=
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/272"
            or receipt.get("historical_toolkit_issue") !=
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/615"
            or receipt.get("protected_residuals") != [
                "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/" + str(n)
                for n in (282, 826, 837)]):
        raise MaintainerScopeError("candidate identity or protected obligations changed")
    finding_ids = receipt.get("finding_ids")
    if (not isinstance(finding_ids, list) or len(finding_ids) != 4
            or finding_ids != sorted(set(finding_ids))):
        raise MaintainerScopeError("unqualified finding membership")
    for assertion in ("current_source_qualified", "live_toolkit_owner_observed",
                      "registry_key_unclaimed_when_checked"):
        if receipt.get(assertion) is not True:
            raise MaintainerScopeError("positive candidate requirement absent: " + assertion)
    for assertion in ("independent_review_accepted", "registry_owner_accepted",
                      "current_observation_acknowledged", "toolkit_writers_fenced",
                      "consumer_migration_qualified", "cutover_authorized"):
        if receipt.get(assertion) is not False:
            raise MaintainerScopeError("candidate receipt illegally asserts authority: " + assertion)
    return canonical_digest({
        "schema": "rahp-registry-maintainer-cutover-scope/v1",
        "key": receipt["key"],
        "candidate_sha256": receipt["candidate_sha256"],
        "source_group_sha256": receipt["source_group_sha256"],
        "source_evidence_sha256": receipt["source_evidence_sha256"],
        "finding_ids": finding_ids,
        "active_toolkit_issue": receipt["active_toolkit_issue"],
        "historical_toolkit_issue": receipt["historical_toolkit_issue"],
        "protected_residuals": receipt["protected_residuals"],
    })


def evaluate(receipt, comments):
    scope_sha = scope(receipt)
    if not isinstance(comments, list):
        raise MaintainerScopeError("complete issue comment history unavailable")
    decisions = []
    for c in comments:
        if not isinstance(c, dict):
            raise MaintainerScopeError("invalid issue comment")
        body = c.get("body") or ""
        if not isinstance(body, str):
            raise MaintainerScopeError("non-text issue comment")
        markers = MARKER.findall(body)
        scoped = [(action, sha) for action, sha in markers if sha == scope_sha]
        if not scoped:
            continue
        if len(markers) != 1 or len(scoped) != 1:
            raise MaintainerScopeError("ambiguous maintainer scope marker")
        actor = c.get("user")
        if (not isinstance(actor, dict) or actor.get("login") != MAINTAINER
                or c.get("author_association") != "OWNER"):
            raise MaintainerScopeError("scope disposition is not from repository maintainer")
        number = c.get("id")
        expected = ("https://github.com/" + REGISTRY + "/issues/" + str(TRACKER)
                    + "#issuecomment-" + str(number))
        if type(number) is not int or number <= 0 or c.get("html_url") != expected:
            raise MaintainerScopeError("scope decision is not bound to live tracker comment")
        decisions.append((number, scoped[0][0], c["html_url"]))
    if len({number for number, _, _ in decisions}) != len(decisions):
        raise MaintainerScopeError("duplicate live comment identity")
    decisions.sort()
    state = ("pending" if not decisions else
             "accepted" if decisions[-1][1] == "accept" else "withdrawn")
    return {
        "schema": "rahp-registry-maintainer-scope-status/v1",
        "assessment_key": KEY,
        "scope_sha256": scope_sha,
        "status": state,
        "decision_comment_url": decisions[-1][2] if decisions else None,
        "expected_accept_marker":
            "<!-- rahp-registry-maintainer-scope:v1:accept:" + scope_sha + " -->",
        "maintainer": MAINTAINER,
        "acceptance_kind": "repository_maintainer_governance",
        "independent_review_claimed": False,
        "source_and_owner_qualifier_required": True,
        "registry_owner_created": False,
        "current_observation_acknowledged": False,
        "toolkit_writer_suppression_authorized": False,
        "cutover_authorized": False,
    }


def full_comments(token, fetch=None):
    if fetch is None:
        fetch = lambda url: intake.request("GET", url, token)
    all_rows = []
    for page in range(1, 101):
        url = ("https://api.github.com/repos/" + REGISTRY + "/issues/" +
               str(TRACKER) + "/comments?per_page=100&page=" + str(page))
        rows = fetch(url)
        if not isinstance(rows, list):
            raise MaintainerScopeError("incomplete tracker comment page")
        all_rows.extend(rows)
        if len(rows) < 100:
            return all_rows
    raise MaintainerScopeError("tracker decision history exceeds pagination limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-receipt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--require-accepted", action="store_true")
    args = parser.parse_args()
    try:
        token = os.getenv("REGISTRY_INTAKE_TOKEN")
        if not token:
            raise MaintainerScopeError("read-only GitHub token required")
        receipt = json.loads(args.candidate_receipt.read_text(encoding="utf-8"))
        result = evaluate(receipt, full_comments(token))
        if args.require_accepted and result["status"] != "accepted":
            raise MaintainerScopeError("exact current scope lacks maintainer acceptance")
    except (OSError, ValueError, KeyError, TypeError, intake.IntakeError) as exc:
        print("UNQUALIFIED maintainer scope:", exc, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("Maintainer governance scope:", result["status"], "(not cutover authority)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
