"""Direct VTI materiality admission must not impersonate Toolkit migration."""
import base64
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_direct_intake as direct
import registry_intake as intake

PATH = "outbox/pending/vti-session-refusal-stepup-2026-11-18.json"
MANIFEST = json.loads((ROOT / PATH).read_text(encoding="utf-8"))
AUTH = json.loads((ROOT / direct.AUTH_PATH).read_text(encoding="utf-8"))


def encoded(value):
    return {"encoding": "base64", "content": base64.b64encode(
        json.dumps(value).encode("utf-8")).decode("ascii")}


class VTIMaterialityAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = copy.deepcopy(MANIFEST)
        self.auth = copy.deepcopy(AUTH)
        self.toolkit_issues = []
        self.posts = []

    def get(self, url):
        if url.endswith("/rahp-assessment-registry/branches/main"):
            return {"commit": {"sha": "a" * 40}}
        if url.endswith("/rahp-toolkit/branches/main"):
            return {"commit": {"sha": "b" * 40}}
        if "/rahp-assessment-registry/contents/" + PATH in url:
            return encoded(self.manifest)
        if "/rahp-assessment-registry/contents/" + direct.AUTH_PATH in url:
            return encoded(self.auth)
        if "/rahp-toolkit/issues?state=all" in url:
            return self.toolkit_issues
        if "/commits/" in url:
            event = self.manifest["event"]
            return {"sha": event["source_revision"], "html_url": event["source_url"]}
        raise AssertionError("unexpected endpoint: " + url)

    def test_exact_source_qualifies_without_any_write_or_assurance(self):
        receipt = direct.run(self.manifest, PATH, "", fetch=self.get)
        self.assertEqual(receipt["state"], "qualified")
        self.assertTrue(receipt["source_only_direct_intake"])
        self.assertTrue(receipt["source_commit_observed"])
        self.assertTrue(receipt["no_toolkit_issue_created"])
        self.assertIsNone(receipt["assurance_determination"])
        self.assertIsNone(receipt["controller_execution"])
        self.assertEqual(self.posts, [])

    def test_toolkit_duplicate_proposition_refuses_creation(self):
        event = self.manifest["event"]
        self.toolkit_issues = [{"number": 691, "state": "open",
                                "body": "<!-- rahp-assessment-key:" +
                                event["assessment_key"] + " -->"}]
        with self.assertRaisesRegex(direct.AdmissionError, "Toolkit already"):
            direct.run(self.manifest, PATH, "", fetch=self.get)

    def test_changed_commit_or_withdrawn_authority_refuses(self):
        for field, value in (("source_revision", "f" * 40),
                             ("finding_id", "substituted-vti-finding"),
                             ("source_repository", "other/repository")):
            updated = copy.deepcopy(self.manifest)
            updated["event"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                direct.run(updated, PATH, "", fetch=self.get)
        self.auth["admissions"][-1]["status"] = "withdrawn"
        with self.assertRaisesRegex(direct.AdmissionError, "no exact"):
            direct.run(self.manifest, PATH, "", fetch=self.get)

    def test_ambiguous_publication_recovery_requires_observed_owner(self):
        ev = self.manifest["event"]
        owner = {"number": 88, "state": "open",
                 "html_url": "https://github.com/" + intake.REGISTRY + "/issues/88",
                 "body": intake.render_body(ev)}
        attempts = iter([[], [owner]])
        def timeout(_):
            self.posts.append(1)
            raise intake.IntakeError("HTTP 502")
        receipt = direct.run(self.manifest, PATH, "", apply=True,
                             fetch=self.get, load_issues=lambda: next(attempts),
                             post=timeout)
        self.assertTrue(receipt["recovered_after_ambiguous_post"])
        self.assertEqual(receipt["owner_number"], 88)
        self.assertEqual(len(self.posts), 1)
        self.assertIsNone(receipt["assurance_determination"])

    def test_existing_legacy_controller_issue_is_not_target(self):
        event = self.manifest["event"]
        self.assertNotIn("controller_issue_url", event)
        self.assertNotIn("toolkit_issue_url", event)
        self.assertTrue(event["assessment_key"].startswith("external:direct:"))
        self.assertIn("trust-task-error", event["proposition"])
        self.assertIn("Toolkit #691", event["proposition"])


if __name__ == "__main__":
    unittest.main()
