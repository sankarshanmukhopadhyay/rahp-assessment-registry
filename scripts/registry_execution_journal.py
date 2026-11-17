#!/usr/bin/env python3
"""Registry-owned, replayable execution journal on the *existing* case issue.

Only publishes a pinned canonical Toolkit result and its independently checked
Registry binding. This is a case-scoped historical execution record, not a
specialist return, a case determination or an operational controller cutover.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as gh
from bind_registry_execution import canonical_bytes, verify_binding, TOOLKIT_REVISION

PREFIX = "<!-- rahp-registry-execution:v1:"
MARKER = re.compile(r"<!-- rahp-registry-execution:v1:([0-9a-f]{32}) -->")
ROOT = f"https://api.github.com/repos/{gh.REGISTRY}"
PILOT_OWNER = 4
MAX_ENTRY_BYTES = 30000
EXPECTED_PUBLISHER_LOGIN = "github-actions[bot]"
EXPECTED_PUBLISHER_USER_ID = 41898282


class JournalError(ValueError):
    pass


def form_entry(case, spec, ledger, result, binding, revision=TOOLKIT_REVISION):
    # This verifies canonical source, outcome, execution, original report digest,
    # and binding integrity. No locally reconstructed RAHP assurance inference.
    verify_binding(binding, case, spec, ledger, result, toolkit_revision=revision)
    if any(binding.get(flag) is not False for flag in (
            "case_determination_imported", "external_specialist_authenticated",
            "delivery_acknowledged", "controller_cutover_qualified")):
        raise JournalError("binding improperly asserts delivery, acceptance or cutover")
    if result.get("outcome") != "INDETERMINATE":
        raise JournalError("pilot execution journal cannot publish a PASS")
    if case["owners"]["current_active_issue"] != f"https://github.com/{gh.REGISTRY}/issues/{PILOT_OWNER}":
        raise JournalError("pilot case active owner mismatch")
    if not re.fullmatch(r"rahp-execution:([0-9a-f]{32})", binding["binding_key"]):
        raise JournalError("unexpected execution binding identity")
    record = {
        "schema": "rahp-registry-execution-record/v1",
        "case_id": case["case_id"],
        "case_url": case["owners"]["current_active_issue"],
        "binding": binding,
        "canonical_result": result,
        "assessment_imported": False,
        "specialist_return_received": False,
    }
    encoded = canonical_bytes(record)
    if len(encoded) > MAX_ENTRY_BYTES:
        raise JournalError("execution record exceeds public case issue bound")
    return record


def comment_text(record):
    key = record["binding"]["binding_key"].split(":", 1)[1]
    return "\n".join((
        f"{PREFIX}{key} -->",
        "## Canonical RAHP execution record (no Registry determination import)",
        "",
        f"- Registry case: `{record['case_id']}`",
        f"- Toolkit execution ID: `{record['binding']['toolkit_assessment_id']}`",
        f"- Source: `{record['binding']['source_pins'][0]['repository']}@{record['binding']['source_pins'][0]['revision']}`",
        f"- Result: **{record['canonical_result']['outcome']}** / "
        f"`{record['canonical_result'].get('reason_code')}`",
        "",
        "The JSON below contains the complete bounded canonical result and its independently verified",
        "case-to-execution binding. This is historical execution evidence, not a specialist",
        "return, an independently accepted assurance determination or a controller cutover.",
        "",
        "```json",
        json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2),
        "```",
    ))


def check_live_case(case, issue):
    if not isinstance(issue, dict) or issue.get("number") != PILOT_OWNER or issue.get("state") != "open":
        raise JournalError("Registry case issue is not the active open pilot owner")
    body = issue.get("body") or ""
    if f"<!-- rahp-registry-case:{case['case_id']} -->" not in body:
        raise JournalError("Registry case identity marker absent")
    for source in (case["source"]["revision"], case["source"]["finding_id"]):
        if source not in body:
            raise JournalError("live case body has diverged from pinned source/finding")


def check_existing(comments, record, text):
    wanted = record["binding"]["binding_key"].split(":", 1)[1]
    matches = []
    if not isinstance(comments, list):
        raise JournalError("GitHub comments response malformed")
    for comment in comments:
        body = comment.get("body") or ""
        markers = MARKER.findall(body)
        if wanted in markers:
            matches.append(comment)
    if len(matches) > 1:
        raise JournalError("multiple execution records with the same canonical identity")
    if len(matches) == 1:
        candidate = matches[0]
        # Public issue comments are user-writable. Matching content is not
        # proof that the authorized workflow publisher performed the write.
        actor = candidate.get("user")
        if (not isinstance(actor, dict)
                or actor.get("id") != EXPECTED_PUBLISHER_USER_ID
                or actor.get("login") != EXPECTED_PUBLISHER_LOGIN):
            raise JournalError("execution marker lacks authorized workflow publisher")
        if candidate.get("body") != text:
            raise JournalError("existing execution identity contains a conflicting result")
        if not isinstance(candidate.get("id"), int) or candidate["id"] <= 0:
            raise JournalError("existing execution lacks durable remote acknowledgment")
        expected = (f"https://github.com/{gh.REGISTRY}/issues/{PILOT_OWNER}"
                    f"#issuecomment-{candidate['id']}")
        if candidate.get("html_url") != expected:
            raise JournalError("execution acknowledgment URL does not match the Registry case")
        return candidate
    return None


def read_comments(token):
    result = []
    for page in range(1, 101):
        values = gh.request("GET", f"{ROOT}/issues/{PILOT_OWNER}/comments?per_page=100&page={page}", token)
        if not isinstance(values, list):
            raise JournalError("malformed GitHub comment page")
        result.extend(values)
        if len(values) < 100:
            return result
    raise JournalError("case comment pagination exceeded upper bound")


def reconcile(record, case, token, *, apply=False, read_issue=None, read_comments_fn=None, post=None):
    """Perform at most one POST; acknowledge only an observable exact comment.

    GitHub Issue comments lack conditional unique-key writes. Callers must hold
    the same exclusive publication lock and deny unrelated concurrent publishers.
    """
    if not token:
        raise JournalError("Registry write/read token missing")
    read_issue = read_issue or (lambda: gh.request("GET", f"{ROOT}/issues/{PILOT_OWNER}", token))
    read_comments_fn = read_comments_fn or (lambda: read_comments(token))
    post = post or (lambda body: gh.request("POST", f"{ROOT}/issues/{PILOT_OWNER}/comments", token,
                                           {"body": body}))
    check_live_case(case, read_issue())
    rendered = comment_text(record)
    existing = check_existing(read_comments_fn(), record, rendered)
    receipt = {
        "schema": "rahp-registry-execution-journal-receipt/v1",
        "case_id": record["case_id"],
        "binding_key": record["binding"]["binding_key"],
        "mode": "apply" if apply else "dry_run",
        "assurance_determination_imported": False,
        "controller_cutover_qualified": False,
    }
    if existing:
        return {**receipt, "state": "acknowledged", "comment_id": existing["id"],
                "comment_url": existing["html_url"]}
    if not apply:
        return {**receipt, "state": "pending", "comment_id": None, "comment_url": None}
    error = None
    response = None
    try:
        response = post(rendered)
    except Exception as exc:
        error = exc
    # A POST response without an exact durable reread is not an acknowledgment.
    observed = check_existing(read_comments_fn(), record, rendered)
    if observed is None:
        raise JournalError("execution journal unacknowledged; retain source intent for replay") from error
    if response is not None and (response.get("id") != observed["id"]
                                 or response.get("html_url") != observed["html_url"]):
        raise JournalError("POST response conflicts with authoritative Registry journal")
    return {**receipt, "state": "acknowledged", "comment_id": observed["id"],
            "comment_url": observed["html_url"], "recovered_ambiguous_post": error is not None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("case", "spec", "ledger", "result", "binding", "receipt"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--toolkit-revision", required=True)
    p.add_argument("--apply", action="store_true", help="explicitly write bounded public Registry issue comment")
    a = p.parse_args()
    receipt = {"schema": "rahp-registry-execution-journal-receipt/v1",
               "state": "indeterminate", "mode": "apply" if a.apply else "dry_run",
               "assurance_determination_imported": False}
    try:
        case, spec, ledger, result, binding = [
            json.loads(getattr(a, name).read_text(encoding="utf-8"))
            for name in ("case", "spec", "ledger", "result", "binding")
        ]
        record = form_entry(case, spec, ledger, result, binding, a.toolkit_revision)
        token = os.environ.get("REGISTRY_EXECUTION_TOKEN", "")
        receipt = reconcile(record, case, token, apply=a.apply)
    except (OSError, ValueError, TypeError, KeyError, gh.IntakeError) as exc:
        receipt["error"] = str(exc)
        print(f"UNACKNOWLEDGED execution journal: {exc}", file=sys.stderr)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if receipt.get("state") == "indeterminate":
        return 1
    print(f"Registry execution journal: {receipt['state']} (not assurance PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
