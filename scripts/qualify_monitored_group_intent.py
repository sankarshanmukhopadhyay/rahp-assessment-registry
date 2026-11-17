#!/usr/bin/env python3
"""Qualify the exact source-controlled grouped handoff intent without writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

KEY = "dtg:portfolio:combined:spec-dependency-alignment"
SCHEMA = "rahp-registry-pending-monitored-group/v1"
class IntentError(ValueError):
    pass

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
        separators=(",",":"),allow_nan=False).encode()).hexdigest()

def qualify(intent, combined, candidate, review):
    required = {"schema","assessment_key","monitor_revision","snapshot_date",
        "source_repository","source_finding_ids","source_group_sha256",
        "source_evidence_sha256","candidate_sha256","maintainer_scope_sha256",
        "toolkit_current_issue_url","toolkit_historical_issue_url","protected_issue_urls",
        "status","registry_successor_issue_url","current_observation_acknowledged",
        "toolkit_writer_suppression_authorized","assurance_determination"}
    if not isinstance(intent,dict) or set(intent)!=required:
        raise IntentError("invalid exact group intent fields")
    if (intent["schema"]!=SCHEMA or intent["assessment_key"]!=KEY or
        intent["monitor_revision"]!="7e2813c8daf867a21e4064513cc83612726aeb44" or
        intent["snapshot_date"]!="2026-11-16" or
        intent["source_repository"]!="trustoverip/dtgwg-trust-tasks-tf" or
        intent["status"]!="pending_governance" or
        intent["registry_successor_issue_url"] is not None or
        intent["current_observation_acknowledged"] is not False or
        intent["toolkit_writer_suppression_authorized"] is not False or
        intent["assurance_determination"] is not None):
        raise IntentError("group intent asserts unauthorized source or ownership")
    ids=intent["source_finding_ids"]
    if (not isinstance(ids,list) or len(ids)!=4 or ids!=sorted(set(ids))
        or not all(isinstance(x,str) and re.fullmatch("[0-9a-f]{20}",x) for x in ids)):
        raise IntentError("invalid four-finding group membership")
    if not isinstance(combined,dict) or combined.get("assessment_key")!=KEY:
        raise IntentError("wrong combined source event")
    obs=combined.get("source_observations")
    if (not isinstance(obs,list) or len(obs)!=4 or
        sorted(x.get("finding_id") for x in obs if isinstance(x,dict))!=ids or
        any(x.get("repository")!=intent["source_repository"] for x in obs)):
        raise IntentError("group source members differ")
    if digest(combined)!=intent["source_group_sha256"]:
        raise IntentError("immutable grouped observation digest differs")
    if (not isinstance(candidate,dict) or candidate.get("schema")!=
        "rahp-registry-monitored-owner-candidate-receipt/v1" or
        candidate.get("key")!=KEY or candidate.get("finding_ids")!=ids or
        candidate.get("source_group_sha256")!=intent["source_group_sha256"] or
        candidate.get("source_evidence_sha256")!=intent["source_evidence_sha256"] or
        candidate.get("candidate_sha256")!=intent["candidate_sha256"] or
        candidate.get("active_toolkit_issue")!=intent["toolkit_current_issue_url"] or
        candidate.get("historical_toolkit_issue")!=intent["toolkit_historical_issue_url"] or
        candidate.get("protected_residuals")!=intent["protected_issue_urls"]):
        raise IntentError("live owner/source qualification differs from intent")
    if (not isinstance(review,dict) or review.get("schema")!=
        "rahp-registry-maintainer-scope-status/v1" or review.get("assessment_key")!=KEY or
        review.get("scope_sha256")!=intent["maintainer_scope_sha256"] or
        review.get("independent_review_claimed") is not False or
        review.get("cutover_authorized") is not False or
        review.get("registry_owner_created") is not False or
        review.get("status") not in ("pending","accepted")):
        raise IntentError("review was withdrawn or source scope differs")
    return {"schema":"rahp-registry-group-pending-intent-qualification/v1",
        "assessment_key":KEY,"source_group_sha256":intent["source_group_sha256"],
        "finding_count":len(ids),"intent_sha256":digest(intent),
        "maintainer_scope_status":review["status"],"source_observation_qualified":True,
        "registry_successor_created":False,"toolkit_group_reserved":False,
        "current_observation_acknowledged":False,
        "toolkit_writer_suppression_authorized":False,"cutover_authorized":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("manifest","combined","owner-candidate","maintainer-status","out"):
        p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    try:
        manifest=json.loads(args.manifest.read_text())
        events=json.loads(args.combined.read_text())
        matched=[x for x in events if isinstance(x,dict) and x.get("assessment_key")==KEY]
        if len(matched)!=1: raise IntentError("ambiguous grouped event")
        receipt=qualify(manifest,matched[0],json.loads(args.owner_candidate.read_text()),
                        json.loads(args.maintainer_status.read_text()))
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print("UNQUALIFIED group intent:",exc,file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("Qualified group intent; no Registry issue, no writer suppression")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
