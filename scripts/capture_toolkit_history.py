#!/usr/bin/env python3
"""Capture GitHub source issue bodies, comments and issue events, without transferring authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

REPOSITORY = "sankarshanmukhopadhyay/rahp-toolkit"
API = "https://api.github.com/repos/" + REPOSITORY
ISSUE_URL = re.compile(r"^https://api.github.com/repos/sankarshanmukhopadhyay/rahp-toolkit/issues/(\d+)$")


class CaptureError(RuntimeError):
    pass


def request_json(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "rahp-registry-source-archive/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise CaptureError(f"GitHub HTTP {exc.code} while reading source archive") from None
    except urllib.error.URLError:
        raise CaptureError("GitHub source retrieval unavailable") from None


def fetch_pages(endpoint, token, *, limit=200, requester=request_json):
    records = []
    for page in range(1, limit + 1):
        uri = f"{API}/{endpoint}?per_page=100&page={page}"
        items = requester(uri, token)
        if not isinstance(items, list):
            raise CaptureError(f"malformed source API collection: {endpoint}")
        records.extend(items)
        if len(items) < 100:
            return records, page
    raise CaptureError(f"incomplete source pagination after {limit} pages: {endpoint}")


def issue_number_from_url(url):
    if not isinstance(url, str):
        return None
    match = ISSUE_URL.fullmatch(url)
    return int(match.group(1)) if match else None


def assemble(issue_list, comments, events):
    if not all(isinstance(v, list) for v in (issue_list, comments, events)):
        raise CaptureError("source collections must be lists")
    issues = [r for r in issue_list if isinstance(r, dict) and "pull_request" not in r]
    identifiers = {r.get("number") for r in issues}
    if len(identifiers) != len(issues) or None in identifiers or not issues:
        raise CaptureError("duplicate, absent, or empty source issue identities")
    for item in issues:
        n = item["number"]
        if item.get("html_url") != f"https://github.com/{REPOSITORY}/issues/{n}":
            raise CaptureError(f"source issue URL mismatch: #{n}")
    accepted_comments = [r for r in comments if issue_number_from_url(r.get("issue_url")) in identifiers]
    accepted_events = [r for r in events if isinstance(r.get("issue"), dict)
                       and r["issue"].get("number") in identifiers]
    actual_counts = Counter(issue_number_from_url(r.get("issue_url")) for r in accepted_comments)
    for issue in issues:
        if actual_counts[issue["number"]] != issue.get("comments", 0):
            raise CaptureError(f"comment count mismatch for issue #{issue['number']} (capture incomplete)")
    if len({r.get("id") for r in accepted_comments}) != len(accepted_comments):
        raise CaptureError("duplicate comment IDs in source")
    if len({r.get("id") for r in accepted_events}) != len(accepted_events):
        raise CaptureError("duplicate issue event IDs in source")
    return (sorted(issues, key=lambda x: x["number"]),
            sorted(accepted_comments, key=lambda x: x["id"]),
            sorted(accepted_events, key=lambda x: x["id"]))


def write_archive(output, records):
    output.mkdir(parents=True, exist_ok=True)
    digest = {}
    for name, collection in records.items():
        content = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                          + "\n" for x in collection).encode("utf-8")
        (output / f"{name}.jsonl").write_bytes(content)
        digest[name] = {"count": len(collection), "sha256": hashlib.sha256(content).hexdigest()}
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-pages", type=int, default=200)
    args = parser.parse_args()
    if args.max_pages < 1:
        raise CaptureError("max-pages must be positive")
    token = os.environ.get("SOURCE_ARCHIVE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise CaptureError("GitHub read token unavailable")
    source, n1 = fetch_pages("issues", token, limit=args.max_pages)
    comments, n2 = fetch_pages("issues/comments", token, limit=args.max_pages)
    events, n3 = fetch_pages("issues/events", token, limit=args.max_pages)
    issues, comments, events = assemble(source, comments, events)
    integrity = write_archive(args.output, {"issues": issues, "comments": comments, "events": events})
    manifest = {
        "schema": "rahp-source-issue-history-export/v1",
        "source_repository": REPOSITORY,
        "source_collections": {
            "issues": n1, "issues/comments": n2, "issues/events": n3,
        },
        "records": integrity,
        "original_source_authoritative": True,
        "complete_full_timeline_mirror": False,
        "scope_note": (
            "Captures GitHub issue list, issue comments and repository-wide issue events; "
            "does not separately retrieve issue-specific timeline-only event classes, "
            "linked artifacts or independently verify every embedded external URL. "
            "Raw API issue/comment/event records preserve source authorship as returned."
        ),
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["count"] for k, v in integrity.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
