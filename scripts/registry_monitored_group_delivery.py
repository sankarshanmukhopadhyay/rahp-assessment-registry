#!/usr/bin/env python3
"""Guarded Registry successor for the exact approved four-finding DTG group.

Never creates a Registry owner before a live matching Toolkit group
reservation and source-bound maintainer acceptance. Issue POST is acknowledged
only by authoritative re-read, including timeout-after-commit recovery.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import qualify_monitored_group_intent as contract
import qualify_monitored_owner as owners
import registry_intake as intake
import verify_maintainer_cutover_acceptance as approval

REG = intake.REGISTRY
TK = owners.TOOLKIT
API = "https://api.github.com/repos/"
INTENT_PATH = "outbox/pending/spec-dependency-2026-11-16.json"
LEDGER = "instances/dtg/registry-transfers.json"
MARK = "<!-- rahp-registry-monitored-group:v1:"

class DeliveryError(ValueError):
    pass

def read_head(fetch, repo):
    entry = fetch(API + repo + "/branches/main")
    sha = ((entry or {}).get("commit") or {}).get("sha")
    if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{40}", sha):
        raise DeliveryError("unavailable main revision for " + repo)
    return sha

def read_pinned(fetch, repo, path, sha):
    response = fetch(API + repo + "/contents/" + path + "?ref=" + sha)
    if not isinstance(response, dict) or response.get("encoding") != "base64":
        raise DeliveryError("committed contract unavailable: " + path)
    try:
        return json.loads(base64.b64decode(response["content"]).decode("utf-8"))
    except (KeyError, TypeError, ValueError) as exc:
        raise DeliveryError("invalid committed JSON: " + path) from exc

def issues(fetch, repo, state="all"):
    result = []
    for page in range(1, 101):
        batch = fetch(API + repo + "/issues?state=" + state +
                      "&per_page=100&page=" + str(page))
        if not isinstance(batch, list):
            raise DeliveryError("incomplete live issue inventory for " + repo)
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise DeliveryError("issue inventory pagination bound exceeded")

def require_reservation(ledger, intent):
    if (not isinstance(ledger, dict) or set(ledger) != {"schema", "transfers"}
            or ledger.get("schema") != "rahp-registry-transfers/v1"
            or not isinstance(ledger.get("transfers"), list)):
        raise DeliveryError("invalid Toolkit transfer ledger")
    expected = {"state": "reserved_group",
                "assessment_key": intent["assessment_key"],
                "toolkit_issue_url": intent["toolkit_current_issue_url"],
                "registry_intent_path": INTENT_PATH,
                "monitor_revision": intent["monitor_revision"],
                "snapshot_date": intent["snapshot_date"],
                "finding_ids": intent["source_finding_ids"],
                "group_sha256": intent["source_group_sha256"]}
    matches = [x for x in ledger["transfers"] if isinstance(x, dict)
               and x.get("assessment_key") == intent["assessment_key"]]
    if matches != [expected]:
        raise DeliveryError("exact Toolkit reserved_group writer fence missing")
    return expected

def body(intent):
    return "\n".join([
        intake.marker(intent["assessment_key"]),
        MARK + intent["source_group_sha256"] + " -->", "",
        "# DTG specification-dependency: Registry administrative successor", "",
        "Monitor commit: " + intent["monitor_revision"],
        "Snapshot date: " + intent["snapshot_date"],
        "Original source: " + intent["source_repository"],
        "Canonical event SHA-256: " + intent["source_group_sha256"],
        "Source evidence SHA-256: " + intent["source_evidence_sha256"],
        *["Finding: " + x for x in intent["source_finding_ids"]],
        "Original Toolkit owner: " + intent["toolkit_current_issue_url"],
        "Historical wrapper: " + intent["toolkit_historical_issue_url"],
        *["Separate residual: " + x for x in intent["protected_issue_urls"]], "",
        "Registry administrative ownership does not import RAHP assurance.",
        "Toolkit retains canonical execution authority. No specialist return,",
        "current-observation delivery acknowledgment, independent assurance,",
        "source-specific Toolkit cutover or PASS is established.", ""
    ])

def lookup(known, intent):
    found = intake.index_issues(known).get(intent["assessment_key"])
    if found is None:
        return None
    if found.get("state") != "open" or not isinstance(found.get("number"), int):
        raise DeliveryError("existing Registry owner closed or malformed")
    if found.get("html_url") != "https://github.com/" + REG + "/issues/" + str(found["number"]):
        raise DeliveryError("Registry owner identity mismatch")
    text = found.get("body") or ""
    if MARK + intent["source_group_sha256"] + " -->" not in text:
        raise DeliveryError("existing owner has different event digest")
    for fid in intent["source_finding_ids"]:
        if "Finding: " + fid not in text:
            raise DeliveryError("existing owner lacks required finding")
    for link in [intent["toolkit_current_issue_url"],
                 intent["toolkit_historical_issue_url"], *intent["protected_issue_urls"]]:
        if link not in text:
            raise DeliveryError("existing owner omits protected obligation")
    return found

def qualify(intent, group, candidate, comments, ledger, registry, toolkit_open):
    decision = approval.evaluate(candidate, comments)
    if decision["status"] != "accepted":
        raise DeliveryError("source-scope maintainer decision absent or withdrawn")
    contract.qualify(intent, group, candidate, decision)
    require_reservation(ledger, intent)
    active = [x for x in toolkit_open if isinstance(x, dict)
              and x.get("state") == "open" and "pull_request" not in x
              and owners.MARKER in (x.get("body") or "")]
    if len(active) != 1 or active[0].get("number") != 272:
        raise DeliveryError("ambiguous active Toolkit owner")
    return lookup(registry, intent), decision

def require_write_context(env):
    if (env.get("GITHUB_ACTIONS") != "true"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_REPOSITORY") != REG
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"):
        raise DeliveryError("write requires main-only serialized workflow_dispatch")

def deliver(intent, group, candidate, token, *, apply=False, fetch=None, post=None):
    if not token:
        raise DeliveryError("GitHub token required")
    if apply:
        require_write_context(os.environ)
    fetch = fetch or (lambda url: intake.request("GET", url, token))
    post = post or (lambda payload: intake.request("POST", intake.URL, token, payload))
    reg_sha, toolkit_sha = read_head(fetch, REG), read_head(fetch, TK)
    if read_pinned(fetch, REG, INTENT_PATH, reg_sha) != intent:
        raise DeliveryError("intent differs from committed Registry main")
    ledger = read_pinned(fetch, TK, LEDGER, toolkit_sha)
    before, decision = qualify(
        intent, group, candidate, approval.full_comments(token, fetch=fetch),
        ledger, issues(fetch, REG), issues(fetch, TK, "open"))
    if read_head(fetch, REG) != reg_sha or read_head(fetch, TK) != toolkit_sha:
        raise DeliveryError("main changed during qualification")
    receipt = {"schema": "rahp-registry-group-delivery/v1",
               "assessment_key": intent["assessment_key"],
               "source_group_sha256": intent["source_group_sha256"],
               "maintainer_comment": decision["decision_comment_url"],
               "state": "owner_observed" if before else "ready_for_delivery",
               "owner_url": before.get("html_url") if before else None,
               "mode": "apply" if apply else "read_only",
               "current_observation_acknowledged": False,
               "controller_reconciled": False, "toolkit_writer_switch": False,
               "assurance_determination": None, "cutover_authorized": False}
    if not apply or before:
        return receipt
    response, error = None, None
    try:
        response = post({"title": "DTG: Trust Tasks dependency group Registry successor",
                         "body": body(intent), "assignees": ["sankarshanmukhopadhyay"]})
    except Exception as exc:
        error = exc
    after = lookup(issues(fetch, REG), intent)
    if after is None:
        raise DeliveryError("POST not acknowledged after authoritative re-read") from error
    if response is not None and (
            not isinstance(response, dict) or response.get("number") != after["number"]
            or response.get("html_url") != after["html_url"]):
        raise DeliveryError("POST disagrees with authoritative case owner")
    if read_head(fetch, REG) != reg_sha or read_head(fetch, TK) != toolkit_sha:
        raise DeliveryError("source authority changed during owner publication")
    return {**receipt, "state": "owner_observed", "owner_url": after["html_url"],
            "recovered_after_ambiguous_post": error is not None}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "combined", "candidate", "receipt"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    result = {"schema": "rahp-registry-group-delivery/v1",
              "state": "indeterminate", "assurance_determination": None}
    try:
        intent = json.loads(args.manifest.read_text())
        events = json.loads(args.combined.read_text())
        match = [x for x in events if isinstance(x, dict)
                 and x.get("assessment_key") == intent["assessment_key"]]
        if len(match) != 1:
            raise DeliveryError("group source observation ambiguous")
        candidate = json.loads(args.candidate.read_text())
        result = deliver(intent, match[0], candidate,
                         os.environ.get("REGISTRY_INTAKE_TOKEN", ""), apply=args.apply)
    except (OSError, ValueError, TypeError, KeyError, intake.IntakeError,
            approval.MaintainerScopeError) as exc:
        result["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result["state"] == "indeterminate":
        print("BLOCKED source-qualified Registry group handoff", file=sys.stderr)
        return 1
    print("Group successor:", result["state"], "(not RAHP assurance)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
