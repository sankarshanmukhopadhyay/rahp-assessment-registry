#!/usr/bin/env python3
"""Acknowledge a later source-bound epoch for an already accepted Registry group.

This is not initial ownership transfer, a Toolkit execution adapter, or
assurance acceptance. No new issue owner is ever created here.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

import registry_intake as gh
import registry_monitored_group_delivery as initial
import registry_group_observation_ack as ack
from registry_group_review_packet import group_digest

TK = initial.TK
REG = initial.REG
MON = "sankarshanmukhopadhyay/dtg-portfolio-monitor"
API = initial.API
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FID = re.compile(r"^[0-9a-f]{20}$")
OWNER_PREFIX = "https://github.com/" + REG + "/issues/"


class EpochError(ValueError):
    pass


def accepted_record(intent, ledger):
    if not isinstance(ledger, dict) or ledger.get("schema") != (
            "rahp-registry-transfers/v1") or not isinstance(
                ledger.get("transfers"), list):
        raise EpochError("invalid Toolkit writer authority ledger")
    matches = [x for x in ledger["transfers"] if isinstance(x, dict)
               and x.get("assessment_key") == intent["assessment_key"]]
    if not matches:
        return None
    if len(matches) != 1:
        raise EpochError("ambiguous Toolkit Registry transfer authority")
    row = matches[0]
    if row.get("state") != "accepted_group":
        return None
    for key, expected in (
        ("toolkit_issue_url", intent["toolkit_current_issue_url"]),
        ("monitor_revision", intent["monitor_revision"]),
        ("snapshot_date", intent["snapshot_date"]),
        ("finding_ids", intent["source_finding_ids"]),
        ("group_sha256", intent["source_group_sha256"]),
        ("maintainer_scope_sha256", intent["maintainer_scope_sha256"])):
        if row.get(key) != expected:
            raise EpochError("accepted Toolkit group source/authority mismatch: " + key)
    url = row.get("registry_issue_url")
    if not isinstance(url, str) or not re.fullmatch(
            re.escape(OWNER_PREFIX) + r"[1-9][0-9]*", url):
        raise EpochError("accepted Registry successor lacks canonical issue URL")
    return row


def qualify_epoch(intent, groups, findings, row, issue, monitor_revision):
    if not SHA40.fullmatch(str(monitor_revision)):
        raise EpochError("current Monitor main revision unavailable")
    if not isinstance(groups, list) or not isinstance(findings, list):
        raise EpochError("current router/source evidence must be arrays")
    matches = [g for g in groups if isinstance(g, dict)
               and g.get("assessment_key") == intent["assessment_key"]]
    if not matches:
        return None
    if len(matches) != 1:
        raise EpochError("ambiguous current materiality group")
    group = matches[0]
    digest = group_digest(group)
    if digest == row["group_sha256"]:
        return None
    day = group.get("observed_at")
    if not isinstance(day, str) or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", day):
        raise EpochError("current source snapshot date invalid")
    observed = group.get("source_observations")
    if not isinstance(observed, list) or not observed:
        raise EpochError("current group has no source findings")
    index = {}
    for finding in findings:
        if not isinstance(finding, dict) or not FID.fullmatch(str(finding.get("finding_id"))):
            raise EpochError("malformed monitored source finding")
        fid = finding["finding_id"]
        if fid in index:
            raise EpochError("duplicate monitored finding")
        index[fid] = finding
    ids = []
    for entry in observed:
        if not isinstance(entry, dict):
            raise EpochError("invalid grouped source observation")
        fid = entry.get("finding_id")
        if not isinstance(fid, str) or not FID.fullmatch(fid) or fid in ids:
            raise EpochError("repeated or invalid group member")
        finding = index.get(fid)
        if finding is None or finding.get("repository") != entry.get("repository"):
            raise EpochError("group member is missing from pinned monitored source")
        if (finding.get("state") != "open" or
                finding.get("materiality") not in ("high", "critical") or
                finding.get("assurance_impact") not in ("potentially-breaking", "breaking")):
            raise EpochError("current group includes nonqualifying source finding")
        ids.append(fid)
    if not isinstance(issue, dict) or issue.get("state") != "open" or (
            issue.get("html_url") != row["registry_issue_url"]):
        raise EpochError("Registry successor not current and open")
    expected_number = int(row["registry_issue_url"].removeprefix(OWNER_PREFIX))
    if type(issue.get("number")) is not int or issue["number"] != expected_number:
        raise EpochError("Registry issue identity substituted")
    body = issue.get("body") or ""
    if (gh.marker(intent["assessment_key"]) not in body or
            initial.MARK + row["group_sha256"] + " -->" not in body or
            row["toolkit_issue_url"] not in body):
        raise EpochError("Registry owner is not the original accepted source-group case")
    return {"source_group_sha256": digest, "snapshot_date": day,
            "monitor_revision": monitor_revision,
            "finding_ids": sorted(ids),
            "registry_issue_url": row["registry_issue_url"],
            "registry_issue_number": expected_number}


EPOCH_SCOPE = re.compile(
    r"<!-- rahp-registry-epoch-scope:v1:(accept|withdraw):([0-9a-f]{64}) -->")
SCOPE_ISSUE_NUMBER = 77
MAINTAINER = "sankarshanmukhopadhyay"


def epoch_scope_decision(history, digest):
    """Require a fresh authenticated decision for the exact changed source group.

    The original accepted_group maintainer scope only approves its original
    group digest; a subsequent event is a distinct governance proposition.
    """
    if not isinstance(history, list):
        raise EpochError("Registry epoch authorization history unavailable")
    decisions = []
    observed_ids = set()
    for comment in history:
        if not isinstance(comment, dict):
            raise EpochError("malformed Registry epoch decision history")
        body = comment.get("body") or ""
        matches = EPOCH_SCOPE.findall(body)
        for action, observed in matches:
            if observed != digest:
                continue
            author = comment.get("user") or {}
            comment_id = comment.get("id")
            if (not isinstance(author, dict) or
                    author.get("login") != MAINTAINER or
                    comment.get("author_association") != "OWNER" or
                    type(comment_id) is not int or comment_id < 1 or
                    comment_id in observed_ids):
                raise EpochError("unauthorized or ambiguous source-epoch approval")
            observed_ids.add(comment_id)
            decisions.append((comment_id, action))
    if not decisions:
        return False
    return sorted(decisions)[-1][1] == "accept"


def acknowledgment_body(observation):
    return ("<!-- rahp-registry-observation:v1:" +
            observation["source_group_sha256"] + " -->\n\n" +
            "Registry monitored source observation received for administrative case " +
            observation["registry_issue_url"] + ".\n\n" +
            "- Monitor revision: `" + observation["monitor_revision"] + "`\n" +
            "- Snapshot date: `" + observation["snapshot_date"] + "`\n" +
            "- Group source SHA-256: `" + observation["source_group_sha256"] + "`\n" +
            "- Finding IDs: " + ", ".join("`" + x + "`" for x in observation["finding_ids"]) +
            "\n\nThis is a new source-observation epoch for an accepted Registry administrative owner. " +
            "It does not import Toolkit assurance, specialist conclusions, or a reviewer judgment.")


def observe(intent, groups, findings, ledger, issue, existing_comments,
            monitor_revision, *, apply=False, post=None, reread=None,
            scope_history=None):
    row = accepted_record(intent, ledger)
    if row is None:
        return {"state": "inactive_no_accepted_transfer",
                "observation_acknowledged": False, "issue_written": False,
                "assurance_determination": None}
    current = qualify_epoch(intent, groups, findings, row, issue, monitor_revision)
    if current is None:
        return {"state": "no_changed_group",
                "observation_acknowledged": False, "issue_written": False,
                "assurance_determination": None}
    n = current["registry_issue_number"]
    digest = current["source_group_sha256"]
    old = ack.observed(existing_comments, n, digest)
    scoped = epoch_scope_decision(scope_history if scope_history is not None else [], digest)
    receipt = {"schema": "rahp-registry-new-group-epoch/v1",
               **current, "state": "observed" if old else "pending",
               "comment_url": old.get("html_url") if old else None,
               "observation_acknowledged": old is not None,
               "maintainer_epoch_authorized": scoped,
               "issue_written": False, "assurance_determination": None,
               "toolkit_issue_number_substituted": False,
               "controller_execution_dispatched": False,
               "cutover_authorized": False}
    if old or not apply:
        return receipt
    if not scoped:
        return {**receipt, "state": "pending_epoch_approval"}
    if post is None or reread is None:
        raise EpochError("new source epoch requires controlled POST and authoritative re-read")
    response, error = None, None
    try:
        response = post(acknowledgment_body(current))
    except Exception as exc:
        error = exc
    fresh = ack.observed(reread(), n, digest)
    if fresh is None:
        raise EpochError("new epoch comment not durably acknowledged") from error
    if response is not None and (not isinstance(response, dict)
                                 or fresh["id"] != response.get("id")
                                 or fresh["html_url"] != response.get("html_url")):
        raise EpochError("GitHub POST response differs from observed epoch comment")
    return {**receipt, "state": "observed",
            "comment_url": fresh["html_url"], "observation_acknowledged": True,
            "issue_written": True, "recovered_after_ambiguous_post": error is not None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "combined", "findings", "receipt"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--monitor-revision", required=True)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    receipt = {"schema": "rahp-registry-new-group-epoch/v1",
               "state": "indeterminate", "observation_acknowledged": False,
               "assurance_determination": None}
    try:
        token = os.environ.get("REGISTRY_INTAKE_TOKEN", "")
        if not token:
            raise EpochError("Registry read authorization required")
        if args.apply:
            env = os.environ
            if (env.get("GITHUB_ACTIONS") != "true" or
                    env.get("GITHUB_REF") != "refs/heads/main" or
                    env.get("GITHUB_REPOSITORY") != REG or
                    env.get("GITHUB_EVENT_NAME") not in ("workflow_dispatch", "schedule")):
                raise EpochError("new epoch write requires main-only scheduled/manual Registry workflow")
        get = lambda url: gh.request("GET", url, token)
        toolkit_sha = initial.read_head(get, TK)
        registry_sha = initial.read_head(get, REG)
        monitor_sha = initial.read_head(get, MON)
        if monitor_sha != args.monitor_revision:
            raise EpochError("Monitor main moved since checkout")
        intent = json.loads(args.manifest.read_text(encoding="utf-8"))
        if initial.read_pinned(get, REG, args.manifest.as_posix(), registry_sha) != intent:
            raise EpochError("Registry committed source intent mismatch")
        ledger = initial.read_pinned(get, TK, initial.LEDGER, toolkit_sha)
        row = accepted_record(intent, ledger)
        if row:
            number = int(row["registry_issue_url"].removeprefix(OWNER_PREFIX))
            owner = get(API + REG + "/issues/" + str(number))
            history = ack.comments(number, get)
        else:
            owner, history, number = None, [], None
        def post(body):
            return gh.request("POST", API + REG + "/issues/" + str(number) +
                              "/comments", token, {"body": body})
        approvals = ack.comments(SCOPE_ISSUE_NUMBER, get) if row else []
        receipt = observe(
            intent, json.loads(args.combined.read_text(encoding="utf-8")),
            json.loads(args.findings.read_text(encoding="utf-8")), ledger,
            owner, history, args.monitor_revision, apply=args.apply,
            post=post, reread=lambda: ack.comments(number, get),
            scope_history=approvals)
        if (initial.read_head(get, TK) != toolkit_sha or
                initial.read_head(get, REG) != registry_sha or
                initial.read_head(get, MON) != monitor_sha):
            raise EpochError("authority branch moved during monitored delivery")
    except (OSError, ValueError, TypeError, KeyError, gh.IntakeError) as exc:
        receipt["state"] = "indeterminate"
        receipt["error"] = str(exc)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    if receipt["state"] == "indeterminate":
        print("INVALID monitored source epoch:", receipt.get("error"), file=sys.stderr)
        return 1
    print("Monitored group epoch:", receipt["state"], "(not assurance PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
