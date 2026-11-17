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
                # Covered/no-action are route dispositions, not a new external
                # examination mandate. A reviewed manifest cannot invert them.
                if matches[0].get("outcome") in ("covered", "no-action"):
                    status = "no_new_case_for_covered_route"
                else:
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



def pending_group_shadow(filename, intent):
    """Account for a separate grouped pending intent without admitting it as one finding.

    Group source/member qualification belongs to the pinned canonical parity
    workflow. A pending intent never counts as an accepted Registry owner.
    """
    if filename != "spec-dependency-2026-11-16.json":
        raise MaterialityError("unreviewed grouped pending intent path")
    if not isinstance(intent, dict) or intent.get("schema") != (
            "rahp-registry-pending-monitored-group/v1"):
        raise MaterialityError("unrecognized grouped pending intent")
    if (intent.get("assessment_key") !=
            "dtg:portfolio:combined:spec-dependency-alignment"
            or intent.get("status") != "pending_governance"
            or intent.get("registry_successor_issue_url") is not None
            or intent.get("current_observation_acknowledged") is not False
            or intent.get("toolkit_writer_suppression_authorized") is not False
            or intent.get("assurance_determination") is not None):
        raise MaterialityError("group intent asserts unsupported authority")
    ids = intent.get("source_finding_ids")
    if (not isinstance(ids, list) or len(ids) != 4
            or ids != sorted(set(ids))):
        raise MaterialityError("group intent is not the four-finding pending obligation")
    return {"manifest": filename, "assessment_key": intent["assessment_key"],
            "state": "group_pending_separate_qualification",
            "finding_count": len(ids),
            "source_group_sha256": intent.get("source_group_sha256"),
            "registry_owner_accepted": False,
            "current_observation_acknowledged": False,
            "new_issue_created": False, "cutover_authorized": False}


def plan_many(findings, routed, manifests, issues):
    """Reconcile a reviewed set against one observed source and owner snapshot."""
    if not isinstance(manifests, dict) or not manifests:
        raise MaterialityError("at least one reviewed intake manifest required")
    checked_source(findings, routed)
    keys, findings_seen, owners, observations, confirmed = set(), set(), set(), set(), set()
    results = []
    pending_groups = []
    for filename, manifest in sorted(manifests.items()):
        if isinstance(manifest, dict) and manifest.get("schema") == (
                "rahp-registry-pending-monitored-group/v1"):
            pending_groups.append(pending_group_shadow(filename, manifest))
            continue
        event = outbox.require_event(manifest)
        key, fid = event["assessment_key"], event["finding_id"]
        if key in keys or fid in findings_seen:
            raise MaterialityError("duplicate reviewed assessment key or finding")
        keys.add(key)
        findings_seen.add(fid)
        decision = plan(findings, routed, manifest, issues)
        if decision["owner_number"] is not None:
            if decision["owner_number"] in owners:
                raise MaterialityError("ambiguous Registry owner across reviewed manifests")
            owners.add(decision["owner_number"])
        if decision["approved_source_observed"]:
            observations.add(fid)
            if decision["state"] == "existing_owner":
                confirmed.add(fid)
        results.append({"manifest": filename, "decision": decision})
    return {
        "schema": "rahp-registry-materiality-batch-shadow/v1",
        "state": "read_only_reconciliation",
        "monitored_source_sha256": results[0]["decision"]["monitored_source_sha256"],
        "router_output_sha256": results[0]["decision"]["router_output_sha256"],
        "observed_routed_count": len(routed),
        "reviewed_intent_count": len(results),
        "pending_group_intent_count": len(pending_groups),
        "pending_group_intents": pending_groups,
        "reviewed_source_match_count": len(observations),
        "unreviewed_routed_count": len(routed) - len(observations),
        "without_confirmed_registry_owner_count": len(routed) - len(confirmed),
        "intents": results,
        "new_issue_created": False,
        "existing_issue_mutated": False,
        "source_reassessment_applied": False,
        "toolkit_issue_written": False,
        "assurance_determination_imported": False,
        "cutover_authorized": False,
    }


def read_reviewed_manifests(directory):
    if not directory.is_dir() or directory.is_symlink():
        raise MaterialityError("reviewed manifest directory required")
    files = sorted(directory.iterdir())
    if not files:
        raise MaterialityError("reviewed manifest directory is empty")
    manifests = {}
    for item in files:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*[.]json", item.name):
            raise MaterialityError("unexpected reviewed manifest filename")
        if item.is_symlink() or not item.is_file():
            raise MaterialityError("reviewed manifest must be an ordinary file")
        manifests[item.name] = json.loads(item.read_text(encoding="utf-8"))
    return manifests


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("findings", "routing", "receipt"):
        p.add_argument("--" + name, required=True, type=Path)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--approved", type=Path)
    source.add_argument("--approved-dir", type=Path)
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
        issues = intake.read_all(token)
        if args.approved_dir is not None:
            receipt = plan_many(findings, routed,
                                read_reviewed_manifests(args.approved_dir), issues)
        else:
            manifest = json.loads(args.approved.read_text(encoding="utf-8"))
            receipt = plan(findings, routed, manifest, issues)
    except (OSError, ValueError, TypeError, KeyError, intake.IntakeError,
            outbox.DeliveryError) as exc:
        receipt["error"] = str(exc)
        print("INVALID Registry materiality intake:", exc, file=sys.stderr)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if receipt["state"] == "invalid":
        return 1
    unowned = receipt.get("without_confirmed_registry_owner_count",
                          receipt.get("unadmitted_routed_count"))
    print("Registry materiality:", receipt["state"],
          f"(routed without confirmed Registry owner: {unowned}, no writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
