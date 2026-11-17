import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import qualify_monitored_owner as q

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "ops/migration/spec-dependency-owner-candidate.json").read_text())
        ids = self.spec["finding_ids"]
        self.events = [{"assessment_key": q.KEY, "source_observations": [
            {"finding_id": i, "repository": self.spec["repository"]} for i in ids]}]
        self.evidence = {"schema": "rahp-registry-release-tag-source-qualification/v1",
            "verification": "live-annotated-tag-reference-and-object",
            "cutover_authorized": False, "ownership_transfer_accepted": False,
            "group_source_qualification": {"source_provenance_qualified": True,
                "cutover_authorized": False, "groups": [{"assessment_key": q.KEY,
                    "finding_count": 4, "observed_commit_findings": 1,
                    "supplemental_annotated_tag_findings": 3,
                    "case_owner_accepted": False}]}}
        self.owner = {"number":272,"html_url":q.URL+"272","state":"open",
            "body": q.MARKER + "\n" + "\n".join("finding="+x for x in ids)}
        self.historical={"number":615,"html_url":q.URL+"615",
                         "state":"closed","body":q.MARKER}
        self.protected=[{"number":n,"html_url":q.URL+str(n),"state":"open"}
                        for n in (282,826,837)]
        self.registry=[]
    def check(self):
        return q.qualify(self.spec,self.events,self.evidence,self.owner,
                         self.historical,self.protected,self.registry)
    def test_candidate_not_cutover(self):
        value=self.check()
        self.assertTrue(value["current_source_qualified"])
        for k in ("independent_review_accepted","registry_owner_accepted",
                  "current_observation_acknowledged","toolkit_writers_fenced",
                  "consumer_migration_qualified","cutover_authorized"):
            self.assertIs(value[k],False)
    def test_missing_finding_fails(self):
        self.owner["body"]=q.MARKER
        with self.assertRaisesRegex(q.CandidateError,"missing a grouped"):
            self.check()
    def test_wrong_owner_and_historical_status_fail(self):
        self.owner["state"]="closed"
        with self.assertRaisesRegex(q.CandidateError,"owner or historical"):
            self.check()
        self.owner["state"]="open"
        self.historical["state"]="open"
        with self.assertRaises(q.CandidateError):
            self.check()
    def test_forged_review_or_suppression_refused(self):
        for flag in ("independent_review_accepted","registry_owner_accepted",
                     "toolkit_writer_exclusion_accepted"):
            self.spec[flag]=True
            with self.assertRaisesRegex(q.CandidateError,"authorization"):
                self.check()
            self.spec[flag]=False
    def test_changed_group_and_evidence_fail(self):
        self.events[0]["source_observations"].pop()
        with self.assertRaises(q.CandidateError): self.check()
        self.setUp()
        self.evidence["group_source_qualification"]["groups"][0]["supplemental_annotated_tag_findings"]=2
        with self.assertRaisesRegex(q.CandidateError,"coverage"):
            self.check()
    def test_protected_owners_and_registry_competition_fail(self):
        self.protected[0]["number"]=400
        with self.assertRaises(q.CandidateError): self.check()
        self.setUp()
        self.registry=[{"number":82, "state":"open",
            "body":"<!-- registry-assessment-key:"+q.KEY+" -->"}]
        with self.assertRaisesRegex(q.CandidateError,"already owned"):
            self.check()
    def test_unknown_source_identity_fails(self):
        self.spec["monitor_revision"]="e"*40
        with self.assertRaises(q.CandidateError): self.check()

if __name__ == "__main__":
    unittest.main()
