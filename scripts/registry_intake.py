#!/usr/bin/env python3
"""Fail-closed external-case intake. This is not a RAHP controller or assessment runner."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

REGISTRY = "sankarshanmukhopadhyay/rahp-assessment-registry"
MARKER = re.compile(r"<!-- registry-assessment-key:([^<>\\n]+) -->")
KEY = re.compile(r"^[a-z0-9][a-z0-9:._/-]{7,180}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
URL = "https://api.github.com/repos/" + REGISTRY + "/issues"


class IntakeError(ValueError):
    pass


def validate_event(event):
    if not isinstance(event, dict):
        raise IntakeError("event must be a JSON object")
    if event.get("kind") != "external_assessment":
        raise IntakeError("only externally owned assessment cases are admissible")
    fields = ("assessment_key", "title", "proposition", "source_repository",
              "source_revision", "source_url", "finding_id", "responsible_owner")
    if any(not isinstance(event.get(k), str) or not event[k].strip() for k in fields):
        raise IntakeError("missing mandatory identity, source pin, proposition or owner")
    if not KEY.fullmatch(event["assessment_key"]):
        raise IntakeError("invalid assessment key")
    if not SHA.fullmatch(event["source_revision"]):
        raise IntakeError("source revision must be an immutable commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", event["source_repository"]):
        raise IntakeError("invalid source repository")
    expected = "https://github.com/" + event["source_repository"] + "/"
    if not event["source_url"].startswith(expected):
        raise IntakeError("source URL does not belong to the pinned repository")
    if len(event["title"]) > 240 or len(event["proposition"]) > 4000:
        raise IntakeError("unbounded description")
    if event.get("controller_issue_url"):
        if not event["controller_issue_url"].startswith(
                "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/"):
            raise IntakeError("controller issue must remain at the RAHP controller")
    if event.get("specialist_result") or event.get("assurance_determination"):
        raise IntakeError("intake events must not invent specialist or assurance outcomes")
    return event


def marker(key):
    return f"<!-- registry-assessment-key:{key} -->"


def index_issues(issues):
    index = {}
    for issue in sorted(issues, key=lambda x: int(x.get("number", 0))):
        if "pull_request" in issue:
            continue
        for key in MARKER.findall(issue.get("body") or ""):
            if key in index and index[key]["number"] != issue["number"]:
                raise IntakeError("duplicate existing owner for assessment key")
            index[key] = issue
    return index


def plan(events, issues):
    if not isinstance(events, list) or not events:
        raise IntakeError("intake requires a nonempty event array")
    index = index_issues(issues)
    decisions, seen = [], set()
    for item in events:
        event = validate_event(item)
        key = event["assessment_key"]
        if key in seen:
            raise IntakeError("duplicate assessment key in one batch; consolidate first")
        seen.add(key)
        owner = index.get(key)
        if owner:
            if owner.get("state") != "open":
                raise IntakeError("closed owner requires explicit governed reassessment; no reopening")
            decisions.append({"action": "existing-owner", "assessment_key": key,
                              "number": owner["number"], "url": owner.get("html_url")})
        else:
            decisions.append({"action": "create", "assessment_key": key, "number": None})
    return decisions


def request(method, path, token, payload=None):
    req = urllib.request.Request(
        path, data=json.dumps(payload).encode() if payload is not None else None,
        method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "rahp-registry-intake/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Do not print response body (possibly secret-bearing).
        raise IntakeError(f"GitHub HTTP {exc.code} (intake not acknowledged)") from None


def read_all(token):
    issues = []
    page = 1
    while True:
        data = request("GET", URL + f"?state=all&per_page=100&page={page}", token)
        if not isinstance(data, list):
            raise IntakeError("GitHub issue listing malformed")
        issues.extend(data)
        if len(data) < 100:
            return issues
        page += 1
        if page > 1000:
            raise IntakeError("issue list pagination exceeds bounded limit")


def render_body(event):
    return "\n".join([
        marker(event["assessment_key"]), "",
        "## External assessment proposition", "", event["proposition"], "",
        "## Source and evidence boundary", "",
        "- Repository: `" + event["source_repository"] + "`",
        "- Revision: `" + event["source_revision"] + "`",
        "- Source: " + event["source_url"],
        "- Finding ID: `" + event["finding_id"] + "`",
        "- Responsible external owner: " + event["responsible_owner"],
        *(["- RAHP controller anchor (execution only): " + event["controller_issue_url"]]
          if event.get("controller_issue_url") else []),
        "", "## Intake limitation", "",
        "Intake is an administrative routing record, not an executed RAHP assessment. "
        "Evidence, privacy and runtime assurance remain unverified unless separately "
        "supported by attributable source-pinned results. No PASS is asserted.",
        "",
    ])


def execute(events, token, *, dry_run=True, issue_snapshot=None):
    issues = read_all(token) if issue_snapshot is None else issue_snapshot
    decisions = plan(events, issues)  # Validate entire batch before any write.
    if dry_run:
        return decisions
    # Explicitly refuse creating an execution/controller anchor in this registry.
    by_key = {e["assessment_key"]: e for e in events}
    output = []
    for item in decisions:
        if item["action"] == "existing-owner":
            output.append(item)
            continue
        event = by_key[item["assessment_key"]]
        created = request("POST", URL, token, {
            "title": event["title"], "body": render_body(event),
            "assignees": ["sankarshanmukhopadhyay"],
        })
        output.append({"action": "created", "assessment_key": item["assessment_key"],
                       "number": created["number"], "url": created["html_url"]})
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--issue-snapshot", type=Path, help="offline issue list for dry-run validation")
    p.add_argument("--apply", action="store_true", help="explicitly allow registry GitHub issue writes")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    events = json.loads(args.events.read_text(encoding="utf-8"))
    if args.issue_snapshot and args.apply:
        raise SystemExit("cannot apply against a supplied offline issue snapshot")
    token = os.getenv("REGISTRY_INTAKE_TOKEN", "")
    if not args.issue_snapshot and not token:
        raise SystemExit("REGISTRY_INTAKE_TOKEN required to verify live registry owners")
    snapshot = json.loads(args.issue_snapshot.read_text()) if args.issue_snapshot else None
    decisions = execute(events, token, dry_run=not args.apply, issue_snapshot=snapshot)
    output = json.dumps({"mode": "apply" if args.apply else "dry-run",
                         "decisions": decisions}, indent=2) + "\n"
    if args.out:
        args.out.write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
