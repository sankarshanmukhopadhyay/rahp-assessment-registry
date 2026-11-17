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


def qualify_combined_groups(report, findings, combined):
    """Bind all grouped observations to exact observed commits or live tag evidence.

    A complete source chain is NOT acceptance of an assessment owner, current
    observation delivery, execution, or publisher cutover.
    """
    if (not isinstance(report, dict) or
            report.get("schema") != "rahp-registry-release-tag-source-qualification/v1" or
            report.get("verification") != "live-annotated-tag-reference-and-object" or
            report.get("cutover_authorized") is not False):
        raise TagPinError("invalid verified tag qualification receipt")
    if not isinstance(findings, list) or not isinstance(combined, list) or not combined:
        raise TagPinError("observed findings and combined groups required")
    source = {}
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("finding_id"), str):
            raise TagPinError("invalid monitored finding")
        fid = finding["finding_id"]
        if fid in source:
            raise TagPinError("duplicated source finding")
        source[fid] = finding
    tagged = {}
    for entry in report.get("supplemental_verified", []):
        fid = entry.get("finding_id") if isinstance(entry, dict) else None
        if fid in tagged or not fid or entry.get("verified") is not True:
            raise TagPinError("duplicate or unverified supplemental tag")
        tagged[fid] = entry
    covered, grouped, groups = set(), set(), []
    url_pattern = re.compile(r"^https://github[.]com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/commit/([0-9a-f]{40})$")
    for event in combined:
        if not isinstance(event, dict) or not isinstance(event.get("source_observations"), list):
            raise TagPinError("combined event lacks structured source observations")
        key = event.get("assessment_key")
        if not isinstance(key, str) or key in grouped:
            raise TagPinError("duplicate or invalid combined group key")
        grouped.add(key)
        direct_pins, direct_count, supplemental_count = set(), 0, 0
        expected_unanchored = []
        seen = set()
        for observed in event["source_observations"]:
            fid = observed.get("finding_id") if isinstance(observed, dict) else None
            if not fid or fid in seen or fid in covered or fid not in source:
                raise TagPinError("missing or duplicated grouped finding identity")
            seen.add(fid)
            covered.add(fid)
            finding = source[fid]
            repo = finding.get("repository")
            if observed.get("repository") != repo:
                raise TagPinError("combined observation differs from source repository")
            revisions = set()
            evidence = finding.get("evidence_urls") or []
            if not isinstance(evidence, list):
                raise TagPinError("malformed source evidence URLs")
            for url in evidence:
                if not isinstance(url, str):
                    raise TagPinError("malformed source evidence URL")
                match = url_pattern.fullmatch(url)
                if match and match.group(1) == repo:
                    revisions.add(match.group(2))
                    direct_pins.add((repo, match.group(2)))
            if observed.get("revisions") != sorted(revisions) or observed.get(
                    "source_pin_status") != ("commit-evidence" if revisions else "unresolved"):
                raise TagPinError("combined machine evidence differs from observed source")
            if revisions:
                direct_count += 1
                if fid in tagged:
                    raise TagPinError("supplemental tag illegally replaced direct commit")
            else:
                expected_unanchored.append(fid)
                claim = tagged.get(fid)
                if (not claim or claim.get("repository") != repo or
                        claim.get("source_tag_url") not in evidence or
                        claim.get("source_observed_commit_url") is not False or
                        not SHA.fullmatch(str(claim.get("supplemental_verified_target_commit", "")))):
                    raise TagPinError("group has unresolved source finding: " + fid)
                supplemental_count += 1
        if (event.get("unanchored_finding_ids") != sorted(expected_unanchored) or
                event.get("source_pins") != [
                    {"repository": repo, "revision": rev} for repo, rev in sorted(direct_pins)]):
            raise TagPinError("combined group source pin/coverage list has drifted")
        groups.append({"assessment_key": key, "finding_count": len(seen),
                       "observed_commit_findings": direct_count,
                       "supplemental_annotated_tag_findings": supplemental_count,
                       "source_provenance_qualified": True,
                       "case_owner_accepted": False})
    if set(tagged) != set(event_id for group in combined
                           for event_id in group["unanchored_finding_ids"]):
        raise TagPinError("supplemental evidence does not correspond exactly to grouped gaps")
    return {"schema": "rahp-registry-combined-group-source-evidence/v1",
            "groups": sorted(groups, key=lambda item: item["assessment_key"]),
            "finding_count": len(covered),
            "observed_commit_findings": sum(x["observed_commit_findings"] for x in groups),
            "supplemental_tag_findings": sum(x["supplemental_annotated_tag_findings"] for x in groups),
            "source_provenance_qualified": True,
            "snapshot_updated": False,
            "new_case_created": False,
            "current_observation_delivered": False,
            "toolkit_publication_suppressed": False,
            "controller_consumer_migrated": False,
            "independent_review_accepted": False,
            "cutover_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--combined-events", type=Path,
                        help="also require complete grouped source provenance from canonical router")
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
        if args.combined_events is not None:
            combined = json.loads(args.combined_events.read_text(encoding="utf-8"))
            report["group_source_qualification"] = qualify_combined_groups(
                report, findings, combined)
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
