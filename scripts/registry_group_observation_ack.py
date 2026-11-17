#!/usr/bin/env python3
"""Durably acknowledge one qualified Registry-owned monitored observation.

The acknowledgment is a GitHub issue comment made by the controlled Registry
publisher; it is not a controller or specialist return or an assurance PASS.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as intake
import registry_monitored_group_delivery as group

REG = intake.REGISTRY
API = "https://api.github.com/repos/"
PREFIX = "<!-- rahp-registry-observation:v1:"
SHA = re.compile(r"^[0-9a-f]{64}$")

class AckError(ValueError):
    pass

def comments(issue, get):
    rows = []
    for page in range(1, 101):
        part = get(API + REG + "/issues/" + str(issue) +
                   "/comments?per_page=100&page=" + str(page))
        if not isinstance(part, list):
            raise AckError("incomplete Registry observation comment history")
        rows.extend(part)
        if len(part) < 100:
            return rows
    raise AckError("Registry observation history exceeds pagination bound")

def authorized(item):
    if not isinstance(item, dict) or not isinstance(item.get("user"), dict):
        return False
    actor = item["user"]
    return (actor.get("login") == "github-actions[bot]" and actor.get("type") == "Bot"
            or actor.get("login") == "sankarshanmukhopadhyay"
            and item.get("author_association") == "OWNER")

def observed(rows, issue, digest):
    if not SHA.fullmatch(digest):
        raise AckError("invalid source observation digest")
    marker = PREFIX + digest + " -->"
    recognized = [c for c in rows if isinstance(c, dict)
                  and marker in (c.get("body") or "")]
    if not recognized:
        return None
    if len(recognized) != 1 or not authorized(recognized[0]):
        raise AckError("missing unique authenticated source acknowledgment")
    c = recognized[0]
    number = c.get("id")
    expected = ("https://github.com/" + REG + "/issues/" + str(issue) +
                "#issuecomment-" + str(number))
    if type(number) is not int or number < 1 or c.get("html_url") != expected:
        raise AckError("source acknowledgment has invalid GitHub comment identity")
    return c

def acknowledge(intent, event, candidate, token, *, apply=False, get=None, post=None):
    if not token:
        raise AckError("GitHub API token required")
    if apply:
        group.require_write_context(os.environ)
    get = get or (lambda url: intake.request("GET", url, token))
    owner = group.deliver(intent, event, candidate, token,
                          apply=False, fetch=get,
                          post=lambda _: (_ for _ in ()).throw(AckError("no issue writes")))
    if owner["state"] != "owner_observed":
        raise AckError("Registry successor must exist before observation acknowledgment")
    url = owner["owner_url"]
    number = int(url.rsplit("/", 1)[1])
    sha = intent["source_group_sha256"]
    old = observed(comments(number, get), number, sha)
    result = {"schema": "rahp-registry-source-observation-ack/v1",
              "assessment_key": intent["assessment_key"],
              "source_group_sha256": sha,
              "registry_issue_url": url,
              "state": "observed" if old else "pending",
              "comment_url": old.get("html_url") if old else None,
              "mode": "apply" if apply else "read_only",
              "current_observation_acknowledged": old is not None,
              "toolkit_publication_switched": False,
              "controller_reconciliation_executed": False,
              "assurance_determination": None, "cutover_authorized": False}
    if not apply or old:
        return result
    post = post or (lambda body: intake.request(
        "POST", API + REG + "/issues/" + str(number) + "/comments",
        token, {"body": body}))
    failure, response = None, None
    try:
        response = post(PREFIX + sha + " -->\n\n" +
            "Registry monitored source observation received for administrative case " + url +
            ". The four-finding source digest is checked against the committed Monitor " +
            "observation and maintained Toolkit group reservation. No RAHP assurance, " +
            "specialist return or Toolkit publisher cutover is asserted.")
    except Exception as exc:
        failure = exc
    actual = observed(comments(number, get), number, sha)
    if actual is None:
        raise AckError("POST did not yield a durable authenticated observation comment") from failure
    if response is not None and (
            not isinstance(response, dict) or response.get("id") != actual.get("id")
            or response.get("html_url") != actual.get("html_url")):
        raise AckError("POST response disagrees with authoritative observation comment")
    return {**result, "state": "observed", "comment_url": actual["html_url"],
            "current_observation_acknowledged": True,
            "recovered_after_ambiguous_post": failure is not None}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "combined", "candidate", "receipt"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    output = {"schema": "rahp-registry-source-observation-ack/v1",
              "state": "indeterminate", "assurance_determination": None}
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        events = json.loads(args.combined.read_text(encoding="utf-8"))
        matches = [x for x in events if isinstance(x, dict)
                   and x.get("assessment_key") == manifest["assessment_key"]]
        if len(matches) != 1:
            raise AckError("canonical grouped source is ambiguous")
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        output = acknowledge(manifest, matches[0], candidate,
                             os.getenv("REGISTRY_INTAKE_TOKEN", ""), apply=args.apply)
    except (OSError, ValueError, TypeError, KeyError, intake.IntakeError) as exc:
        output["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    if output["state"] == "indeterminate":
        print("BLOCKED Registry source observation acknowledgment", file=sys.stderr)
        return 1
    print("Registry source observation:", output["state"], "(not assurance)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
