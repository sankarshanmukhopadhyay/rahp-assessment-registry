#!/usr/bin/env python3
"""Read-only compressed history integrity and privacy-amplification screening."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path

EXPECTED = {"issues": 769, "comments": 1797, "events": 6967}
SOURCE = "sankarshanmukhopadhyay/rahp-toolkit"
TOKENS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}"),
    "cloud_access_key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "bearer_credential": re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{28,}", re.I),
}
CONTACT = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class HistoryError(ValueError):
    pass


def verify(directory, expected=EXPECTED):
    if directory.is_symlink() or not directory.is_dir():
        raise HistoryError("invalid archive directory")
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest.get("schema") != "rahp-registry-source-history-package/v1"
            or manifest.get("source_repository") != SOURCE
            or manifest.get("complete_full_timeline_mirror") is not False
            or set(manifest.get("files", {})) != set(expected)):
        raise HistoryError("unsupported history publication claim")
    records = {}
    for kind, minimum in expected.items():
        path = directory / (kind + ".jsonl.gz")
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_000_000:
            raise HistoryError(kind + ": missing or oversized archive")
        compressed = path.read_bytes()
        metadata = manifest["files"][kind]
        if (len(compressed) != metadata["gzip_bytes"]
                or hashlib.sha256(compressed).hexdigest() != metadata["gzip_sha256"]):
            raise HistoryError(kind + ": compressed content digest mismatch")
        sha = hashlib.sha256()
        count = 0
        size = 0
        risky = {k: 0 for k in TOKENS}
        contact_count = 0
        issue_ids = set()
        with gzip.open(path, "rb") as stream:
            for line in stream:
                count += 1
                size += len(line)
                if len(line) > 4_000_000 or size > 250_000_000:
                    raise HistoryError(kind + ": decompression bound exceeded")
                if not line.endswith(b"\n"):
                    raise HistoryError(kind + ": truncated record")
                sha.update(line)
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise HistoryError(kind + ": invalid record")
                if kind == "issues":
                    number = item.get("number")
                    if (type(number) is not int or number < 1
                            or number in issue_ids or item.get("html_url") !=
                            f"https://github.com/{SOURCE}/issues/{number}"):
                        raise HistoryError("source issue identity mismatch")
                    issue_ids.add(number)
                body = " ".join(str(item.get(field) or "")
                                for field in ("body", "title"))
                for name, pattern in TOKENS.items():
                    risky[name] += bool(pattern.search(body))
                contact_count += bool(CONTACT.search(body))
        if count != metadata["source_count"] or sha.hexdigest() != metadata["raw_sha256"]:
            raise HistoryError(kind + ": raw content count/digest mismatch")
        if count < minimum:
            raise HistoryError(kind + ": incomplete historical capture")
        records[kind] = {"count": count, "raw_and_gzip_digests_valid": True,
                         "potential_sensitive_records": risky,
                         "contact_detail_records": contact_count}
    return {"schema": "rahp-registry-source-history-review/v1",
            "source_repository": SOURCE,
            "verified": records,
            "source_history_integrity_verified": True,
            "privacy_approved": False,
            "full_issue_timeline_verified": False,
            "archival_completion_gate_met": False,
            "cutover_authorized": False,
            "interpretation": "Pattern screening is not exhaustive or permission to republish."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS verified source archive bytes/counts; privacy and timeline gate remain open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
