#!/usr/bin/env python3
"""Reconcile an actual transferred-case Toolkit execution into its Registry owner.

Case #88 only in this qualification. The historical Toolkit issue is provenance,
never a mutation target. GitHub comments have no compare-and-swap: apply requires
the shared registry-case-publication lock and an authorized main-branch operator.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as gh
from bind_registry_execution import canonical_bytes, digest
from bind_transferred_execution import (
    bind, ENGINE_REVISION, REG_ISSUE, CASE_ID, GROUP_SHA256, KEY, TK_ISSUE,
)

API = f"https://api.github.com/repos/{gh.REGISTRY}/issues/88"
MARKER = re.compile(r"<!-- rahp-registry-transferred-execution:v1:([0-9a-f]{64}) -->")
WORKFLOW_ACTOR = {"login": "github-actions[bot]", "id": 41898282}
MAX_BYTES = 30000


class ReturnError(ValueError):
    pass


def record_for(case, transfers, spec, evidence, result, binding, *,
               engine_revision, transfer_ledger_revision):
    expected = bind(case, transfers, spec, evidence, result,
                    engine_revision=engine_revision,
                    transfer_ledger_revision=transfer_ledger_revision)
    if canonical_bytes(binding) != canonical_bytes(expected):
        raise ReturnError("execution receipt is not the qualified canonical binding")
    scope = {
        "case_id": CASE_ID,
        "source_group_sha256": GROUP_SHA256,
        "toolkit_engine_revision": ENGINE_REVISION,
        "toolkit_correlation_key": binding["toolkit_correlation_key"],
    }
    record = {
        "schema": "rahp-registry-transferred-execution-record/v1",
        "epoch_id": digest(scope),
        "case_id": CASE_ID,
        "case_url": REG_ISSUE,
        "historical_toolkit_issue_url": TK_ISSUE,
        "transfer_key": KEY,
        "binding": binding,
        "canonical_result": result,
        "assessment_imported": False,
        "specialist_return_received": False,
        "toolkit_legacy_issue_worker_dispatched": False,
        "controller_cutover_qualified": False,
    }
    if len(canonical_bytes(record)) > MAX_BYTES:
        raise ReturnError("bounded execution exceeds issue-comment limit")
    return record


def render(record):
    return "\n".join((
        f"<!-- rahp-registry-transferred-execution:v1:{record['epoch_id']} -->",
        "## Canonical Toolkit execution returned to Registry (evidence-required)",
        "",
        f"- Case: `{record['case_id']}` / {record['case_url']}",
        f"- Historical Toolkit issue (not dispatched): {record['historical_toolkit_issue_url']}",
        f"- Toolkit execution identity: `{record['binding']['toolkit_execution_id']}`",
        f"- Result: `{record['canonical_result']['outcome']}` / `{record['canonical_result']['reason_code']}`",
        "",
        "The exact normalized controller result and verified Registry binding follow. ",
        "This is an execution *observation*, not independent assurance, reviewer",
        "acceptance, specialist return, authorization of a legacy issue worker,",
        "or a portfolio-wide publisher migration.",
        "",
        "```json", json.dumps(record, sort_keys=True, indent=2), "```",
    ))


def check_owner(issue):
    if (not isinstance(issue, dict) or issue.get("number") != 88
            or issue.get("state") != "open" or issue.get("html_url") != REG_ISSUE):
        raise ReturnError("live Registry #88 is not the active owner")
    body = issue.get("body") or ""
    for marker in (
        f"<!-- rahp-registry-case:{CASE_ID} -->",
        f"<!-- registry-assessment-key:{KEY} -->",
        GROUP_SHA256, TK_ISSUE,
    ):
        if marker not in body:
            raise ReturnError("live Registry case source identity differs")


def find_record(comments, record):
    if not isinstance(comments, list):
        raise ReturnError("Registry comment history unavailable")
    matches = []
    for comment in comments:
        if not isinstance(comment, dict):
            raise ReturnError("malformed Registry comment history")
        markers = MARKER.findall(comment.get("body") or "")
        if record["epoch_id"] in markers:
            matches.append(comment)
    if len(matches) > 1:
        raise ReturnError("duplicate Toolkit execution returns for one case epoch")
    if not matches:
        return None
    found = matches[0]
    actor = found.get("user")
    if (not isinstance(actor, dict)
            or actor.get("id") != WORKFLOW_ACTOR["id"]
            or actor.get("login") != WORKFLOW_ACTOR["login"]):
        raise ReturnError("return marker was not written by the expected workflow actor")
    if found.get("body") != render(record):
        raise ReturnError("conflicting canonical result for already-returned case epoch")
    number = found.get("id")
    if type(number) is not int or number < 1 or (
        found.get("html_url") != REG_ISSUE + "#issuecomment-" + str(number)
    ):
        raise ReturnError("Registry return acknowledgment identity is invalid")
    return found


def read_comments(token):
    rows = []
    for page in range(1, 101):
        part = gh.request("GET", API + f"/comments?per_page=100&page={page}", token)
        if not isinstance(part, list):
            raise ReturnError("comment page unavailable")
        rows.extend(part)
        if len(part) < 100:
            return rows
    raise ReturnError("unbounded Registry comment history")


def reconcile(record, token, *, apply=False, exclusive_lock=False,
              get_issue=None, get_comments=None, post=None):
    if not token:
        raise ReturnError("read/write Registry token missing")
    get_issue = get_issue or (lambda: gh.request("GET", API, token))
    get_comments = get_comments or (lambda: read_comments(token))
    post = post or (lambda body: gh.request(
        "POST", API + "/comments", token, {"body": body}))
    check_owner(get_issue())
    old = find_record(get_comments(), record)
    receipt = {
        "schema": "rahp-registry-transferred-execution-return-receipt/v1",
        "case_id": CASE_ID,
        "epoch_id": record["epoch_id"],
        "binding_key": record["binding"]["binding_key"],
        "state": "pending",
        "mode": "apply" if apply else "read_only",
        "case_determination_imported": False,
        "toolkit_legacy_issue_worker_dispatched": False,
        "specialist_return_authenticated": False,
        "controller_cutover_qualified": False,
    }
    if old:
        return {**receipt, "state": "acknowledged", "comment_url": old["html_url"],
                "comment_id": old["id"], "replay": True}
    if not apply:
        return receipt
    if not exclusive_lock:
        raise ReturnError("effectful return requires serialized exclusive Registry publisher")
    response, error = None, None
    try:
        response = post(render(record))
    except Exception as exc:
        error = exc
    # Never accept the POST response itself as delivery evidence.
    observed = find_record(get_comments(), record)
    check_owner(get_issue())
    if observed is None:
        raise ReturnError("canonical return not durably acknowledged; do not retry blindly") from error
    if response is not None and (
        not isinstance(response, dict) or response.get("id") != observed["id"]
        or response.get("html_url") != observed["html_url"]
    ):
        raise ReturnError("POST receipt conflicts with authoritative Registry case history")
    return {**receipt, "state": "acknowledged",
            "comment_url": observed["html_url"], "comment_id": observed["id"],
            "recovered_ambiguous_post": error is not None, "replay": False}



def require_write_context(env):
    is_main_owner = (
        env.get("GITHUB_REF") == "refs/heads/main"
        and env.get("GITHUB_REPOSITORY") == gh.REGISTRY
        and env.get("GITHUB_ACTOR") == "sankarshanmukhopadhyay"
    )
    event = env.get("GITHUB_EVENT_NAME")
    approved_push = (
        event == "push"
        and "Registry-Case-88-Return-Authorization: " + GROUP_SHA256
        in env.get("REGISTRY_RETURN_COMMIT_MESSAGE", "")
    )
    if not is_main_owner or not (event == "workflow_dispatch" or approved_push):
        raise ReturnError("effectful return lacks owner-authorized Registry main dispatch/push")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("case", "transfer-ledger", "spec", "evidence-ledger",
                "result", "binding", "receipt"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--engine-revision", required=True)
    p.add_argument("--transfer-ledger-revision", required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    receipt = {"schema": "rahp-registry-transferred-execution-return-receipt/v1",
               "state": "indeterminate", "case_determination_imported": False}
    try:
        data = [json.loads(getattr(args, k).read_text(encoding="utf-8")) for k in (
            "case", "transfer_ledger", "spec", "evidence_ledger", "result", "binding")]
        record = record_for(*data, engine_revision=args.engine_revision,
                            transfer_ledger_revision=args.transfer_ledger_revision)
        if args.apply:
            require_write_context(os.environ)
        receipt = reconcile(record, os.getenv("REGISTRY_EXECUTION_TOKEN", ""),
                            apply=args.apply, exclusive_lock=args.apply)
    except (OSError, ValueError, KeyError, TypeError, gh.IntakeError) as exc:
        receipt["error"] = str(exc)
        print(f"UNACKNOWLEDGED transferred execution: {exc}", file=sys.stderr)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if receipt["state"] == "indeterminate":
        return 1
    print("Transferred Registry execution return:", receipt["state"],
          "(no assurance import)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
