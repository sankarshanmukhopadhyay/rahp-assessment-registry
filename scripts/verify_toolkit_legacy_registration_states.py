#!/usr/bin/env python3
"""Independently verify live Toolkit workflow registration retirement.

Read-only registration evidence. This is not a test of all GitHub Issues
credentials, old-ref dispatch attempts, or universal Registry case ownership.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
API = "https://api.github.com/repos/" + TOOLKIT + "/actions/workflows"
REPLACEMENTS = (
    ".github/workflows/dtg-materiality-main.yml",
    ".github/workflows/instance-monitor-main.yml",
)
LEGACY = (
    (343470013, ".github/workflows/dtg-portfolio-materiality-handoff.yml"),
    (334033746, ".github/workflows/instance-watch.yml"),
)
DISABLED = frozenset({"disabled_manually", "deleted"})


class RegistrationError(ValueError):
    pass


def verify(inventory, lookup):
    if not isinstance(inventory, dict) or not isinstance(inventory.get("workflows"), list):
        raise RegistrationError("live workflow listing unavailable")
    replacements = []
    for path in REPLACEMENTS:
        matches = [row for row in inventory["workflows"]
                   if isinstance(row, dict) and row.get("path") == path]
        if (len(matches) != 1 or matches[0].get("state") != "active"
                or type(matches[0].get("id")) is not int):
            raise RegistrationError("replacement missing, ambiguous or not active: " + path)
        replacements.append({"id": matches[0]["id"], "path": path, "state": "active"})
    retired = []
    for workflow_id, path in LEGACY:
        record = lookup(workflow_id)
        if (not isinstance(record, dict) or record.get("id") != workflow_id
                or record.get("path") != path or record.get("state") not in DISABLED):
            raise RegistrationError("legacy registration still active or mismatched: " + path)
        retired.append({"id": workflow_id, "path": path, "state": record["state"]})
    return {
        "schema": "rahp-registry-independent-toolkit-registration-check/v1",
        "toolkit": TOOLKIT,
        "replacement_registrations": replacements,
        "retired_legacy_registrations": retired,
        "legacy_registration_retirement_verified": True,
        "historical_dispatch_denial_observed": False,
        "toolkit_external_case_publication_exclusive": False,
        "registry_cutover_authorized": False,
    }


def fetch(url, token=""):
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "rahp-registry-independent-workflow-retirement/1.0"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RegistrationError("GitHub registration read failed with HTTP " + str(exc.code)) from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # GitHub's public workflow listing supports unauthenticated reads for
    # public Toolkit; a Registry-scoped token does not confer Toolkit rights.
    report = verify(fetch(API + "?per_page=100"),
                    lambda workflow_id: fetch(API + "/" + str(workflow_id)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("PASS independently verified two retired Toolkit registrations and two live replacements")
    print("No dispatch-denial or general case-owner cutover claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
