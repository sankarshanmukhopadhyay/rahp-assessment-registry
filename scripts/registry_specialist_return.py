#!/usr/bin/env python3
"""Qualify a DPIP return for an explicitly admitted Registry case, read-only.

The canonical Toolkit contract validates portable result shape; source/outbox/
ack agreement provides provenance evidence, not independent authentication or
permission to import an RAHP determination. No GitHub writes are implemented.
"""
from __future__ import annotations

import re

from verify_dpip_legacy_consumer import (
    ConsumerError, DPIP_REPO, verify_portable_return_chain,
)

REGISTRY = "sankarshanmukhopadhyay/rahp-assessment-registry"
GITHUB_ISSUE = re.compile(r"^https://github[.]com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class SpecialistAdmissionError(ValueError):
    pass


def admitted_referral(case, dpip_issue):
    """A valid-looking specialist return does not create its own authority."""
    if not isinstance(case, dict) or not isinstance(dpip_issue, dict):
        raise SpecialistAdmissionError("case/producer issue must be objects")
    refs = case.get("referrals")
    if not isinstance(refs, list):
        raise SpecialistAdmissionError("case referral ledger absent")
    eligible = [
        r for r in refs if isinstance(r, dict)
        and r.get("role") == "specialist_assessor"
        and r.get("repository") == DPIP_REPO
        and r.get("contract") == "rahp-assessor-result/v1"
        and r.get("issue_url") == f"https://github.com/{DPIP_REPO}/issues/{dpip_issue.get('number')}"
    ]
    if len(eligible) != 1:
        raise SpecialistAdmissionError("no unique admitted Registry DPIP examination referral")
    route = eligible[0]
    if route.get("status") not in ("accepted", "returned"):
        raise SpecialistAdmissionError("DPIP referral is not admitted/accepted")
    # A historical/candidate reference without a source pin is not active authority.
    source = case.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("repository"), str) \
            or not isinstance(source.get("revision"), str) \
            or not SHA40.fullmatch(source["revision"]):
        raise SpecialistAdmissionError("case source immutable pin missing")
    if case.get("assessment", {}).get("determination") != "not_assessed":
        raise SpecialistAdmissionError("case already has a determination; review new assessment epoch")
    return route


def source_claims(case, case_issue, dpip_issue, dpip_comments, consumer):
    owner = case.get("owners", {}).get("current_active_issue")
    match = GITHUB_ISSUE.fullmatch(str(owner or ""))
    if not match or match.group(1) != REGISTRY:
        raise SpecialistAdmissionError("case does not identify a Registry issue owner")
    number = int(match.group(2))
    if case_issue.get("number") != number or case_issue.get("state") != "open":
        raise SpecialistAdmissionError("Registry case issue not current/open")
    if f"<!-- rahp-registry-case:{case.get('case_id')} -->" not in (case_issue.get("body") or ""):
        raise SpecialistAdmissionError("case ID marker absent from live Registry issue")
    if any(str(v) not in (case_issue.get("body") or "")
           for v in (case["source"]["repository"], case["source"]["revision"])):
        raise SpecialistAdmissionError("Registry issue source pin differs from case")

    body = dpip_issue.get("body") or ""
    blocks = [b.get("source") for b in consumer.yaml_blocks(body)
              if isinstance(b.get("source"), dict)]
    for c in dpip_comments:
        blocks.extend([b["source_referral"] for b in consumer.yaml_blocks(c.get("body") or "")
                       if isinstance(b.get("source_referral"), dict)])
    matching = [b for b in blocks if b.get("system") == "RAHP"
                and b.get("repository") == REGISTRY and b.get("issue") == number]
    if len(matching) != 1:
        raise SpecialistAdmissionError("DPIP has no unique explicit Registry source referral")
    src = matching[0]
    changed = src.get("changed_artifact")
    pin = (case["source"]["repository"], case["source"]["revision"])
    if not isinstance(changed, dict) or (changed.get("repository"), changed.get("revision")) != pin:
        raise SpecialistAdmissionError("DPIP referral changed artifact mismatches Registry pin")
    pins = src.get("source_pins")
    if not isinstance(pins, list) or pin not in {
        (p.get("repository"), p.get("revision")) for p in pins if isinstance(p, dict)
    }:
        raise SpecialistAdmissionError("DPIP referral omits Registry source pin")

    identities = src.get("identities")
    if (not isinstance(identities, dict)
            or not str(identities.get("examination_key", "")).strip()
            or not str(identities.get("referral_id", "")).startswith("rahp-referral:")):
        raise SpecialistAdmissionError("DPIP referral lacks canonical examination/referral identity")
    if dpip_issue.get("state") != "closed" or not {"source:rahp", "run:complete"}.issubset({
        l.get("name") for l in dpip_issue.get("labels", []) if isinstance(l, dict)
    }):
        raise SpecialistAdmissionError("DPIP examination is not a terminal source-qualified result")
    return number, pin


def qualify(case, case_issue, case_comments, dpip_issue, dpip_comments,
            consumer, assessor_contract):
    """Read-only qualified chain; never apply specialist result to case status."""
    admitted_referral(case, dpip_issue)
    number, pin = source_claims(case, case_issue, dpip_issue, dpip_comments, consumer)
    issue_number = dpip_issue["number"]
    try:
        chain = verify_portable_return_chain(
            case_comments, {issue_number: dpip_comments}, consumer, assessor_contract,
            source_repo=REGISTRY, source_issue=number,
            dpip_issue=issue_number, expected_source_pin=pin,
        )
    except (ConsumerError, KeyError, TypeError) as exc:
        raise SpecialistAdmissionError(f"canonical DPIP return chain rejected: {exc}") from exc
    if chain["source_destination"] != f"https://github.com/{REGISTRY}/issues/{number}":
        raise SpecialistAdmissionError("return destination is not the Registry case")
    return {
        "schema": "rahp-registry-dpip-admission-receipt/v1",
        "case_id": case["case_id"],
        "case_url": case["owners"]["current_active_issue"],
        "dpip_issue_url": f"https://github.com/{DPIP_REPO}/issues/{issue_number}",
        "source_pin": {"repository": pin[0], "revision": pin[1]},
        "dpip_assessment_id": chain["portable_assessment_id"],
        "dpip_outcome_observed": chain["portable_outcome"],
        "dpip_return_digest": chain["source_delivery_digest"],
        "canonical_assessor_schema_validated": True,
        "outbox_source_ack_chain_observed": True,
        "return_transport_authenticated": False,
        "case_determination_imported": False,
        "controller_reconciliation_executed": False,
        "operational_cutover_qualified": False,
    }
