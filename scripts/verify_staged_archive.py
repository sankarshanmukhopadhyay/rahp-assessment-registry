#!/usr/bin/env python3
"""Verify committed Toolkit history package and canonical source identities; not RAHP PASS."""
import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SOURCE = "sankarshanmukhopadhyay/rahp-toolkit"
SUSPECT = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"ghp_[A-Za-z0-9]{36}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{48,}"),
)


def sha(content):
    return hashlib.sha256(content).hexdigest()


def check(path: Path):
    errors = []
    meta = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if meta.get("schema") != "rahp-registry-source-history-package/v1":
        errors.append("wrong package schema")
    if meta.get("source_repository") != SOURCE:
        errors.append("wrong source")
    if meta.get("complete_full_timeline_mirror") is not False:
        errors.append("false complete-timeline claim")
    result = {}
    for key in ("issues", "comments", "events"):
        f = path / f"{key}.jsonl.gz"
        if not f.is_file():
            errors.append(f"missing {key} archive")
            continue
        compressed = f.read_bytes()
        details = (meta.get("files") or {}).get(key, {})
        if sha(compressed) != details.get("gzip_sha256"):
            errors.append(f"{key} compressed digest mismatch")
            continue
        try:
            raw = gzip.decompress(compressed)
        except (OSError, EOFError):
            errors.append(f"{key} corrupt gzip")
            continue
        if sha(raw) != details.get("raw_sha256"):
            errors.append(f"{key} raw digest mismatch")
        if any(p.search(raw) for p in SUSPECT):
            errors.append(f"{key} possible credential exposure requires review")
        try:
            data = [json.loads(line) for line in raw.splitlines()]
        except ValueError:
            errors.append(f"{key} malformed JSONL")
            continue
        if len(data) != details.get("source_count"):
            errors.append(f"{key} record count mismatch")
        result[key] = data
    if len(result) != 3:
        return errors
    issues, comments, events = (result[k] for k in ("issues", "comments", "events"))
    numbers = [i.get("number") for i in issues]
    if len(issues) != 769 or len(set(numbers)) != 769:
        errors.append("source issue baseline must contain 769 distinct issues")
    states = Counter(i.get("state") for i in issues)
    if states != {"closed": 712, "open": 57}:
        errors.append("historical open/closed source baseline mismatch")
    for item in issues:
        n = item.get("number")
        if not isinstance(n, int) or item.get("html_url") != f"https://github.com/{SOURCE}/issues/{n}" or "pull_request" in item:
            errors.append("source issue authority/path mismatch")
            break
    known = set(numbers)
    comment_count = Counter()
    comment_ids = []
    for item in comments:
        comment_ids.append(item.get("id"))
        url = str(item.get("issue_url") or "")
        m = re.fullmatch(r"https://api.github.com/repos/sankarshanmukhopadhyay/rahp-toolkit/issues/(\d+)", url)
        if not m or int(m.group(1)) not in known:
            errors.append("comment not attached to original source issue")
            break
        comment_count[int(m.group(1))] += 1
    if len(set(comment_ids)) != len(comments):
        errors.append("duplicate source comment ID")
    for item in issues:
        if comment_count[item["number"]] != item.get("comments"):
            errors.append(f"source comment count mismatch on #{item['number']}")
            break
    if len({x.get("id") for x in events}) != len(events):
        errors.append("duplicate source event ID")
    if any((x.get("issue") or {}).get("number") not in known for x in events):
        errors.append("event outside source issue set")
    if not any("rahp-assessment-registry/issues/4" in (c.get("body") or "")
               for c in comments if str(c.get("issue_url") or "").endswith("/issues/1203")):
        errors.append("pilot source issue #1203 successor provenance missing")
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--path", type=Path, required=True)
    args = p.parse_args()
    errors = check(args.path)
    for error in errors:
        print("INVALID:", error)
    if errors:
        raise SystemExit(1)
    print("PASS committed source history integrity and provenance; not a complete timeline mirror or RAHP PASS")


if __name__ == "__main__":
    main()
