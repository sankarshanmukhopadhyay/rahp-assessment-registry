import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_dtg_replay import validate_replay


class ReplayVerifierTests(unittest.TestCase):
    def test_positive_structural_result_does_not_claim_assurance(self):
        finding = {"finding_id": "f-001"}
        errors, result = validate_replay(
            [finding], [{"finding": finding, "outcome": "combined"}],
            [{"assessment_key": "dtg:combined:a", "body": "review"}], [], [],
            toolkit_revision="a" * 40, monitor_revision="b" * 40,
            snapshot_date="2026-11-13")
        self.assertEqual(errors, [])
        self.assertEqual(result["effects"]["assurance_determination"], "not_assessed")
        self.assertFalse(result["effects"]["target_runtime_tested"])

    def test_unpinned_revision_rejected(self):
        errors, _ = validate_replay([], [], [], [], [], toolkit_revision="main",
                                     monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertTrue(any("immutable commit" in x for x in errors))

    def test_empty_snapshot_not_accepted(self):
        errors, _ = validate_replay([], [], [], [], [], toolkit_revision="a" * 40,
                                     monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("empty snapshot is not proof of routing parity", errors)

    def test_forged_routed_finding_rejected(self):
        errors, _ = validate_replay(
            [{"finding_id": "f-001"}],
            [{"finding": {"finding_id": "not-the-source"}, "outcome": "combined"}], [], [], [],
            toolkit_revision="a" * 40, monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("routing item does not originate in pinned source", errors)

    def test_missing_routing_outcome_rejected(self):
        errors, _ = validate_replay(
            [{"finding_id": "f-001"}],
            [{"finding": {"finding_id": "f-001"}}], [], [], [],
            toolkit_revision="a" * 40, monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("routing outcome missing", errors)

    def test_event_without_identity_rejected(self):
        errors, _ = validate_replay(
            [{"finding_id": "f-001"}], [], [{"body": "missing key"}], [], [],
            toolkit_revision="a" * 40, monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("combined: generated event missing body or key", errors)

    def test_unresolved_foreign_finding_rejected(self):
        errors, _ = validate_replay(
            [{"finding_id": "f-001"}], [], [], [], [{"finding_id": "foreign"}],
            toolkit_revision="a" * 40, monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("unresolved finding not in pinned source", errors)

    def test_duplicate_source_finding_rejected(self):
        errors, _ = validate_replay(
            [{"finding_id": "f-001"}, {"finding_id": "f-001"}], [], [], [], [],
            toolkit_revision="a" * 40, monitor_revision="b" * 40, snapshot_date="2026-11-13")
        self.assertIn("source finding IDs are duplicated", errors)


if __name__ == "__main__":
    unittest.main()
