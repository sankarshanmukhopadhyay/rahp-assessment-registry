#!/usr/bin/env python3
"""Replay source-controlled Registry intake intents; never write Toolkit issues."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import sys
from pathlib import Path
import registry_intake as intake


class DeliveryError(ValueError):
    pass


def require_event(value):
    if not isinstance(value, dict) or value.get("schema") != "rahp-registry-pending-intake/v1":
        raise DeliveryError("unknown outbox manifest schema")
    if set(value) != {"schema", "event"}:
        raise DeliveryError("unreviewed outbox manifest fields")
    return intake.validate_event(value["event"])


def owner_for(event, issues):
    if "source_routing_key" in event:
        routing = event["source_routing_key"]
        key_marker = intake.marker(event["assessment_key"])
        for issue in issues:
            if "pull_request" in issue:
                continue
            body = issue.get("body") or ""
            source_keys = re.findall(r"<!-- rahp-registry-source-routing:([^<>\n]+) -->", body)
            source_keys.extend(intake.MARKER.findall(body))
            matches = (
                routing in source_keys
                or any(intake.routing_alias(k, routing) for k in source_keys)
                or "<!-- rahp-registry-case:" + event["case_id"] + " -->" in body
                or "<!-- rahp-registry-monitored-evidence:sha256:" + event["source_evidence_sha256"] + " -->" in body
            )
            if matches and key_marker not in body:
                raise DeliveryError("conflicting Registry source lineage, case or evidence owner")
    decisions = intake.plan([event], issues)
    if len(decisions) != 1:
        raise DeliveryError("ambiguous source event planning")
    decision = decisions[0]
    if decision["action"] == "existing-owner":
        matching = [i for i in issues if i.get("number") == decision["number"] and "pull_request" not in i]
        if len(matching) != 1:
            raise DeliveryError("existing owner is missing or ambiguous")
        body = matching[0].get("body") or ""
        if event.get("case_id") and (
                "<!-- rahp-registry-case:" + event["case_id"] + " -->" not in body):
            raise DeliveryError("existing owner lacks the approved Registry case identity")
        if event["source_revision"] not in body or event["finding_id"] not in body:
            raise DeliveryError("existing owner does not acknowledge this exact source revision/finding; reassessment required")
        if "source_routing_key" in event:
            routes = re.findall(r"<!-- rahp-registry-source-routing:([^<>\n]+) -->", body)
            manifests = re.findall(r"<!-- rahp-registry-monitored-manifest:sha256:([^<>\n]+) -->", body)
            if routes != [event["source_routing_key"]] or manifests != [intake.manifest_digest(event)]:
                raise DeliveryError("existing owner lacks exact approved monitored manifest/routing identity")
        digest = event.get("source_evidence_sha256")
        if digest and (
                "<!-- rahp-registry-monitored-evidence:sha256:" + digest + " -->"
                not in body):
            raise DeliveryError(
                "existing owner does not acknowledge the exact monitored source evidence digest; reassessment required"
            )
    return decision


TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
TOOLKIT_API = "https://api.github.com/repos/" + TOOLKIT
TRANSFER_PATH = "instances/dtg/registry-transfers.json"
PENDING_PATH = re.compile(r"^outbox/pending/[a-z0-9][a-z0-9-]*\.json$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def verify_live_reservation(manifest, manifest_path, token, *, fetch=None):
    """Read-only proof of a matching Toolkit main reservation, not assurance PASS.

    The branch head is checked twice; this cannot atomically fence concurrent
    workflows. A separate operator cutover gate must exclude in-flight publishers.
    """
    event = require_event(manifest)
    if "source_routing_key" in event:
        raise DeliveryError("historical lineage requires monitored qualification, not transfer")
    if not isinstance(manifest_path, str) or not PENDING_PATH.fullmatch(manifest_path):
        raise DeliveryError("reservation requires a committed canonical pending-intake path")
    if fetch is None:
        fetch = lambda url: intake.request("GET", url, token)
    registry_ref = fetch("https://api.github.com/repos/" + intake.REGISTRY + "/branches/main")
    registry_head = ((registry_ref or {}).get("commit") or {}).get("sha")
    if not isinstance(registry_head, str) or not COMMIT_SHA.fullmatch(registry_head):
        raise DeliveryError("Registry main branch revision unavailable")
    committed = fetch("https://api.github.com/repos/" + intake.REGISTRY +
                      "/contents/" + manifest_path + "?ref=" + registry_head)
    if not isinstance(committed, dict) or committed.get("encoding") != "base64":
        raise DeliveryError("Registry pending intent is not committed")
    try:
        actual = json.loads(base64.b64decode(committed["content"]).decode("utf-8"))
    except (KeyError, ValueError, UnicodeError, binascii.Error) as exc:
        raise DeliveryError("invalid committed Registry intent") from exc
    if actual != manifest:
        raise DeliveryError("Registry committed intent does not match qualification input")
    ref = fetch(TOOLKIT_API + "/branches/main")
    head = ((ref or {}).get("commit") or {}).get("sha")
    if not isinstance(head, str) or not COMMIT_SHA.fullmatch(head):
        raise DeliveryError("Toolkit main branch revision unavailable")
    contents = fetch(TOOLKIT_API + "/contents/" + TRANSFER_PATH + "?ref=" + head)
    if not isinstance(contents, dict) or contents.get("encoding") != "base64":
        raise DeliveryError("Toolkit transfer ledger content unavailable")
    try:
        ledger = json.loads(base64.b64decode(contents["content"], validate=False).decode("utf-8"))
    except (KeyError, ValueError, UnicodeError, binascii.Error) as exc:
        raise DeliveryError("invalid Toolkit transfer ledger encoding") from exc
    if not isinstance(ledger, dict) or set(ledger) != {"schema", "transfers"} or ledger.get("schema") != "rahp-registry-transfers/v1" or not isinstance(ledger.get("transfers"), list):
        raise DeliveryError("unsupported Toolkit transfer ledger")
    entry = [e for e in ledger["transfers"] if isinstance(e, dict) and e.get("assessment_key") == event["assessment_key"]]
    if len(entry) != 1:
        raise DeliveryError("missing or ambiguous exact Toolkit reservation")
    reservation = entry[0]
    required = {"assessment_key", "toolkit_issue_url", "registry_intent_path", "source_revision", "finding_id", "state"}
    if set(reservation) != required or reservation["state"] != "reserved" or reservation["registry_intent_path"] != manifest_path or reservation["source_revision"] != event["source_revision"] or reservation["finding_id"] != event["finding_id"]:
        raise DeliveryError("Toolkit reservation does not match committed pending intake")
    url = reservation["toolkit_issue_url"]
    match = re.fullmatch(r"https://github\.com/sankarshanmukhopadhyay/rahp-toolkit/issues/([1-9][0-9]*)", str(url))
    if not match:
        raise DeliveryError("invalid historical Toolkit issue identity")
    issue = fetch(TOOLKIT_API + "/issues/" + match.group(1))
    if not isinstance(issue, dict) or issue.get("html_url") != url or issue.get("state") not in ("open", "closed"):
        raise DeliveryError("historical Toolkit issue does not resolve")
    body = issue.get("body") or ""
    if ("<!-- rahp-assessment-key:" + event["assessment_key"] + " -->") not in body or event["finding_id"] not in body:
        raise DeliveryError("historical Toolkit issue does not identify the reserved proposition and finding")
    new_ref = fetch(TOOLKIT_API + "/branches/main")
    if ((new_ref or {}).get("commit") or {}).get("sha") != head:
        raise DeliveryError("Toolkit main changed during reservation qualification")
    registry_again = fetch("https://api.github.com/repos/" + intake.REGISTRY + "/branches/main")
    if ((registry_again or {}).get("commit") or {}).get("sha") != registry_head:
        raise DeliveryError("Registry main changed during intent qualification")
    return {"toolkit_main_sha": head, "registry_main_sha": registry_head,
            "toolkit_issue_url": url, "registry_intent_path": manifest_path,
            "assessment_key": event["assessment_key"]}


def deliver(manifest, token, *, apply=False, allow_new_case=False, load_issues=None, post=None, before_post=None):
    """Only a live issue re-read acknowledges a delivery, not an HTTP POST.

    Publication workers must be serialized; GitHub has no atomic unique issue key.
    An unacknowledged manifest remains durable in the repository for replay.
    """
    event = require_event(manifest)
    if load_issues is None:
        load_issues = lambda: intake.read_all(token)
    if post is None:
        post = lambda payload: intake.request("POST", intake.URL, token, payload)

    before = owner_for(event, load_issues())
    receipt = {"schema": "rahp-registry-intake-receipt/v1",
               "assessment_key": event["assessment_key"],
               "source_revision": event["source_revision"],
               "finding_id": event["finding_id"],
               "mode": "apply" if apply else "dry_run",
               "assurance_determination": None, "controller_execution": None}
    if before["action"] == "existing-owner":
        receipt.update(state="owner_observed", owner_url=before.get("url"), owner_number=before["number"])
        return receipt
    if before["action"] != "create":
        raise DeliveryError("unknown intake action")
    if not apply:
        receipt.update(state="pending", owner_url=None, owner_number=None)
        return receipt
    # The production entry point never grants new-case authority while Toolkit
    # remains an active publisher. A test-injected override exercises transport
    # recovery without asserting operational authorization or cutover.
    if not allow_new_case:
        raise DeliveryError(
            "new Registry issue creation blocked: publisher cutover authority not established"
        )

    if before_post is not None:
        before_post()
    failure = None
    response = None
    try:
        response = post({"title": event["title"], "body": intake.render_body(event),
                         "assignees": ["sankarshanmukhopadhyay"]})
    except Exception as exc:
        failure = exc

    after = owner_for(event, load_issues())
    if after["action"] != "existing-owner" or not after.get("url"):
        raise DeliveryError("no authoritative Registry owner after delivery; replay pending intent") from failure
    if response is not None and (not isinstance(response, dict)
                                 or response.get("number") != after["number"]
                                 or response.get("html_url") != after["url"]):
        raise DeliveryError("POST receipt disagrees with authoritative Registry owner")
    receipt.update(state="owner_observed", owner_url=after["url"], owner_number=after["number"])
    if failure is not None:
        receipt["recovered_after_ambiguous_post"] = True
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--qualify-reservation", action="store_true",
                        help="read-only live Toolkit main reservation qualification; never enables POST")
    args = parser.parse_args()
    receipt = {"schema": "rahp-registry-intake-receipt/v1", "state": "indeterminate",
               "mode": "apply" if args.apply else "dry_run", "assurance_determination": None}
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        event = require_event(data)
        receipt["assessment_key"] = event["assessment_key"]
        receipt["source_revision"] = event["source_revision"]
        token = os.environ.get("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise DeliveryError("REGISTRY_INTAKE_TOKEN required to verify live owners")
        if args.qualify_reservation:
            if args.apply:
                raise DeliveryError("read-only reservation qualification cannot be combined with --apply")
            proof = verify_live_reservation(data, args.manifest.as_posix(), token)
            receipt.update(state="reservation_qualified", **proof,
                           controller_execution=None)
        else:
            receipt = deliver(data, token, apply=args.apply)
    except (OSError, ValueError, intake.IntakeError) as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if receipt["state"] == "indeterminate":
        print("INVALID: delivery unacknowledged; committed intent remains pending", file=sys.stderr)
        return 1
    print("Registry intake:", receipt["state"], "(not RAHP assurance PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
