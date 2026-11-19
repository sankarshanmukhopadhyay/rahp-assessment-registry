#!/usr/bin/env python3
"""Create an evidence-bound reviewer packet with canonical Toolkit renderer.

A Registry source group is not a Toolkit issue and has no Toolkit issue
number. This consumes only the canonical worker's pure packet renderer;
it never calls an effectful Toolkit review/DPIP consumer.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
FID = re.compile(r"^[0-9a-f]{20}$")


class ReviewPacketError(ValueError):
    pass


def group_digest(group):
    return hashlib.sha256(json.dumps(
        group, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def build(intent, groups, findings, renderer, finding_parser, *, toolkit_revision):
    if not isinstance(intent, dict) or intent.get("schema") != (
            "rahp-registry-pending-monitored-group/v1"):
        raise ReviewPacketError("unknown reviewed source-group manifest")
    if not isinstance(toolkit_revision, str) or not SHA.fullmatch(toolkit_revision):
        raise ReviewPacketError("unverifiable Toolkit worker revision")
    ids = intent.get("source_finding_ids")
    if (not isinstance(ids, list) or not ids or
            any(not isinstance(fid, str) or not FID.fullmatch(fid) for fid in ids)
            or ids != sorted(set(ids))):
        raise ReviewPacketError("missing, repeated or unordered monitored finding IDs")
    if not isinstance(groups, list) or not isinstance(findings, list):
        raise ReviewPacketError("canonical groups and Monitor findings must be arrays")
    matches = [g for g in groups if isinstance(g, dict)
               and g.get("assessment_key") == intent.get("assessment_key")]
    if len(matches) != 1:
        raise ReviewPacketError("missing or ambiguous original combined source group")
    group = matches[0]
    if group.get("observed_at") != intent.get("snapshot_date"):
        raise ReviewPacketError("monitored group source date differs from approved epoch")
    if group_digest(group) != intent.get("source_group_sha256"):
        raise ReviewPacketError("original combined source-group digest differs")
    observations = group.get("source_observations")
    if not isinstance(observations, list) or len(observations) != len(ids):
        raise ReviewPacketError("missing complete source-group observations")
    observed = [row.get("finding_id") if isinstance(row, dict) else None
                for row in observations]
    if sorted(observed) != ids or len(observed) != len(set(observed)):
        raise ReviewPacketError("source group finding membership has drifted")
    catalog = {}
    for record in findings:
        if not isinstance(record, dict) or not isinstance(record.get("finding_id"), str):
            raise ReviewPacketError("malformed monitored finding")
        fid = record["finding_id"]
        if fid in catalog:
            raise ReviewPacketError("duplicate finding in pinned Monitor snapshot")
        catalog[fid] = record
    for observed_item in observations:
        fid = observed_item["finding_id"]
        source = catalog.get(fid)
        if source is None or source.get("repository") != observed_item.get("repository"):
            raise ReviewPacketError("missing or substituted source finding/repository")
    # A source descriptor, NOT an issue. Never assign number=272 or the
    # Registry issue number to a Toolkit issue-number consumer.
    subject = {"body": "\n".join("`" + fid + "`" for fid in ids)}
    if finding_parser(subject["body"]) != ids:
        raise ReviewPacketError("canonical worker parsed foreign or missing identities")
    packet = renderer(subject, catalog)
    if not isinstance(packet, str) or not packet.strip():
        raise ReviewPacketError("canonical reviewer returned no judgment packet")
    receipt = {
        "schema": "rahp-registry-canonical-combined-packet/v1",
        "state": "reviewer_packet_rendered",
        "assessment_key": intent["assessment_key"],
        "source_monitor_revision": intent["monitor_revision"],
        "source_snapshot_date": intent["snapshot_date"],
        "source_group_sha256": intent["source_group_sha256"],
        "toolkit_worker_revision": toolkit_revision,
        "finding_ids": ids,
        "finding_count": len(ids),
        "historical_toolkit_issue_url": intent["toolkit_current_issue_url"],
        "toolkit_issue_number_substituted": False,
        "registry_case_owner_accepted": False,
        "toolkit_effectful_consumer_dispatched": False,
        "source_observation_delivered": False,
        "assurance_determination": None,
        "independent_review_accepted": False,
        "cutover_authorized": False,
    }
    return packet, receipt


def load_canonical_worker(root):
    script = root / "tools/combined_review_worker.py"
    if not script.is_file() or script.is_symlink():
        raise ReviewPacketError("canonical Toolkit worker missing")
    spec = importlib.util.spec_from_file_location("pinned_combined_review_worker", script)
    if spec is None or spec.loader is None:
        raise ReviewPacketError("cannot load pinned canonical worker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_judgment_packet, module.finding_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "combined", "findings", "packet", "receipt"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--toolkit", type=Path, required=True)
    parser.add_argument("--toolkit-revision", required=True)
    args = parser.parse_args()
    try:
        renderer, finder = load_canonical_worker(args.toolkit)
        packet, receipt = build(
            json.loads(args.manifest.read_text(encoding="utf-8")),
            json.loads(args.combined.read_text(encoding="utf-8")),
            json.loads(args.findings.read_text(encoding="utf-8")),
            renderer, finder, toolkit_revision=args.toolkit_revision)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print("INVALID Registry combined reviewer compatibility:", exc, file=sys.stderr)
        return 1
    args.packet.parent.mkdir(parents=True, exist_ok=True)
    args.packet.write_text(packet, encoding="utf-8")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print("REVIEW PACKET", receipt["finding_count"], "source-bound findings; no issue writes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
