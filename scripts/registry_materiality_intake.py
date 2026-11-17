#!/usr/bin/env python3
"""Read-only materiality -> reviewed Registry intake reconciliation.

Consumes the actual normalized router result and the exact monitored source
snapshot. Only a Git-committed, explicitly reviewed outbox intent can be
eligible to create or reassess. No issue is written; no source or assurance
authority is inferred from a routed finding.
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

SHA = re.compile(r"^[0-9a-f]{40}$")
GIT_COMMIT = re.compile(
    r"^https://github[.]com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/commit/([0-9a-f]{40})$"
)
ALLOWED_OUTCOMES = {"combined", "dpip", "covered", "no-action", "UNMAPPED"}


class MaterialityError(ValueError):
    pass


def checked_source(findings, routed):
    """Reject a substituted, duplicated, or unqualified router observation."""
    if not isinstance(findings, list) or not isinstance(routed, list) or not routed:
        raise MaterialityError("source and nonempty routed observations required")
    source = {}
    for item in findings:
        if not isinstance(item, dict) or not isinstance(item.get("finding_id"), str):
            raise MaterialityError("malformed source finding identity")
        fid = item["finding_id"]
        if fid in source:
            raise MaterialityError("duplicate monitored source finding")
        source[fid] = item
    seen = set()
    for entry in routed:
        if not isinstance(entry, dict) or not isinstance(entry.get("finding"), dict):
            raise MaterialityError("malformed normalized routing item")
        observed = entry["finding"]
        fid = observed.get("finding_id")
        if fid in seen:
            raise MaterialityError("duplicate routed material finding")
        seen.add(fid)
        if fid not in source or observed != source[fid]:
            raise MaterialityError("routed finding does not match exact monitored source")
        if (observed.get("state") != "open"
                or observed.get("review_status") not in (None, "unreviewed")
                or observed.get("materiality") not in ("high", "critical")
                or observed.get("assurance_impact") not in ("potentially-breaking", "breaking")
                or entry.get("outcome") not in ALLOWED_OUTCOMES):
            raise MaterialityError("routed finding has unsupported materiality/route state")
    return source


def immutable_pin(finding, event):
    """The source commit must be present in the actual monitored evidence set."""
    pins = set()
    for url in finding.get("evidence_urls") or []:
        if not isinstance(url, str):
            raise MaterialityError("malformed source evidence URL")
        m = GIT_COMMIT.fullmatch(url)
        if m:
            pins.add((m.group(1), m.group(2)))
    if not pins:
        raise MaterialityError("approved materiality finding has no immutable commit evidence")
    exact = (event["source_repository"], event["source_revision"])
    if exact not in pins:
        raise MaterialityError("reviewed source pin not present in observed finding evidence")
    if event["source_url"] not in finding.get("evidence_urls", []):
        raise MaterialityError("reviewed source URL not observed in monitored evidence")
    if event["responsible_owner"] != event["source_repository"]:
        raise MaterialityError("reviewed external owner differs from pinned source")
    return exact


def plan(findings, routed, manifest, issues):
    source = checked_source(findings, routed)
    event = outbox.require_event(manifest)
    if not isinstance(issues, list):
        raise MaterialityError("live Registry issue collection required")
    # Guard against ambiguous owner state even when no matching event is in
    # the current snapshot; the result must not imply a usable Registry.
    intake.index_issues(issues)
    matches = [entry for entry in routed
               if entry["finding"]["finding_id"] == event["finding_id"]]
    status = "outside_observed_materiality"
    owner = None
    if len(matches) > 1:
        raise MaterialityError("duplicate approved material finding")
    if matches:
        finding = matches[0]["finding"]
        if finding.get("repository") != event["source_repository"]:
            raise MaterialityError("approved source repository mismatch")
        immutable_pin(finding, event)
        try:
            decision = outbox.owner_for(event, issues)
        except (outbox.DeliveryError, intake.IntakeError) as exc:
            msg = str(exc)
            if "reassessment required" in msg:
                status = "reassessment_required"
                # This is a blocked decision, not successful case acceptance:
                # an authorized new epoch must be reviewed against the owner.
                owner = None
            else:
                raise MaterialityError("Registry owner reconciliation failed: " + msg) from exc
        else:
            if decision["action"] == "existing-owner":
                status = "existing_owner"
                owner = decision["number"]
            elif decision["action"] == "create":
                status = "pending_reviewed_creation"
            else:
                raise MaterialityError("unsupported Registry owner decision")
    # Every other routed item remains unadmitted; treating a routed candidate
    # as authority to create an issue would duplicate live Toolkit ownership.
    unmatched = len(routed) - len(matches)
    def digest(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
    return {
        "schema": "rahp-registry-materiality-intake-shadow/v1",
        "monitored_source_sha256": digest(findings),
        "router_output_sha256": digest(routed),
        "approved_manifest_sha256": digest(manifest),
        "approved_assessment_key": event["assessment_key"],
        "approved_finding_id": event["finding_id"],
        "state": status,
        "owner_number": owner,
        "observed_routed_count": len(routed),
        "unadmitted_routed_count": unmatched,
        "approved_source_observed": bool(matches),
        "outbox_manifest_reviewed": True,
        "new_issue_created": False,
        "existing_issue_mutated": False,
        "source_reassessment_applied": False,
        "toolkit_issue_written": False,
        "assurance_determination_imported": False,
        "source_candidate_claim": "routing-and-owner-observation-only",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("findings", "routing", "approved", "receipt"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    receipt = {"schema": "rahp-registry-materiality-intake-shadow/v1",
               "state": "invalid", "new_issue_created": False,
               "assurance_determination_imported": False}
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise MaterialityError("read-only Registry token required for live owner reconciliation")
        findings = json.loads(args.findings.read_text(encoding="utf-8"))
        routed = json.loads(args.routing.read_text(encoding="utf-8"))
        manifest = json.loads(args.approved.read_text(encoding="utf-8"))
        receipt = plan(findings, routed, manifest, intake.read_all(token))
    except (OSError, ValueError, TypeError, KeyError, intake.IntakeError,
            outbox.DeliveryError) as exc:
        receipt["error"] = str(exc)
        print("INVALID Registry materiality intake:", exc, file=sys.stderr)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if receipt["state"] == "invalid":
        return 1
    print("Registry materiality:", receipt["state"],
          f"(unadmitted routed: {receipt['unadmitted_routed_count']}, no writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
