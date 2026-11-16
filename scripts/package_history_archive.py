#!/usr/bin/env python3
"""Package a verified GitHub history export as deterministic compressed archive files."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


class PackageError(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package(source, target, min_issues=769):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "rahp-source-issue-history-export/v1":
        raise PackageError("unexpected source archive schema")
    if manifest.get("source_repository") != "sankarshanmukhopadhyay/rahp-toolkit":
        raise PackageError("not Toolkit source archive")
    if manifest.get("complete_full_timeline_mirror") is not False:
        raise PackageError("invalid archive scope claim")
    records = manifest.get("records", {})
    if records.get("issues", {}).get("count", 0) < min_issues:
        raise PackageError("incomplete historical source issue coverage")
    staged = {}
    for name in ("issues", "comments", "events"):
        path = source / f"{name}.jsonl"
        raw = path.read_bytes()
        expected = records.get(name, {})
        if sha(raw) != expected.get("sha256"):
            raise PackageError(f"{name}: raw content digest mismatch")
        if raw.count(b"\n") != expected.get("count"):
            raise PackageError(f"{name}: record count mismatch")
        if not raw or not raw.endswith(b"\n"):
            raise PackageError(f"{name}: empty or truncated source")
        target.mkdir(parents=True, exist_ok=True)
        data = gzip.compress(raw, compresslevel=9, mtime=0)
        (target / f"{name}.jsonl.gz").write_bytes(data)
        if gzip.decompress(data) != raw:
            raise PackageError(f"{name}: gzip roundtrip mismatch")
        staged[name] = {"source_count": expected["count"], "raw_sha256": sha(raw),
                        "gzip_sha256": sha(data), "gzip_bytes": len(data)}
    receipt = {
        "schema": "rahp-registry-source-history-package/v1",
        "source_repository": manifest["source_repository"],
        "capture": manifest,
        "files": staged,
        "content_authority": "original GitHub issue/comment/event source URLs",
        "complete_full_timeline_mirror": False,
        "accepted_assurance_determinations": 0,
        "scope_note": "Portable source-history package only. Does not include per-issue timeline-only events, external attachments or upstream evidence bytes; no authority transfer.",
    }
    (target / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--target", required=True, type=Path)
    args = p.parse_args()
    record = package(args.source, args.target)
    print(json.dumps({k: v["source_count"] for k, v in record["files"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
