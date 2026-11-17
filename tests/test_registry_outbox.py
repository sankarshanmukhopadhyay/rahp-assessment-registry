import copy
import base64
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import registry_outbox as outbox
import registry_intake as intake


def event(**kwargs):
    return {
        "kind": "external_assessment",
        "assessment_key": "dtg:case:sample-0001",
        "title": "A bounded examination",
        "proposition": "Unsupported authorization must be rejected.",
        "source_repository": "OpenVTC/verifiable-trust-infrastructure",
        "source_revision": "a" * 40,
        "source_url": "https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2439",
        "finding_id": "finding-sample-0001",
        "responsible_owner": "OpenVTC/verifiable-trust-infrastructure",
        **kwargs
    }


def manifest(**kwargs):
    return {"schema": "rahp-registry-pending-intake/v1", "event": event(**kwargs)}


def issue(ev, number=18):
    return {"number": number, "state": "open",
            "html_url": f"https://github.com/{intake.REGISTRY}/issues/{number}",
            "body": intake.render_body(ev)}


class OutboxTests(unittest.TestCase):
    def test_live_reservation_binds_main_ledger_intent_and_historical_source(self):
        ev = event()
        key = ev["assessment_key"]
        path = "outbox/pending/test-case.json"
        issue_url = "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1234"
        reservation = {
            "assessment_key": key, "toolkit_issue_url": issue_url,
            "registry_intent_path": path, "source_revision": ev["source_revision"],
            "finding_id": ev["finding_id"], "state": "reserved",
        }
        ledger = {"schema": "rahp-registry-transfers/v1", "transfers": [reservation]}
        sha = "b" * 40
        head = {"commit": {"sha": sha}}
        issue = {"html_url": issue_url, "state": "open",
                 "body": "<!-- rahp-assessment-key:" + key + " --> " + ev["finding_id"]}
        contents = {"encoding": "base64", "content": base64.b64encode(json.dumps(ledger).encode()).decode()}
        committed = {"encoding": "base64", "content": base64.b64encode(
            json.dumps(manifest()).encode()).decode()}
        urls = []
        registry_head = {"commit": {"sha": "d" * 40}}
        def fetch(url):
            urls.append(url)
            if "/rahp-assessment-registry/branches/main" in url:
                return registry_head
            if "/rahp-assessment-registry/contents/" in url:
                return committed
            if "/branches/main" in url:
                return head
            if "/contents/" in url:
                return contents
            if "/issues/1234" in url:
                return issue
            self.fail("unrecognized Toolkit read " + url)
        proof = outbox.verify_live_reservation(manifest(), path, "", fetch=fetch)
        self.assertEqual(proof["toolkit_main_sha"], sha)
        self.assertEqual(len(urls), 7)

        for changes in (
            {"state": "accepted"},
            {"source_revision": "c" * 40},
            {"finding_id": "different"},
            {"registry_intent_path": "outbox/pending/other.json"},
            {"registry_issue_url": "https://github.com/example/repo/issues/2"},
        ):
            with self.subTest(changes=changes):
                changed = {**reservation, **changes}
                contents["content"] = base64.b64encode(json.dumps({
                    "schema": "rahp-registry-transfers/v1", "transfers": [changed]
                }).encode()).decode()
                with self.assertRaises(outbox.DeliveryError):
                    outbox.verify_live_reservation(manifest(), path, "", fetch=fetch)
        contents["content"] = base64.b64encode(json.dumps(ledger).encode()).decode()
        issue["body"] = "no matching source"
        with self.assertRaisesRegex(outbox.DeliveryError, "does not identify"):
            outbox.verify_live_reservation(manifest(), path, "", fetch=fetch)
        issue["body"] = "<!-- rahp-assessment-key:" + key + " --> " + ev["finding_id"]
        next_head = iter([head, {"commit": {"sha": "c" * 40}}])
        def drifting(url):
            if "/rahp-toolkit/branches/main" in url:
                return next(next_head)
            return fetch(url)
        with self.assertRaisesRegex(outbox.DeliveryError, "changed"):
            outbox.verify_live_reservation(manifest(), path, "", fetch=drifting)

        committed["content"] = base64.b64encode(json.dumps(
            {"schema": "rahp-registry-pending-intake/v1", "event": {**ev, "source_revision": "f" * 40}}
        ).encode()).decode()
        with self.assertRaisesRegex(outbox.DeliveryError, "does not match"):
            outbox.verify_live_reservation(manifest(), path, "", fetch=fetch)
        committed["content"] = base64.b64encode(json.dumps(manifest()).encode()).decode()
        registry_reads = iter([registry_head, {"commit": {"sha": "e" * 40}}])
        def registry_drifting(url):
            if "/rahp-assessment-registry/branches/main" in url:
                return next(registry_reads)
            return fetch(url)
        with self.assertRaisesRegex(outbox.DeliveryError, "Registry main changed"):
            outbox.verify_live_reservation(manifest(), path, "", fetch=registry_drifting)

    def test_reservation_rejects_uncommitted_or_traversal_paths(self):
        for path in ("../outbox/pending/test.json", "/tmp/test.json",
                     "outbox/pending/test.txt", "outbox/pending/UPPER.json"):
            with self.subTest(path=path), self.assertRaises(outbox.DeliveryError):
                outbox.verify_live_reservation(manifest(), path, "", fetch=lambda _: self.fail("network not needed"))

    def test_workflow_grants_write_only_to_explicit_main_branch_publish(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/registry-outbox-replay.yml"
        text = path.read_text(encoding="utf-8")
        prefix, rest = text.split("  publish:", 1)
        self.assertIn("  pull_request:", prefix)
        self.assertIn("  contents: read\n  issues: read", prefix)
        self.assertNotIn("issues: write", prefix)
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.apply == true", rest)
        self.assertIn("github.ref == 'refs/heads/main'", rest)
        self.assertIn("issues: write", rest)
        self.assertIn("new Registry issue creation requires a coordinated", rest)
        self.assertIn("receipt.get('state') != 'owner_observed'", rest)
        self.assertIn("--receipt build/outbox/replayed.json --apply", rest)
        self.assertNotIn("gh issue create", rest)

    def test_unrecognized_schema_or_additional_fields_fail(self):
        for item in ([], {}, {"schema": "wrong", "event": event()},
                     {**manifest(), "assurance_determination": "PASS"}):
            with self.subTest(item=item), self.assertRaises(outbox.DeliveryError):
                outbox.require_event(item)

    def test_dry_run_does_not_post(self):
        calls = []
        receipt = outbox.deliver(manifest(), "", load_issues=lambda: [],
                                 post=lambda p: calls.append(p))
        self.assertEqual(receipt["state"], "pending")
        self.assertEqual(calls, [])
        self.assertIsNone(receipt["assurance_determination"])

    def test_existing_matching_owner_idempotent(self):
        calls = []
        receipt = outbox.deliver(manifest(), "", apply=True,
                                 load_issues=lambda: [issue(event())],
                                 post=lambda p: calls.append(p))
        self.assertEqual(receipt["state"], "owner_observed")
        self.assertEqual(receipt["owner_number"], 18)
        self.assertEqual(calls, [])

    def test_existing_owner_different_revision_requires_reassessment(self):
        with self.assertRaisesRegex(outbox.DeliveryError, "reassessment"):
            outbox.deliver(manifest(source_revision="b" * 40), "",
                           load_issues=lambda: [issue(event())])

    def test_existing_owner_different_finding_requires_reassessment(self):
        with self.assertRaisesRegex(outbox.DeliveryError, "reassessment"):
            outbox.deliver(manifest(finding_id="different-finding"), "",
                           load_issues=lambda: [issue(event())])

    def test_direct_apply_cannot_create_during_toolkit_publication(self):
        calls = []
        with self.assertRaisesRegex(outbox.DeliveryError, "publisher cutover authority"):
            outbox.deliver(manifest(), "", apply=True,
                           load_issues=lambda: [], post=lambda p: calls.append(p))
        self.assertEqual(calls, [])

    def test_existing_owner_is_still_observable_with_create_blocked(self):
        result = outbox.deliver(manifest(), "", apply=True,
                                load_issues=lambda: [issue(event())],
                                post=lambda p: self.fail("no issue POST expected"))
        self.assertEqual(result["state"], "owner_observed")

    def test_success_requires_authoritative_owner_reread(self):
        before = [[], [issue(event())]]
        receipt = outbox.deliver(manifest(), "", apply=True, allow_new_case=True,
                                 load_issues=lambda: before.pop(0),
                                 post=lambda p: {"number": 18,
                                                 "html_url": issue(event())["html_url"]})
        self.assertEqual(receipt["state"], "owner_observed")

    def test_post_200_without_visible_owner_is_indeterminate(self):
        before = [[], []]
        with self.assertRaisesRegex(outbox.DeliveryError, "unacknowledged|no authoritative"):
            outbox.deliver(manifest(), "", apply=True, allow_new_case=True,
                           load_issues=lambda: before.pop(0),
                           post=lambda p: {"number": 18, "html_url": issue(event())["html_url"]})

    def test_ambiguous_http_failure_after_commit_recovers(self):
        before = [[], [issue(event())]]
        def lost_ack(payload):
            raise intake.IntakeError("GitHub HTTP 502")
        receipt = outbox.deliver(manifest(), "", apply=True, allow_new_case=True,
                                 load_issues=lambda: before.pop(0), post=lost_ack)
        self.assertTrue(receipt["recovered_after_ambiguous_post"])
        self.assertEqual(receipt["state"], "owner_observed")

    def test_http_failure_without_commit_stays_pending(self):
        before = [[], []]
        with self.assertRaisesRegex(outbox.DeliveryError, "no authoritative"):
            outbox.deliver(manifest(), "", apply=True, allow_new_case=True,
                           load_issues=lambda: before.pop(0),
                           post=lambda p: (_ for _ in ()).throw(intake.IntakeError("HTTP 502")))

    def test_forged_post_response_rejected(self):
        before = [[], [issue(event())]]
        with self.assertRaisesRegex(outbox.DeliveryError, "disagrees"):
            outbox.deliver(manifest(), "", apply=True, allow_new_case=True,
                           load_issues=lambda: before.pop(0),
                           post=lambda p: {"number": 19, "html_url": issue(event(), 19)["html_url"]})

    def test_closed_owner_cannot_be_reopened(self):
        closed = issue(event())
        closed["state"] = "closed"
        with self.assertRaises(intake.IntakeError):
            outbox.deliver(manifest(), "", apply=True, load_issues=lambda: [closed])

    def test_false_result_and_missing_pin_rejected(self):
        for changed in ({"assurance_determination": "PASS"},
                        {"source_revision": "main"}):
            with self.subTest(changed=changed), self.assertRaises(intake.IntakeError):
                outbox.require_event(manifest(**changed))

    def test_pilot_existing_owner_is_not_dispatched(self):
        from json import loads
        pilot = loads((Path(__file__).resolve().parents[1]
                       / "intake/manifests/network-answer-pilot.json").read_text())[0]
        owner = {"number": 4, "state": "open",
                 "html_url": f"https://github.com/{intake.REGISTRY}/issues/4",
                 "body": "<!-- rahp-registry-case:RAHP-AR-DTG-0001 --> "
                         + pilot["source_revision"] + " " + pilot["finding_id"]}
        called = []
        receipt = outbox.deliver({"schema": "rahp-registry-pending-intake/v1",
                                  "event": pilot}, "", apply=True,
                                 load_issues=lambda: [owner],
                                 post=lambda p: called.append(p))
        self.assertEqual(receipt["owner_number"], 4)
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
