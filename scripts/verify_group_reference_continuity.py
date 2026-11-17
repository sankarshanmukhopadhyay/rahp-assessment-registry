#!/usr/bin/env python3
"""Verify live reference continuity after a monitored Registry group acknowledgment.

This is a locator/identity check, not controller, reviewer, DPIP or Lab
consumer migration. Missing live evidence fails closed without a write.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as gh
import registry_group_observation_ack as ack

REG = gh.REGISTRY
TK = "sankarshanmukhopadhyay/rahp-toolkit"
ROOT = "https://api.github.com/repos/"
TOOLKIT_URL = "https://github.com/" + TK + "/issues/"
REGISTRY_URL = "https://github.com/" + REG + "/issues/"
KEY_MARK = "<!-- rahp-assessment-key:dtg:portfolio:combined:spec-dependency-alignment -->"
REG_MARK = "<!-- registry-assessment-key:dtg:portfolio:combined:spec-dependency-alignment -->"
GROUP_MARK = "<!-- rahp-registry-monitored-group:v1:"


class LocatorError(ValueError):
    pass


def locate(intent, delivery, observed, *, get):
    if not isinstance(intent, dict):
        raise LocatorError("committed source intent unavailable")
    expected = [TOOLKIT_URL + str(n) for n in (272, 615, 282, 826, 837)]
    current = intent.get("toolkit_current_issue_url")
    historical = intent.get("toolkit_historical_issue_url")
    protected = intent.get("protected_issue_urls")
    if ([current, historical] + (protected if isinstance(protected, list) else [])) != expected:
        raise LocatorError("source, historical or protected Toolkit references changed")
    if (not isinstance(delivery, dict) or delivery.get("state") != "owner_observed"
            or not isinstance(observed, dict)
            or observed.get("state") != "observed"
            or observed.get("current_observation_acknowledged") is not True):
        raise LocatorError("Registry successor/observation is unacknowledged")
    url = delivery.get("owner_url")
    if (not isinstance(url, str) or
            not re.fullmatch(re.escape(REGISTRY_URL) + r"[1-9][0-9]*", url)
            or observed.get("registry_issue_url") != url
            or observed.get("source_group_sha256") != intent.get("source_group_sha256")
            or delivery.get("source_group_sha256") != intent.get("source_group_sha256")):
        raise LocatorError("Registry owner or acknowledgment source mismatch")
    number = int(url.removeprefix(REGISTRY_URL))
    owner = get(ROOT + REG + "/issues/" + str(number))
    if (not isinstance(owner, dict) or owner.get("number") != number
            or owner.get("html_url") != url or owner.get("state") != "open"
            or "pull_request" in owner):
        raise LocatorError("Registry successor is not an open unique issue")
    body = owner.get("body") or ""
    if (REG_MARK not in body or
            GROUP_MARK + intent["source_group_sha256"] + " -->" not in body
            or any(link not in body for link in expected)
            or any("Finding: " + fid not in body
                   for fid in intent["source_finding_ids"])):
        raise LocatorError("Registry successor lacks required source/backlinks")
    confirmed = ack.observed(ack.comments(number, get), number,
                             intent["source_group_sha256"])
    if confirmed is None or confirmed["html_url"] != observed.get("comment_url"):
        raise LocatorError("authenticated current observation not found")
    # The five issue numbers are Toolkit-local historical/consumer identifiers;
    # they must never be replaced with the Registry owner issue number.
    for index, old_url in enumerate(expected):
        old_number = int(old_url.removeprefix(TOOLKIT_URL))
        issue = get(ROOT + TK + "/issues/" + str(old_number))
        expected_state = ("open" if index == 0 else "closed" if index == 1 else None)
        if (not isinstance(issue, dict) or issue.get("number") != old_number
                or issue.get("html_url") != old_url
                or issue.get("state") not in ("open", "closed")
                or "pull_request" in issue):
            raise LocatorError("Toolkit original/historical/residual issue unavailable")
        if expected_state and issue["state"] != expected_state:
            raise LocatorError("Toolkit source or historical lifecycle changed")
        if index in (0, 1) and KEY_MARK not in (issue.get("body") or ""):
            raise LocatorError("Toolkit source/historical key marker unavailable")
        if index == 0 and any(fid not in (issue.get("body") or "")
                              for fid in intent["source_finding_ids"]):
            raise LocatorError("Toolkit current owner lost source findings")
    return {
        "schema": "rahp-registry-group-reference-continuity/v1",
        "source_group_sha256": intent["source_group_sha256"],
        "registry_case_issue_url": url,
        "authenticated_observation_url": confirmed["html_url"],
        "toolkit_current_issue_url": current,
        "toolkit_historical_issue_url": historical,
        "independent_residual_urls": protected,
        "all_references_live_and_distinct": True,
        "controller_issue_number_adapter_executed": False,
        "reviewer_issue_number_adapter_executed": False,
        "specialist_return_transport_authenticated": False,
        "cutover_authorized": False,
        "assurance_determination": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "owner_receipt", "observation_receipt", "out"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    receipt = {"schema": "rahp-registry-group-reference-continuity/v1",
               "state": "indeterminate", "cutover_authorized": False}
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN")
        if not token:
            raise LocatorError("authenticated read token required")
        intent = json.loads(args.manifest.read_text(encoding="utf-8"))
        delivery = json.loads(args.owner_receipt.read_text(encoding="utf-8"))
        observed = json.loads(args.observation_receipt.read_text(encoding="utf-8"))
        receipt = locate(intent, delivery, observed,
                         get=lambda url: gh.request("GET", url, token))
    except (OSError, ValueError, KeyError, TypeError, gh.IntakeError, ack.AckError) as exc:
        receipt["error"] = str(exc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if receipt.get("state") == "indeterminate":
        print("BLOCKED: Registry/Toolkit reference continuity unverified",
              file=sys.stderr)
        return 1
    print("Registry/Toolkit references resolved; consumers not migrated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
