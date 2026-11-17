import base64
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import registry_direct_intake as direct
import registry_intake as intake


ROOT = Path(__file__).resolve().parents[1]
PATH = "outbox/pending/ondtf-emergency-authority-v1.json"
MANIFEST = json.loads((ROOT / PATH).read_text())
AUTH = json.loads((ROOT / direct.AUTH_PATH).read_text())


def encoded(value):
    return {"encoding": "base64", "content": base64.b64encode(
        json.dumps(value).encode("utf-8")).decode("ascii")}


class DirectAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = copy.deepcopy(MANIFEST)
        self.authority = copy.deepcopy(AUTH)
        self.registry_head = {"commit": {"sha": "c" * 40}}
        self.toolkit_head = {"commit": {"sha": "d" * 40}}
        self.issues = []
        self.urls = []
        self.posted = []

    def fetch(self, url):
        self.urls.append(url)
        if "/rahp-assessment-registry/branches/main" in url:
            return self.registry_head
        if "/rahp-toolkit/branches/main" in url:
            return self.toolkit_head
        if "/rahp-assessment-registry/contents/" + PATH in url:
            return encoded(self.manifest)
        if "/rahp-assessment-registry/contents/" + direct.AUTH_PATH in url:
            return encoded(self.authority)
        if "/rahp-toolkit/issues?state=all" in url:
            return self.issues
        if "/commits/" in url:
            e = self.manifest["event"]
            return {"sha": e["source_revision"], "html_url": e["source_url"]}
        self.fail("unexpected source endpoint: " + url)

    def test_manual_dispatch_has_exclusive_direct_intake_gate(self):
        workflow = (ROOT / ".github/workflows/registry-outbox-replay.yml").read_text()
        self.assertIn("direct_intake:", workflow)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("if: inputs.direct_intake == true", workflow)
        self.assertIn("if: inputs.direct_intake != true", workflow)
        self.assertIn("receipt.get('state') != 'owner_observed'", workflow)
        self.assertIn("receipt.get('state') == 'qualified'", workflow)
        self.assertNotIn("gh issue create", workflow)
        self.assertNotIn("  schedule:", workflow)

    def test_real_source_admission_is_exact_and_read_only(self):
        proof = direct.run(self.manifest, PATH, "", fetch=self.fetch)
        self.assertEqual(proof["state"], "qualified")
        self.assertTrue(proof["source_commit_observed"])
        self.assertEqual(proof["owner_number"], None)
        self.assertEqual(proof["assurance_determination"], None)
        self.assertFalse(self.posted)

    def test_apply_uses_outbox_authoritative_owner_reread(self):
        ev = self.manifest["event"]
        owner = {"number": 23, "state": "open", "body": intake.render_body(ev),
                 "html_url": "https://github.com/" + intake.REGISTRY + "/issues/23"}
        observed = iter([[], [owner]])
        def post(payload):
            self.posted.append(payload)
            return {"number": 23, "html_url": owner["html_url"]}
        receipt = direct.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                             load_issues=lambda: next(observed), post=post)
        self.assertEqual(receipt["state"], "owner_observed")
        self.assertEqual(receipt["owner_number"], 23)
        self.assertEqual(len(self.posted), 1)
        self.assertFalse(receipt["first_case_execution"])
        self.assertIsNone(receipt["assurance_determination"])

    def test_ambiguous_post_recovers_only_on_observed_owner(self):
        ev = self.manifest["event"]
        owner = {"number": 24, "state": "open", "body": intake.render_body(ev),
                 "html_url": "https://github.com/" + intake.REGISTRY + "/issues/24"}
        observed = iter([[], [owner]])
        def failed(_):
            raise intake.IntakeError("HTTP 502")
        receipt = direct.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                             load_issues=lambda: next(observed), post=failed)
        self.assertTrue(receipt["recovered_after_ambiguous_post"])

    def test_unobserved_post_does_not_acknowledge(self):
        observed = iter([[], []])
        with self.assertRaisesRegex(ValueError, "no authoritative Registry owner"):
            direct.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                       load_issues=lambda: next(observed),
                       post=lambda _: {"number": 99, "html_url": "https://github.com/example"})

    def test_altered_manifest_or_authority_fails_before_post(self):
        changes = [
            ("assessment_key", "external:direct:forged:case-0001"),
            ("source_revision", "f" * 40),
            ("source_url", "https://github.com/other/repo/commit/" + "f" * 40),
            ("finding_id", "different-finding-id"),
            ("responsible_owner", "someone/else"),
        ]
        for field, value in changes:
            with self.subTest(field=field):
                current = self.manifest["event"][field]
                self.manifest["event"][field] = value
                with self.assertRaises(ValueError):
                    direct.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                               post=lambda _: self.fail("no POST permitted"))
                self.manifest["event"][field] = current
        self.authority["admissions"].append(copy.deepcopy(self.authority["admissions"][0]))
        with self.assertRaisesRegex(direct.AdmissionError, "no exact"):
            direct.run(self.manifest, PATH, "", fetch=self.fetch)

    def test_toolkit_existing_owner_precludes_new_case(self):
        self.issues = [{"number": 99, "body": "<!-- rahp-assessment-key:" +
                        self.manifest["event"]["assessment_key"] + " -->", "state": "open"}]
        with self.assertRaisesRegex(direct.AdmissionError, "Toolkit already"):
            direct.run(self.manifest, PATH, "", fetch=self.fetch)

    def test_branch_drift_rejected(self):
        original = self.fetch
        changes = iter([self.registry_head, {"commit": {"sha": "e" * 40}}])
        def drifting(url):
            if "/rahp-assessment-registry/branches/main" in url:
                return next(changes)
            return original(url)
        with self.assertRaisesRegex(direct.AdmissionError, "branch changed"):
            direct.qualify(self.manifest, PATH, "", fetch=drifting)

    def test_non_direct_and_path_escape_rejected(self):
        for path in ("../outbox/pending/a.json", "outbox/pending/UPPER.json", "/tmp/x.json"):
            with self.subTest(path=path), self.assertRaises(direct.AdmissionError):
                direct.qualify(self.manifest, path, "", fetch=self.fetch)
        other = copy.deepcopy(self.manifest)
        other["event"]["assessment_key"] = "dtg:portfolio:combined:old-review"
        with self.assertRaises(direct.AdmissionError):
            direct.qualify(other, PATH, "", fetch=self.fetch)


if __name__ == "__main__":
    unittest.main()
