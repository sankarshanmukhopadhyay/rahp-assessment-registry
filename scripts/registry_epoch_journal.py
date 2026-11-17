#!/usr/bin/env python3
"""Durable, case-scoped record of one DPIP disposition per examination epoch.

This is a *qualified observation* journal, not authentication of specialist
transport, an imported assurance determination, or controller reconciliation.
GitHub issue comments do not have conditional unique-key writes. An applying
caller MUST hold the shared registry-case-publication serialization lock.
"""
from __future__ import annotations

import hashlib
import json
import re

import registry_intake as gh
from registry_specialist_return import REGISTRY, DPIP_REPO, qualify_epoch

MARKER = re.compile(r"<!-- rahp-epoch-disposition:v1:([0-9a-f]{64}) -->")
ACTOR = {"login": "github-actions[bot]", "id": 41898282}
ISSUE = "https://github.com/" + REGISTRY + "/issues/"
DPIP_ISSUE = "https://github.com/" + DPIP_REPO + "/issues/"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class EpochJournalError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def record_for(receipt, case):
    if not isinstance(receipt, dict) or not isinstance(case, dict):
        raise EpochJournalError("qualified receipt and Registry case must be objects")
    expected = {
        "schema": "rahp-registry-dpip-admission-receipt/v1",
        "case_id": case.get("case_id"),
        "case_url": (case.get("owners") or {}).get("current_active_issue"),
    }
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise EpochJournalError("qualified receipt case/owner identity mismatch")
    if (not isinstance(expected["case_url"], str)
            or not re.fullmatch(re.escape(ISSUE) + r"[1-9][0-9]*", expected["case_url"])):
        raise EpochJournalError("noncanonical Registry case owner")
    if (receipt.get("canonical_assessor_schema_validated") is not True
            or receipt.get("outbox_source_ack_chain_observed") is not True):
        raise EpochJournalError("specialist return chain is not qualified")
    for flag in ("return_transport_authenticated", "case_determination_imported",
                 "controller_reconciliation_executed", "operational_cutover_qualified"):
        if receipt.get(flag) is not False:
            raise EpochJournalError("qualified observation cannot claim authority: " + flag)
    pin = receipt.get("source_pin")
    source = case.get("source")
    if (not isinstance(pin, dict) or not isinstance(source, dict)
            or pin.get("repository") != source.get("repository")
            or pin.get("revision") != source.get("revision")
            or not isinstance(pin.get("revision"), str)
            or not SHA40.fullmatch(pin["revision"])):
        raise EpochJournalError("specialist source pin does not match Registry case")
    key = receipt.get("examination_key")
    if not isinstance(key, str) or not key.strip() or key != key.strip() or len(key) > 300:
        raise EpochJournalError("noncanonical examination key")
    source_ref = receipt.get("source_referral_id")
    dpip_url = receipt.get("dpip_issue_url")
    dpip_id = receipt.get("dpip_assessment_id")
    delivery_digest = receipt.get("dpip_return_digest")
    if (not isinstance(source_ref, str) or not source_ref.startswith("rahp-referral:")
            or not isinstance(dpip_url, str) or not re.fullmatch(
                re.escape(DPIP_ISSUE) + r"[1-9][0-9]*", dpip_url)
            or not isinstance(dpip_id, str) or not dpip_id.strip()
            or not isinstance(delivery_digest, str) or not re.fullmatch(
                r"[0-9a-f]{20,64}", delivery_digest)):
        raise EpochJournalError("incomplete specialist return/referral identity")
    if (receipt.get("dpip_outcome_observed") not in
            ("PASS", "FAIL", "NOT_APPLICABLE", "INDETERMINATE")):
        raise EpochJournalError("unknown specialist observation outcome")
    refs = case.get("referrals")
    if not isinstance(refs, list) or sum(
        isinstance(ref, dict) and ref.get("issue_url") == dpip_url
        and ref.get("repository") == DPIP_REPO
        and ref.get("role") == "specialist_assessor"
        and ref.get("contract") == "rahp-assessor-result/v1"
        and ref.get("status") in ("accepted", "returned")
        for ref in refs
    ) != 1:
        raise EpochJournalError("DPIP return has no unique accepted case referral")
    epoch = {"case_id": case["case_id"], "source_pin": pin, "examination_key": key}
    scope_id = digest(epoch)
    record = {
        "schema": "rahp-registry-epoch-observation/v1",
        "epoch_id": scope_id,
        "epoch": epoch,
        "registry_case_url": expected["case_url"],
        "qualified_return": receipt,
        "qualified_return_sha256": digest(receipt),
        "state": "observed_unverified",
        "specialist_transport_authenticated": False,
        "controller_reconciliation_executed": False,
        "case_determination_imported": False,
    }
    return record


