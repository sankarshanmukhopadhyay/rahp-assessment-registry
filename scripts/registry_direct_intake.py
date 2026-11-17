#!/usr/bin/env python3
"""Source-qualified direct intake into Registry, never an RAHP assurance outcome.

Unlike a historical Toolkit transfer, direct intake has no Toolkit issue anchor.
Only an exact committed authorization permits a single manually dispatched case.
"""
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
import registry_outbox as outbox

REGISTRY = intake.REGISTRY
TOOLKIT = "sankarshanmukhopadhyay/rahp-toolkit"
API = "https://api.github.com/repos/"
AUTH_PATH = "ops/migration/direct-intake-authorizations.json"
PENDING = re.compile(r"^outbox/pending/[a-z0-9][a-z0-9-]*\.json$")
SHA = re.compile(r"^[0-9a-f]{40}$")
DIRECT = re.compile(r"^external:direct:[a-z0-9][a-z0-9:._/-]{7,160}$")


class AdmissionError(ValueError):
    pass


def _json_contents(value, what):
    if not isinstance(value, dict) or value.get("encoding") != "base64":
        raise AdmissionError(what + " not available at pinned main")
    try:
        raw = base64.b64decode(value["content"], validate=False)
        return json.loads(raw.decode("utf-8"))
    except (KeyError, ValueError, UnicodeError, binascii.Error) as exc:
        raise AdmissionError(what + " cannot be decoded") from exc


def _head(fetch, repository):
    ref = fetch(API + repository + "/branches/main")
    sha = (ref.get("commit") or {}).get("sha") if isinstance(ref, dict) else None
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise AdmissionError(repository + " main revision is unavailable")
    return sha


def qualify(manifest, manifest_path, token, *, fetch=None):
    event = outbox.require_event(manifest)
    if not isinstance(manifest_path, str) or not PENDING.fullmatch(manifest_path):
        raise AdmissionError("direct intake requires a canonical committed pending path")
    key = event["assessment_key"]
    if not DIRECT.fullmatch(key) or event.get("controller_issue_url"):
        raise AdmissionError("first-time intake requires Registry-exclusive namespace and no historic controller issue")
    if event["responsible_owner"] != event["source_repository"]:
        raise AdmissionError("direct intake cannot assume another source owner's authority")
    source_url = "https://github.com/" + event["source_repository"] + "/commit/" + event["source_revision"]
    if event["source_url"] != source_url:
        raise AdmissionError("direct intake source must resolve to the exact pinned commit")
    if fetch is None:
        fetch = lambda url: intake.request("GET", url, token)
    registry_head = _head(fetch, REGISTRY)
    committed = _json_contents(fetch(API + REGISTRY + "/contents/" + manifest_path +
                                     "?ref=" + registry_head), "committed intake")
    if committed != manifest:
        raise AdmissionError("local manifest differs from committed Registry main intent")
    authority = _json_contents(fetch(API + REGISTRY + "/contents/" + AUTH_PATH +
                                     "?ref=" + registry_head), "direct admission authorization")
    if not isinstance(authority, dict) or set(authority) != {"schema", "admissions"} or (
            authority["schema"] != "rahp-registry-direct-intake-authority/v1"
            or not isinstance(authority["admissions"], list)):
        raise AdmissionError("unrecognized direct-intake authority ledger")
    required = {"assessment_key", "manifest_path", "source_repository", "source_revision",
                "finding_id", "status"}
    matches = [record for record in authority["admissions"]
               if isinstance(record, dict) and record.get("assessment_key") == key]
    if len(matches) != 1 or set(matches[0]) != required or matches[0] != {
            "assessment_key": key, "manifest_path": manifest_path,
            "source_repository": event["source_repository"],
            "source_revision": event["source_revision"],
            "finding_id": event["finding_id"], "status": "approved"}:
        raise AdmissionError("no exact committed source-qualified direct-intake authorization")

    commit = fetch(API + event["source_repository"] + "/commits/" + event["source_revision"])
    if not isinstance(commit, dict) or commit.get("sha") != event["source_revision"] or (
            commit.get("html_url") != source_url):
        raise AdmissionError("authoritative source commit does not match reviewed intake")

    # Toolkit owns historic observations. No direct case may replace an existing
    # assessment proposition. This is an exact-string countercheck, not fuzzy review.
    toolkit_head = _head(fetch, TOOLKIT)
    scanned = 0
    for page in range(1, 100):
        issues = fetch(API + TOOLKIT + "/issues?state=all&per_page=100&page=" + str(page))
        if not isinstance(issues, list):
            raise AdmissionError("Toolkit existing-owner enumeration malformed")
        for issue in issues:
            if "pull_request" in issue:
                continue
            body = issue.get("body") or ""
            title = issue.get("title") or ""
            if ("<!-- rahp-assessment-key:" + key + " -->") in body or (
                event["source_repository"] in (title + "\n" + body)
                and event["finding_id"] in (title + "\n" + body)
            ):
                raise AdmissionError("Toolkit already contains the direct-intake proposition")
            scanned += 1
        if len(issues) < 100:
            break
    else:
        raise AdmissionError("Toolkit owner scan exceeded bounded pagination")
    if _head(fetch, TOOLKIT) != toolkit_head or _head(fetch, REGISTRY) != registry_head:
        raise AdmissionError("source-of-authority branch changed during admission")
    return {
        "schema": "rahp-registry-direct-intake-qualification/v1",
        "assessment_key": key,
        "finding_id": event["finding_id"],
        "manifest_path": manifest_path,
        "source_revision": event["source_revision"],
        "registry_main_sha": registry_head,
        "toolkit_main_sha": toolkit_head,
        "toolkit_historical_issues_scanned": scanned,
        "source_commit_observed": True,
        "source_only_direct_intake": True,
        "no_toolkit_issue_created": True,
        "controller_execution": None,
        "assurance_determination": None,
    }


def run(manifest, path, token, *, apply=False, fetch=None, load_issues=None, post=None):
    proof = qualify(manifest, path, token, fetch=fetch)
    if not apply:
        return {**proof, "mode": "dry_run", "state": "qualified",
                "owner_url": None, "owner_number": None}
    receipt = outbox.deliver(manifest, token, apply=True, allow_new_case=True,
                             load_issues=load_issues, post=post)
    if receipt["state"] != "owner_observed":
        raise AdmissionError("direct intake lacks an observed authoritative Registry owner")
    return {**proof, **receipt, "admission": "direct-source-qualified",
            "first_case_execution": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    receipt = {"schema": "rahp-registry-direct-intake-qualification/v1",
               "state": "indeterminate", "mode": "apply" if args.apply else "dry_run",
               "assurance_determination": None, "controller_execution": None}
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        token = os.getenv("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise AdmissionError("REGISTRY_INTAKE_TOKEN required for live authority verification")
        receipt = run(manifest, args.manifest.as_posix(), token, apply=args.apply)
    except (OSError, ValueError, intake.IntakeError) as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if receipt["state"] == "indeterminate":
        print("INVALID direct intake; durable pending intent remains for review", file=sys.stderr)
        return 1
    print("Registry direct intake:", receipt["state"], "(no assurance PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
