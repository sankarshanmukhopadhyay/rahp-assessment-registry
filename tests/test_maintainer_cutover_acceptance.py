import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_maintainer_cutover_acceptance as m

SHA = "a"*64
def fixture():
    return {
        "schema": "rahp-registry-monitored-owner-candidate-receipt/v1",
        "key": m.KEY,
        "candidate_sha256": SHA,
        "source_group_sha256": "b"*64,
        "source_evidence_sha256": "c"*64,
        "finding_ids": sorted(("0add1f4cc0f048ce6bfc", "29e39a0329123d8839a6",
                               "a60eaffaf3cbc1394553", "acc9772126b1a3820240")),
        "active_toolkit_issue":
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/272",
        "historical_toolkit_issue":
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/615",
        "protected_residuals": [
            "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/" + str(n)
            for n in (282, 826, 837)],
        "current_source_qualified": True,
        "live_toolkit_owner_observed": True,
        "registry_key_unclaimed_when_checked": True,
        "independent_review_accepted": False,
        "registry_owner_accepted": False,
        "current_observation_acknowledged": False,
        "toolkit_writers_fenced": False,
        "consumer_migration_qualified": False,
        "cutover_authorized": False,
    }

def comment(receipt, number=123, action="accept", actor=m.MAINTAINER, association="OWNER"):
    digest = m.scope(receipt)
    return {
        "id": number,
        "html_url": "https://github.com/" + m.REGISTRY +
                    "/issues/11#issuecomment-" + str(number),
        "user": {"login": actor, "id": 2384, "type": "User"},
        "author_association": association,
        "body": "<!-- rahp-registry-maintainer-scope:v1:" + action +
                ":" + digest + " -->\nMaintainer scope disposition for exact candidate.",
    }

class MaintainerAcceptanceTests(unittest.TestCase):
    def test_unapproved_is_pending_not_independent(self):
        r = m.evaluate(fixture(), [])
        self.assertEqual(r["status"], "pending")
        self.assertFalse(r["independent_review_claimed"])
        self.assertFalse(r["cutover_authorized"])
        self.assertFalse(r["toolkit_writer_suppression_authorized"])
    def test_exact_maintainer_acceptance_still_is_not_cutover(self):
        f = fixture()
        r = m.evaluate(f, [comment(f)])
        self.assertEqual(r["status"], "accepted")
        self.assertEqual(r["decision_comment_url"],
                         "https://github.com/" + m.REGISTRY + "/issues/11#issuecomment-123")
        self.assertFalse(r["registry_owner_created"])
        self.assertFalse(r["current_observation_acknowledged"])
        self.assertFalse(r["cutover_authorized"])
    def test_withdrawal_supersedes_acceptance_and_new_acceptance_can_replace(self):
        f = fixture()
        a = comment(f, 10)
        d = comment(f, 12, "withdraw")
        self.assertEqual(m.evaluate(f, [d, a])["status"], "withdrawn")
        self.assertEqual(m.evaluate(f, [a, d, comment(f, 20)])["status"], "accepted")
    def test_stale_candidate_digest_does_not_authorize_new_scope(self):
        f = fixture()
        old = comment(f)
        f["source_group_sha256"] = "d"*64
        self.assertEqual(m.evaluate(f, [old])["status"], "pending")
        f["finding_ids"].pop()
        with self.assertRaises(m.MaintainerScopeError):
            m.evaluate(f, [])
    def test_foreign_actor_or_ambiguous_marker_fails_closed(self):
        f = fixture()
        for issue in (comment(f, actor="other"),
                      comment(f, association="CONTRIBUTOR")):
            with self.assertRaisesRegex(m.MaintainerScopeError, "not from"):
                m.evaluate(f, [issue])
        pair = comment(f)
        pair["body"] += "\n" + comment(f, action="withdraw")["body"]
        with self.assertRaisesRegex(m.MaintainerScopeError, "ambiguous"):
            m.evaluate(f, [pair])
    def test_forged_receipt_authority_fields_rejected(self):
        for field in ("independent_review_accepted", "registry_owner_accepted",
                      "current_observation_acknowledged", "toolkit_writers_fenced",
                      "consumer_migration_qualified", "cutover_authorized"):
            f=fixture()
            f[field]=True
            with self.subTest(field=field), self.assertRaises(m.MaintainerScopeError):
                m.evaluate(f, [])
    def test_wrong_comment_identity_and_duplicate_ids_are_rejected(self):
        f=fixture()
        bad=comment(f)
        bad["html_url"] += "-wrong"
        with self.assertRaises(m.MaintainerScopeError):
            m.evaluate(f, [bad])
        with self.assertRaises(m.MaintainerScopeError):
            m.evaluate(f, [comment(f), comment(f)])
    def test_paginated_tracker_history_and_incomplete_page(self):
        calls=[]
        rows=[{"id":n, "body":"ordinary comment"} for n in range(100)]
        def get(url):
            calls.append(url)
            return rows if url.endswith("page=1") else []
        self.assertEqual(len(m.full_comments("token", fetch=get)), 100)
        self.assertEqual(len(calls), 2)
        with self.assertRaises(m.MaintainerScopeError):
            m.full_comments("token", fetch=lambda _: None)

if __name__ == "__main__":
    unittest.main()
