import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import registry_intake as intake


def event(**overrides):
    base = {
        "kind": "external_assessment", "assessment_key": "dtg:case:example-001",
        "title": "Verify signed task response rejection",
        "proposition": "Unverified responses must not authorize action.",
        "source_repository": "OpenVTC/verifiable-trust-infrastructure",
        "source_revision": "a" * 40,
        "source_url": "https://github.com/OpenVTC/verifiable-trust-infrastructure/pull/2439",
        "finding_id": "example-finding-001",
        "responsible_owner": "OpenVTC/verifiable-trust-infrastructure",
    }
    return {**base, **overrides}


class IntakeTests(unittest.TestCase):
    def test_fresh_dry_run_has_no_writes(self):
        with patch.object(intake, "request") as req:
            result = intake.execute([event()], "", issue_snapshot=[])
        req.assert_not_called()
        self.assertEqual(result[0]["action"], "create")

    def test_existing_owner_is_idempotent(self):
        issue = {"number": 4, "state": "open", "html_url": "https://github.com/x/y/issues/4",
                 "body": intake.marker(event()["assessment_key"])}
        result = intake.execute([event()], "", issue_snapshot=[issue])
        self.assertEqual(result[0]["action"], "existing-owner")
        self.assertEqual(result[0]["number"], 4)

    def test_key_with_letter_n_is_indexed(self):
        key = "dtg:network:consumer"
        owner = {"number": 11, "state": "open", "body": intake.marker(key)}
        self.assertEqual(intake.index_issues([owner])[key]["number"], 11)

    def test_migrated_pilot_does_not_create_duplicate(self):
        ev = event(finding_id="4cdb4f9a7399aea0a55a")
        owner = {"number": 4, "state": "open", "body": "<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->"}
        with patch.object(intake, "request") as req:
            result = intake.execute([ev], "", issue_snapshot=[owner])
        req.assert_not_called()
        self.assertEqual(result[0]["action"], "existing-owner")
        self.assertEqual(result[0]["number"], 4)

    def test_migrated_pilot_owner_absent_or_closed_fails(self):
        ev = event(finding_id="4cdb4f9a7399aea0a55a")
        for state, body in (("closed", "<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->"),
                            ("open", "<!-- wrong-case -->")):
            with self.subTest(state=state, body=body), self.assertRaisesRegex(
                intake.IntakeError, "no verified open"
            ):
                intake.plan([ev], [{"number": 4, "state": state, "body": body}])

    def test_migrated_pilot_conflicting_key_fails(self):
        ev = event(finding_id="4cdb4f9a7399aea0a55a")
        issues = [
            {"number": 4, "state": "open", "body": "<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->"},
            {"number": 5, "state": "open", "body": intake.marker(ev["assessment_key"])},
        ]
        with self.assertRaisesRegex(intake.IntakeError, "conflicts"):
            intake.plan([ev], issues)

    def test_closed_case_not_reopened(self):
        issue = {"number": 4, "state": "closed", "body": intake.marker(event()["assessment_key"])}
        with self.assertRaisesRegex(intake.IntakeError, "closed owner"):
            intake.execute([event()], "", issue_snapshot=[issue])

    def test_duplicate_registered_owner_rejected(self):
        issues = [{"number": n, "state": "open", "body": intake.marker(event()["assessment_key"])}
                  for n in (4, 5)]
        with self.assertRaisesRegex(intake.IntakeError, "duplicate existing owner"):
            intake.plan([event()], issues)

    def test_duplicate_batch_rejected_before_write(self):
        with patch.object(intake, "request") as req:
            with self.assertRaisesRegex(intake.IntakeError, "duplicate assessment key"):
                intake.execute([event(), event()], "token", dry_run=False, issue_snapshot=[])
        req.assert_not_called()

    def test_prohibit_toolkit_issue_and_controller_events(self):
        for kind in ("controller", "development", "specialist_return"):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(intake.IntakeError, "externally owned"):
                    intake.validate_event(event(kind=kind))

    def test_source_pin_missing_or_spoofed(self):
        for overrides in (
            {"source_revision": "main"},
            {"source_url": "https://github.com/other/repo/pull/1"},
            {"source_repository": "invalid"},
            {"responsible_owner": ""},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(intake.IntakeError):
                    intake.validate_event(event(**overrides))

    def test_assurance_outcome_cannot_be_imported_by_intake(self):
        for field in ("assurance_determination", "specialist_result"):
            with self.assertRaisesRegex(intake.IntakeError, "invent"):
                intake.validate_event(event(**{field: "PASS"}))

    def test_bad_controller_anchor_rejected(self):
        with self.assertRaisesRegex(intake.IntakeError, "controller issue"):
            intake.validate_event(event(controller_issue_url="https://github.com/x/y/issues/2"))

    def test_apply_writes_to_registry_only(self):
        with patch.object(intake, "request", return_value={
            "number": 7, "html_url": "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/7"
        }) as req:
            result = intake.execute([event()], "test-token", dry_run=False, issue_snapshot=[])
        self.assertEqual(result[0]["action"], "created")
        self.assertEqual(req.call_args.args[1], intake.URL)
        self.assertNotIn("rahp-toolkit", req.call_args.args[1])
        self.assertIn("No PASS is asserted", req.call_args.args[3]["body"])

    def test_error_preserves_no_false_receipt(self):
        with patch.object(intake, "request", side_effect=intake.IntakeError("GitHub HTTP 403")):
            with self.assertRaises(intake.IntakeError):
                intake.execute([event()], "token", dry_run=False, issue_snapshot=[])

    def test_pagination_covers_page_six(self):
        pages = []
        def fake(method, path, token, payload=None):
            page = int(path.split("page=")[-1])
            pages.append(page)
            return [{}] * 100 if page < 6 else [{"number": 501}]
        with patch.object(intake, "request", side_effect=fake):
            out = intake.read_all("token")
        self.assertEqual(pages, [1, 2, 3, 4, 5, 6])
        self.assertEqual(len(out), 501)


if __name__ == "__main__":
    unittest.main()
