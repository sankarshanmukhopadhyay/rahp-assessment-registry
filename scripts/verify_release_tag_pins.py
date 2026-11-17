#!/usr/bin/env python3
"""Verify source-observed annotated release tag provenance without mutating Monitor."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
import registry_intake

SHA = re.compile(r"^[0-9a-f]{40}$")
TAG = re.compile(r"^[A-Za-z0-9._-]+$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class TagPinError(ValueError):
    pass


def qualify(manifest, findings, fetch):
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "items"}:
        raise TagPinError("unexpected qualification manifest")
    if manifest["schema"] != "rahp-registry-annotated-tag-evidence/v1":
        raise TagPinError("unknown tag evidence schema")
    entries = manifest["items"]
    if not isinstance(entries, list) or not entries:
        raise TagPinError("tag evidence items required")
    if not isinstance(findings, list):
        raise TagPinError("monitored findings must be an array")
    by_id = {}
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("finding_id"), str):
            raise TagPinError("malformed monitored source finding")
        if finding["finding_id"] in by_id:
            raise TagPinError("duplicate monitored source finding")
        by_id[finding["finding_id"]] = finding
    seen = set()
    records = []
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) !=
                {"finding_id", "repository", "tag_name", "tag_object_sha", "target_commit_sha"}):
            raise TagPinError("unsupported tag evidence fields")
        fid, repo, name = (entry["finding_id"], entry["repository"],
                           entry["tag_name"])
        tag_sha, target_sha = entry["tag_object_sha"], entry["target_commit_sha"]
        if not isinstance(fid, str) or not re.fullmatch(r"[0-9a-f]{20}", fid):
            raise TagPinError("invalid finding identity")
        if fid in seen:
            raise TagPinError("duplicate tagged finding")
        seen.add(fid)
        if (not isinstance(repo, str) or not REPO.fullmatch(repo)
                or not isinstance(name, str) or not TAG.fullmatch(name)
                or not isinstance(tag_sha, str) or not SHA.fullmatch(tag_sha)
                or not isinstance(target_sha, str) or not SHA.fullmatch(target_sha)):
            raise TagPinError("invalid tag or immutable source identity")
        finding = by_id.get(fid)
        if not finding or finding.get("repository") != repo:
            raise TagPinError("tag evidence does not match observed repository and finding")
        observed_url = f"https://github.com/{repo}/releases/tag/{name}"
        if observed_url not in (finding.get("evidence_urls") or []):
            raise TagPinError("tag release URL absent from monitored source evidence")
        base = f"https://api.github.com/repos/{repo}/git"
        ref = fetch(base + "/ref/tags/" + name)
        if (not isinstance(ref, dict) or not isinstance(ref.get("object"), dict)
                or ref["object"].get("type") != "tag"
                or ref["object"].get("sha") != tag_sha):
            raise TagPinError("tag reference missing, retargeted, or not annotated")
        tag = fetch(base + "/tags/" + tag_sha)
        if (not isinstance(tag, dict) or tag.get("tag") != name
                or not isinstance(tag.get("object"), dict)
                or tag["object"].get("type") != "commit"
                or tag["object"].get("sha") != target_sha):
            raise TagPinError("annotated tag object has conflicting commit target")
        records.append({
            "finding_id": fid, "repository": repo, "source_tag_url": observed_url,
            "immutable_tag_object_sha": tag_sha,
            "supplemental_verified_target_commit": target_sha,
            "source_observed_commit_url": False,
            "source_observed_tag_url": True,
            "verified": True,
        })
    return {
        "schema": "rahp-registry-release-tag-source-qualification/v1",
        "verification": "live-annotated-tag-reference-and-object",
        "qualified_count": len(records),
        "supplemental_verified": records,
        "source_findings_modified": False,
        "ownership_transfer_accepted": False,
        "new_case_created": False,
        "cutover_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise TagPinError("read-only token required for live tag verification")
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        findings = json.loads(args.findings.read_text(encoding="utf-8"))
        report = qualify(evidence, findings,
                         lambda url: registry_intake.request("GET", url, token))
    except (OSError, ValueError, TypeError, KeyError, registry_intake.IntakeError) as exc:
        print("INVALID release tag qualification:", exc, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Supplemental tag-to-commit evidence verified:", report["qualified_count"],
          "(source records unchanged; no authority transfer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
