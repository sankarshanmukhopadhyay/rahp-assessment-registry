#!/usr/bin/env python3
"""Read-only live replay of a real Toolkit/DPIP return through canonical consumer.

Historical fixture: Toolkit #1116, DPIP #304 and #305 (duplicate examination
epoch), Toolkit residual #1117. No Registry cutover or assurance PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

TOOLKIT_REV = "70298566dc897669e22bf37759843d6b7c0597d2"
SOURCE_REPO = "sankarshanmukhopadhyay/rahp-toolkit"
DPIP_REPO = "sankarshanmukhopadhyay/dtg-privacy-implementation-profile"
SOURCE_ISSUE = 1116
TARGET_ISSUES = (304, 305)
EXAM_RE = re.compile(r"<!-- rahp-dpip-examination:([a-zA-Z0-9]+) -->")


class ConsumerError(ValueError):
    pass


def api(repo, path):
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "rahp-registry-dpip-readonly-preflight",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def comments(repo, issue):
    out = []
    for page in range(1, 20):
        items = api(repo, f"issues/{issue}/comments?per_page=100&page={page}")
        if not isinstance(items, list):
            raise ConsumerError("malformed source comment response")
        out.extend(items)
        if len(items) < 100:
            return out
    raise ConsumerError("comment history exceeds bounded pagination")


def examination_key(issue):
    found = EXAM_RE.findall(issue.get("body") or "")
    if len(found) != 1:
        raise ConsumerError("DPIP examination marker missing or ambiguous")
    return found[0]


def verify_historical_links(source, source_comments, targets, target_comments, consumer):
    if source.get("number") != SOURCE_ISSUE or source.get("state") != "closed":
        raise ConsumerError("historical RAHP source issue is not closed #1116")
    if set(targets) != set(TARGET_ISSUES):
        raise ConsumerError("historical DPIP target set changed")
    if any(targets[n].get("number") != n for n in TARGET_ISSUES):
        raise ConsumerError("DPIP issue identity mismatch")
    epochs = [examination_key(targets[n]) for n in TARGET_ISSUES]
    if epochs[0] != epochs[1]:
        raise ConsumerError("expected historical duplicate examination identity absent")
    for n in TARGET_ISSUES:
        body = targets[n].get("body") or ""
        if f"<!-- rahp-dpip-referral:{SOURCE_ISSUE}:" not in body:
            raise ConsumerError("DPIP target missing source referral identity")
        blocks = consumer.yaml_blocks(body)
        original = next((b["source"] for b in blocks if isinstance(b.get("source"), dict)), None)
        if not original or original.get("repository") != SOURCE_REPO or original.get("issue") != SOURCE_ISSUE:
            raise ConsumerError("DPIP target source provenance mismatch")
    parsed = consumer.parse_return(source_comments)
    if not parsed or parsed.get("target_repository") != DPIP_REPO or parsed.get("target_issue") != 305:
        raise ConsumerError("latest source return is not pinned DPIP #305")
    if parsed.get("conclusion") != "INDETERMINATE":
        raise ConsumerError("historical return incorrectly promoted to assurance success")
    if consumer.base_state(parsed["conclusion"], parsed.get("terminal_reason") or "") != "evidence-external":
        raise ConsumerError("historical DPIP evidence gap was not preserved")
    recon = consumer.reconciliation_marker(SOURCE_ISSUE, 305)
    if not any(recon in (c.get("body") or "") for c in source_comments):
        raise ConsumerError("source controller has no matching reconciliation receipt")
    ack = [c for c in target_comments[305]
           if "<!-- rahp-return-ack:v2:305:" in (c.get("body") or "")
           and f"destination: {chr(96)}{SOURCE_REPO}#{SOURCE_ISSUE}{chr(96)}" in (c.get("body") or "")]
    if len(ack) != 1:
        raise ConsumerError("DPIP target has no unique source-specific return acknowledgement")
    return {
        "schema": "rahp-registry-legacy-dpip-consumer-preflight/v1",
        "source": f"https://github.com/{SOURCE_REPO}/issues/{SOURCE_ISSUE}",
        "dpip_targets": [f"https://github.com/{DPIP_REPO}/issues/{n}" for n in TARGET_ISSUES],
        "latest_return_target": 305,
        "conclusion": "INDETERMINATE",
        "normalized_obligation_state": "evidence-external",
        "duplicate_semantic_examination_detected": True,
        "duplicate_is_historical_not_new_execution": True,
        "reconciliation_receipt_observed": True,
        "target_acknowledgement_observed": True,
        "registry_controller_cutover_qualified": False,
        "assurance_pass": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toolkit", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    toolkit = args.toolkit.resolve()
    try:
        rev = subprocess.check_output(["git", "-C", str(toolkit), "rev-parse", "HEAD"],
                                      text=True).strip()
        if rev != TOOLKIT_REV:
            raise ConsumerError("canonical Toolkit source pin mismatch")
        sys.path.insert(0, str(toolkit / "tools"))
        import dpip_return_reconcile as consumer
        source = api(SOURCE_REPO, f"issues/{SOURCE_ISSUE}")
        source_comments = comments(SOURCE_REPO, SOURCE_ISSUE)
        targets = {n: api(DPIP_REPO, f"issues/{n}") for n in TARGET_ISSUES}
        target_comments = {n: comments(DPIP_REPO, n) for n in TARGET_ISSUES}
        result = verify_historical_links(source, source_comments, targets, target_comments, consumer)
        result["toolkit_revision"] = rev
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as exc:
        print(f"INVALID historical DPIP consumer replay: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("PASS historical DPIP consumer parity and duplicate-examination detection; not Registry cutover")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