def from_offered_runs(case, case_issue, case_comments, runs, consumer, assessor_contract):
    """Use the existing canonical consumer first, before proposing persistence."""
    receipts = qualify_epoch(case, case_issue, case_comments, runs, consumer, assessor_contract)
    return [record_for(receipt, case) for receipt in receipts]


def comment_text(record):
    if record.get("schema") != "rahp-registry-epoch-observation/v1":
        raise EpochJournalError("unknown epoch record schema")
    return "\n".join((
        f"<!-- rahp-epoch-disposition:v1:{record['epoch_id']} -->",
        "## Qualified specialist return observed (not imported)",
        "",
        "This records a source-qualified observation for one case/examination epoch.",
        "It does not authenticate the specialist, reconcile the Toolkit controller,",
        "or import an assurance outcome.",
        "",
        "```json", json.dumps(record, sort_keys=True, indent=2), "```",
    ))


def lookup(comments, record):
    """Scan full bounded case comment history, not only current delivery batch."""
    if not isinstance(comments, list):
        raise EpochJournalError("case comment history unavailable")
    matching = []
    for c in comments:
        if not isinstance(c, dict):
            raise EpochJournalError("malformed Registry comment")
        body = c.get("body") or ""
        found = MARKER.findall(body)
        if not found:
            continue
        # Any claimed identity bearing this epoch must be inspected, including
        # an untrusted user's marker: ignore/skip would allow false success.
        if record["epoch_id"] in found:
            matching.append(c)
    if len(matching) > 1:
        raise EpochJournalError("more than one recorded disposition for same examination epoch")
    if not matching:
        return None
    candidate = matching[0]
    if candidate.get("user") != ACTOR:
        raise EpochJournalError("epoch marker is not from authorized workflow publisher")
    if candidate.get("body") != comment_text(record):
        raise EpochJournalError("conflicting return for persisted examination epoch")
    ident = candidate.get("id")
    if type(ident) is not int or ident <= 0:
        raise EpochJournalError("missing GitHub comment acknowledgment identity")
    expected_url = record["registry_case_url"] + "#issuecomment-" + str(ident)
    if candidate.get("html_url") != expected_url:
        raise EpochJournalError("epoch acknowledgment URL does not bind to case")
    return candidate


def reconcile(record, issue, *, apply=False, exclusive_operator_lock=False,
              read_comments, post=None):
    """At most one POST, then authoritative re-read. No cross-repo atomicity.

    Caller must serialize all case publication attempts using the shared
    registry-case-publication lock, including retries and independent writers.
    """
    if not isinstance(issue, dict) or issue.get("state") != "open":
        raise EpochJournalError("Registry case is not open")
    if issue.get("html_url") != record.get("registry_case_url"):
        raise EpochJournalError("Registry case owner has changed")
    if ("<!-- rahp-registry-case:" + record["epoch"]["case_id"] + " -->"
            not in (issue.get("body") or "")):
        raise EpochJournalError("live case owner does not bind examination identity")
    text = comment_text(record)
    prior = lookup(read_comments(), record)
    base = {"schema": "rahp-registry-epoch-journal-receipt/v1",
            "epoch_id": record["epoch_id"], "registry_case_url": record["registry_case_url"],
            "state": "pending", "observation_only": True,
            "specialist_transport_authenticated": False,
            "controller_reconciliation_executed": False,
            "case_determination_imported": False}
    if prior is not None:
        return {**base, "state": "observed", "comment_id": prior["id"],
                "comment_url": prior["html_url"], "replayed": True}
    if not apply:
        return base
    if not exclusive_operator_lock or post is None:
        raise EpochJournalError("journal write requires exclusive serialized publisher")
    response = None
    error = None
    try:
        response = post(text)
    except Exception as exc:
        error = exc
    observed = lookup(read_comments(), record)
    if observed is None:
        raise EpochJournalError("ambiguous or unacknowledged epoch POST; do not retry blindly") from error
    if response is not None and (response.get("id") != observed["id"]
                                or response.get("html_url") != observed["html_url"]):
        raise EpochJournalError("POST acknowledgment contradicts authoritative case history")
    return {**base, "state": "observed", "comment_id": observed["id"],
            "comment_url": observed["html_url"],
            "recovered_ambiguous_post": error is not None, "replayed": False}
