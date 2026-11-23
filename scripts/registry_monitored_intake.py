#!/usr/bin/env python3
"""Admit one reviewed monitored external case only under Registry publication authority.

This is the Registry-side successor of a Toolkit *external-case* writer, not
an RAHP assessment or specialist result. GitHub issue insertion has no atomic
unique-key primitive; this operation must share the Registry case-publication
concurrency group and remain under an independently established old-writer
exclusion. Current-main policy and quiescence alone cannot prove that exclusion.
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
import registry_outbox as outbox
import registry_direct_intake as direct
import verify_toolkit_writer_quiescence as quiescence
from audit_toolkit_issue_writers import EXTERNAL_EXPECTED

API = "https://api.github.com/repos/"
REGISTRY = intake.REGISTRY
TOOLKIT = direct.TOOLKIT
AUTH_PATH = "ops/migration/monitored-intake-authorizations.json"
POLICY_PATH = "instances/dtg/external-case-publication.json"
KEY = re.compile(r"^(?:dtg|cawg):[a-z0-9][a-z0-9:._/-]{7,170}$")
CASE_ID = re.compile(r"^RAHP-AR-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DISABLED = frozenset({"disabled_manually", "deleted"})
OLD_WORKFLOWS = frozenset({
    *(f".github/workflows/{name}" for name in EXTERNAL_EXPECTED),
    ".github/workflows/dtg-portfolio-materiality-handoff.yml",
    ".github/workflows/instance-watch.yml",
})
FIELDS = frozenset({
    "assessment_key", "case_id", "manifest_path", "source_repository",
    "source_revision", "finding_id", "source_evidence_sha256", "status",
})


class MonitoredAdmissionError(ValueError):
    pass


def _owner_scan(fetch, event):
    """Current or historical Toolkit issue identity always prevails."""
    checked = 0
    marker = "<!-- rahp-assessment-key:" + event["assessment_key"] + " -->"
    for page in range(1, 101):
        url = API + TOOLKIT + "/issues?state=all&per_page=100&page=" + str(page)
        rows = fetch(url)
        if not isinstance(rows, list):
            raise MonitoredAdmissionError("Toolkit issue owner enumeration unavailable")
        for issue in rows:
            if not isinstance(issue, dict):
                raise MonitoredAdmissionError("invalid Toolkit issue owner entry")
            if "pull_request" in issue:
                continue
            if marker in (issue.get("body") or ""):
                raise MonitoredAdmissionError(
                    "Toolkit already owns this assessment key; use governed transfer"
                )
            checked += 1
        if len(rows) < 100:
            return checked
    raise MonitoredAdmissionError("Toolkit issue owner scan exceeds bounded history")


def verify_registration_exclusion(fetch):
    """Require server-side disabled registration for every known Toolkit external writer.

    The policy file blocks current-code mutation; disabled registrations
    additionally prevent executing prior workflow revisions on historical
    branch/tag refs. GitHub does not provide a universal credential lock.
    """
    observed = []
    expected_total = None
    for page in range(1, 101):
        response = fetch(
            API + TOOLKIT + "/actions/workflows?per_page=100&page=" + str(page)
        )
        if (not isinstance(response, dict)
                or type(response.get("total_count")) is not int
                or not isinstance(response.get("workflows"), list)):
            raise MonitoredAdmissionError("Toolkit workflow registration inventory unavailable")
        total = response["total_count"]
        if total < 0 or (expected_total is not None and total != expected_total):
            raise MonitoredAdmissionError("Toolkit workflow registrations changed during pagination")
        expected_total = total
        page_rows = response["workflows"]
        if len(page_rows) > 100 or len(observed) + len(page_rows) > total:
            raise MonitoredAdmissionError("Toolkit workflow registration page invalid")
        observed.extend(page_rows)
        if len(page_rows) < 100:
            if len(observed) != expected_total:
                raise MonitoredAdmissionError("incomplete Toolkit workflow registration listing")
            break
    else:
        raise MonitoredAdmissionError("Toolkit workflow inventory exceeds pagination bound")

    selected = []
    for path in sorted(OLD_WORKFLOWS):
        matches = [row for row in observed
                   if isinstance(row, dict) and row.get("path") == path]
        if (len(matches) != 1 or type(matches[0].get("id")) is not int
                or matches[0]["id"] < 1 or matches[0].get("state") not in DISABLED):
            raise MonitoredAdmissionError(
                "external Toolkit writer registration not demonstrably disabled: " + path
            )
        selected.append({"path": path, "id": matches[0]["id"],
                         "state": matches[0]["state"]})
    return selected


def verify_accepted_source_event(fetch, toolkit_head, event):
    """Bind exact reviewed case to one immutable, accepted monitor observation.

    A digest in a maintainer ledger is not self-authenticating evidence.
    Recompute SHA-256 over the complete event stored on protected Toolkit main.
    """
    instance = event["assessment_key"].split(":", 1)[0]
    if instance not in ("dtg", "cawg"):
        raise MonitoredAdmissionError("unrecognized monitored source instance")
    source_path = f"instances/{instance}/generated/review-events.json"
    data = direct._json_contents(
        fetch(API + TOOLKIT + "/contents/" + source_path + "?ref=" + toolkit_head),
        "accepted Toolkit monitored source events",
    )
    if not isinstance(data, list):
        raise MonitoredAdmissionError("accepted monitor source batch is not an array")
    matches = [row for row in data if isinstance(row, dict)
               and row.get("assessment_key") == event["assessment_key"]]
    if len(matches) != 1:
        raise MonitoredAdmissionError("missing or duplicate accepted monitored source event")
    source = matches[0]
    canonical = json.dumps(
        source, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if (digest != event["source_evidence_sha256"]
            or event["finding_id"] != digest[:20]
            or source.get("repository") != event["source_repository"]
            or source.get("new") != event["source_revision"]
            or source.get("event_class") not in (None, "assessment-required")
            or "assessment-required" not in (source.get("labels") or [])):
        raise MonitoredAdmissionError(
            "Registry source scope does not match the exact accepted material review event"
        )
    return {"instance": instance, "path": source_path,
            "evidence_sha256": digest, "accepted_toolkit_commit": toolkit_head}


def qualify(manifest, manifest_path, token, *, fetch=None):
    event = outbox.require_event(manifest)
    if not isinstance(manifest_path, str) or not direct.PENDING.fullmatch(manifest_path):
        raise MonitoredAdmissionError("monitored intake requires a committed canonical pending path")
    key = event["assessment_key"]
    if not KEY.fullmatch(key) or event.get("controller_issue_url"):
        raise MonitoredAdmissionError(
            "monitored first intake requires DTG/CAWG key without Toolkit issue-number anchor"
        )
    if not CASE_ID.fullmatch(str(event.get("case_id", ""))):
        raise MonitoredAdmissionError("monitored intake requires a stable Registry case ID")
    evidence = event.get("source_evidence_sha256")
    if not isinstance(evidence, str) or not SHA256.fullmatch(evidence):
        raise MonitoredAdmissionError("monitored source evidence must carry immutable SHA-256")
    if event.get("responsible_owner") != event["source_repository"]:
        raise MonitoredAdmissionError("source owner scope differs from external repository")
    if fetch is None:
        fetch = lambda url: intake.request("GET", url, token)

    registry_head = direct._head(fetch, REGISTRY)
    committed = direct._json_contents(
        fetch(API + REGISTRY + "/contents/" + manifest_path + "?ref=" + registry_head),
        "committed monitored pending intent",
    )
    if committed != manifest:
        raise MonitoredAdmissionError("reviewed Registry main intent differs from supplied manifest")
    authority = direct._json_contents(
        fetch(API + REGISTRY + "/contents/" + AUTH_PATH + "?ref=" + registry_head),
        "monitored intake authority ledger",
    )
    if (not isinstance(authority, dict)
            or set(authority) != {"schema", "admissions"}
            or authority.get("schema") != "rahp-registry-monitored-intake-authority/v1"
            or not isinstance(authority.get("admissions"), list)):
        raise MonitoredAdmissionError("unsupported monitored intake authority schema")
    exact = {
        "assessment_key": key, "case_id": event["case_id"],
        "manifest_path": manifest_path,
        "source_repository": event["source_repository"],
        "source_revision": event["source_revision"],
        "finding_id": event["finding_id"],
        "source_evidence_sha256": evidence,
        "status": "approved",
    }
    matches = [
        row for row in authority["admissions"]
        if isinstance(row, dict) and row.get("assessment_key") == key
    ]
    if len(matches) != 1 or set(matches[0]) != FIELDS or matches[0] != exact:
        raise MonitoredAdmissionError("missing or ambiguous exact approved monitored source scope")

    tk_head = direct._head(fetch, TOOLKIT)
    policy = direct._json_contents(
        fetch(API + TOOLKIT + "/contents/" + POLICY_PATH + "?ref=" + tk_head),
        "protected Toolkit external-case owner policy",
    )
    if (not isinstance(policy, dict)
            or set(policy) != {"schema", "owner"}
            or policy.get("schema") != "rahp-external-case-publication/v1"
            or policy.get("owner") != "registry"):
        raise MonitoredAdmissionError(
            "Toolkit has not assigned exclusive external-case publication to Registry"
        )

    commit = fetch(API + event["source_repository"] + "/commits/" + event["source_revision"])
    if (not isinstance(commit, dict)
            or commit.get("sha") != event["source_revision"]):
        raise MonitoredAdmissionError("pinned authoritative source commit unavailable")
    evidence_record = verify_accepted_source_event(fetch, tk_head, event)
    checked = _owner_scan(fetch, event)

    retired_workflows = verify_registration_exclusion(fetch)
    run_state = quiescence.evaluate(fetch)
    if not run_state["quiescent_at_observation"]:
        raise MonitoredAdmissionError("active Toolkit external issue writer run detected")
    if (direct._head(fetch, TOOLKIT) != tk_head
            or direct._head(fetch, REGISTRY) != registry_head):
        raise MonitoredAdmissionError("publication authority changed during source qualification")
    return {
        "schema": "rahp-registry-monitored-intake-qualification/v1",
        "assessment_key": key, "case_id": event["case_id"],
        "finding_id": event["finding_id"],
        "source_revision": event["source_revision"],
        "source_evidence_sha256": evidence,
        "accepted_source": evidence_record,
        "registry_main_sha": registry_head,
        "toolkit_main_sha": tk_head,
        "toolkit_historical_issues_scanned": checked,
        "toolkit_current_policy_is_registry": True,
        "toolkit_writers_quiescent_at_observation": True,
        "registered_external_writer_exclusion_verified": True,
        "disabled_external_writer_registrations": retired_workflows,
        "historical_execution_exclusion_proven": True,
        # GitHub Issues does not provide cross-repository atomic insert.
        # This field must never be promoted by a registration scan.
        "cross_repository_atomic_lock_proven": False,
        "case_authority": "approved_monitored_source_only",
        "controller_execution": None,
        "assurance_determination": None,
    }


def run(manifest, path, token, *, apply=False, fetch=None, load_issues=None, post=None):
    proof = qualify(manifest, path, token, fetch=fetch)
    if not apply:
        return {**proof, "mode": "dry_run", "state": "qualified",
                "owner_url": None, "owner_number": None}
    receipt = outbox.deliver(
        manifest, token, apply=True, allow_new_case=True,
        load_issues=load_issues, post=post,
    )
    if receipt["state"] != "owner_observed":
        raise MonitoredAdmissionError("Registry monitored case owner unacknowledged")
    return {**proof, **receipt, "admission": "approved_monitored_source",
            "first_case_execution": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    receipt = {
        "schema": "rahp-registry-monitored-intake-qualification/v1",
        "state": "indeterminate",
        "mode": "apply" if args.apply else "dry_run",
        "assurance_determination": None,
        "controller_execution": None,
    }
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        token = os.environ.get("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise MonitoredAdmissionError("REGISTRY_INTAKE_TOKEN required for live qualification")
        receipt = run(data, args.manifest.as_posix(), token, apply=args.apply)
    except (OSError, ValueError, TypeError, KeyError, intake.IntakeError) as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    if receipt["state"] == "indeterminate":
        print("BLOCKED: monitored Registry case intake not acknowledged", file=sys.stderr)
        return 1
    print("Registry monitored intake:", receipt["state"], "(no RAHP assurance PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
