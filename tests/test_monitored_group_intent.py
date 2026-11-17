import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import qualify_monitored_group_intent as q

class GroupIntentTests(unittest.TestCase):
    def setUp(self):
        self.intent=json.loads((ROOT/"outbox/pending/spec-dependency-2026-11-16.json").read_text())
        i=self.intent
        self.group={"assessment_key":q.KEY,"source_observations":[
            {"finding_id":fid,"repository":i["source_repository"]}
            for fid in i["source_finding_ids"]]}
        i["source_group_sha256"]=q.digest(self.group)
        self.candidate={"schema":"rahp-registry-monitored-owner-candidate-receipt/v1",
            "key":q.KEY,"finding_ids":i["source_finding_ids"],
            "source_group_sha256":i["source_group_sha256"],
            "source_evidence_sha256":i["source_evidence_sha256"],
            "candidate_sha256":i["candidate_sha256"],
            "active_toolkit_issue":i["toolkit_current_issue_url"],
            "historical_toolkit_issue":i["toolkit_historical_issue_url"],
            "protected_residuals":i["protected_issue_urls"]}
        self.review={"schema":"rahp-registry-maintainer-scope-status/v1",
            "assessment_key":q.KEY,"scope_sha256":i["maintainer_scope_sha256"],
            "status":"pending","independent_review_claimed":False,
            "cutover_authorized":False,"registry_owner_created":False}
    def check(self):return q.qualify(self.intent,self.group,self.candidate,self.review)
    def test_pending_or_accepted_scope_never_suppresses_toolkit(self):
        for state in ("pending","accepted"):
            self.review["status"]=state
            self.assertFalse(self.check()["cutover_authorized"])
            self.assertFalse(self.check()["current_observation_acknowledged"])
    def test_source_group_changed_or_missing_finding_rejected(self):
        self.group["extra"]="different"
        with self.assertRaisesRegex(q.IntentError,"digest"):self.check()
        self.setUp()
        self.group["source_observations"].pop()
        with self.assertRaises(q.IntentError):self.check()
    def test_reject_false_publication_or_assurance(self):
        for key,value in (("status","accepted"),("registry_successor_issue_url","https://fake"),
            ("current_observation_acknowledged",True),
            ("toolkit_writer_suppression_authorized",True),("assurance_determination","PASS")):
            self.setUp()
            self.intent[key]=value
            with self.assertRaises(q.IntentError):self.check()
    def test_maintainer_scope_drift_or_withdrawal_rejected(self):
        self.review["scope_sha256"]="f"*64
        with self.assertRaises(q.IntentError):self.check()
        self.setUp()
        self.review["status"]="withdrawn"
        with self.assertRaises(q.IntentError):self.check()
    def test_candidate_protected_owner_changed_rejected(self):
        self.candidate["protected_residuals"]=[]
        with self.assertRaises(q.IntentError):self.check()
    def test_does_not_pretend_four_findings_are_one(self):
        i=json.loads((ROOT/"outbox/pending/spec-dependency-2026-11-16.json").read_text())
        self.assertNotIn("finding_id",i)
        self.assertNotIn("source_revision",i)
        self.assertEqual(len(i["source_finding_ids"]),4)
if __name__=="__main__":unittest.main()
