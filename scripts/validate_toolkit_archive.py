#!/usr/bin/env python3
"""Validate a source-pinned issue-metadata inventory, never a RAHP assurance result."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"external-assessment-candidate", "mixed-review", "development-or-unclassified"}
SOURCE = "sankarshanmukhopadhyay/rahp-toolkit"


def verify(manifest, parts):
    errors = []
    def check(ok, reason):
        if not ok:
            errors.append(reason)
    check(isinstance(manifest, dict), "manifest must be a mapping")
    if not isinstance(manifest, dict):
        return errors
    check(manifest.get("schema") == "rahp-toolkit-issue-metadata-archive/v1", "bad schema")
    check(manifest.get("source_repository") == SOURCE, "unexpected source repo")
    check(manifest.get("full_content_mirror") is False, "metadata index cannot claim full mirror")
    check(manifest.get("source_pages", 0) >= 1, "missing pagination evidence")
    partitions = manifest.get("partitions")
    check(isinstance(partitions, list) and len(partitions) == len(parts), "partition count mismatch")
    if not isinstance(partitions, list) or len(partitions) != len(parts):
        return errors
    ids = []
    states = Counter()
    for part, records in zip(partitions, parts):
        check(isinstance(records, list), "part must contain a list")
        if not isinstance(records, list):
            continue
        check(part.get("expected_issues") == len(records), "partition issue count mismatch")
        for item in records:
            if not isinstance(item, dict):
                errors.append("issue entry is not an object")
                continue
            n = item.get("number")
            check(type(n) is int and n > 0, "invalid source issue ID")
            if type(n) is not int or n <= 0:
                continue
            ids.append(n)
            check(item.get("url") == f"https://github.com/{SOURCE}/issues/{n}", f"wrong source URL #{n}")
            check(item.get("state") in ("open", "closed"), f"invalid state #{n}")
            check(item.get("classification") in KINDS, f"invalid routing class #{n}")
            check(isinstance(item.get("title"), str) and bool(item["title"].strip()), f"missing title #{n}")
            check(type(item.get("comments")) is int and item["comments"] >= 0, f"invalid comment count #{n}")
            check(isinstance(item.get("labels"), list), f"invalid labels #{n}")
            check(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T.+", str(item.get("created_at") or ""))), f"no created timestamp #{n}")
            if item.get("state") == "open":
                check(item.get("closed_at") is None, f"open issue has closure #{n}")
            else:
                check(bool(item.get("closed_at")), f"closed issue missing timestamp #{n}")
            states[item.get("state")] += 1
    check(len(ids) == len(set(ids)), "duplicate source issue IDs")
    check(len(ids) == manifest.get("total_issues"), "total count mismatch")
    check(dict(states) == manifest.get("state_counts"), "state count mismatch")
    check(any(i.get("number") == 1203 and i.get("registry_successor", "").endswith("/issues/4")
              for records in parts for i in records if isinstance(i, dict)), "pilot successor lost")
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=ROOT / "archive/manifest.json")
    args = p.parse_args()
    meta = json.loads(args.manifest.read_text(encoding="utf-8"))
    parts = [json.loads((ROOT / item["path"]).read_text(encoding="utf-8"))
             for item in meta["partitions"]]
    failures = verify(meta, parts)
    for failure in failures:
        print("FAIL", failure)
    if failures:
        raise SystemExit(1)
    print(f"PASS metadata archive: {meta['total_issues']} source issues "
          "(not a full-content mirror, transfer or assurance result)")


if __name__ == "__main__":
    main()
