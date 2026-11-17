#!/usr/bin/env python3
"""Replay source-controlled Registry intake intents; never write Toolkit issues."""
from __future__ import annotations

import argparse
import json
import os
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
    decisions = intake.plan([event], issues)
    if len(decisions) != 1:
        raise DeliveryError("ambiguous source event planning")
    decision = decisions[0]
    if decision["action"] == "existing-owner":
        matching = [i for i in issues if i.get("number") == decision["number"] and "pull_request" not in i]
        if len(matching) != 1:
            raise DeliveryError("existing owner is missing or ambiguous")
        body = matching[0].get("body") or ""
        if event["source_revision"] not in body or event["finding_id"] not in body:
            raise DeliveryError("existing owner does not acknowledge this exact source revision/finding; reassessment required")
    return decision


def deliver(manifest, token, *, apply=False, allow_new_case=False, load_issues=None, post=None):
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
