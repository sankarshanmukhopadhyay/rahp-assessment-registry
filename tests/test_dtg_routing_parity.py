import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_dtg_routing_outputs import FILES, compare


class ParityTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.old = self.root / "old"
        self.new = self.root / "new"
        self.old.mkdir()
        self.new.mkdir()
        for directory in (self.old, self.new):
            for name in FILES:
                content = '[{"finding": {"finding_id": "x"}, "outcome": "combined"}]\n' if name == "routing.json" else "[]\n" if name.endswith(".json") else "composition-x\n"
                (directory / name).write_text(content)

    def test_identical_results_are_not_assurance(self):
        errors, receipt = compare(self.old, self.new)
        self.assertEqual(errors, [])
        self.assertEqual(receipt["assurance_determination"], "not_assessed")
        self.assertFalse(receipt["controller_or_specialist_return_tested"])

    def test_all_material_output_classes_fail_independently_on_drift(self):
        for name in FILES:
            with self.subTest(name=name):
                original = (self.new / name).read_bytes()
                try:
                    (self.new / name).write_bytes(original + b"\nchanged")
                    errors, receipt = compare(self.old, self.new)
                    self.assertIn(f"parity mismatch: {name}", errors)
                    self.assertFalse(receipt["files"][name]["identical"])
                finally:
                    (self.new / name).write_bytes(original)

    def test_missing_both_sides_is_not_false_parity(self):
        (self.old / "combined-events.json").unlink()
        (self.new / "combined-events.json").unlink()
        errors, _ = compare(self.old, self.new)
        self.assertIn("missing required output: combined-events.json", errors)

    def test_read_only_live_shadow_exercises_both_implementations(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/dtg-live-shadow.yml").read_text()
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("python3 toolkit/tools/dtg_portfolio_routing.py", workflow)
        self.assertIn("python3 registry/ops/dtg/dtg_portfolio_routing.py", workflow)
        self.assertIn("python3 registry/scripts/compare_dtg_routing_outputs.py", workflow)
        self.assertIn("--out build/live/dual-router-parity.json", workflow)
        self.assertIn("python3 registry/scripts/verify_live_shadow.py", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("gh issue create", workflow)

    def test_changed_route_rejected(self):
        (self.new / "routing.json").write_text('[{"outcome": "FAIL"}]\n')
        errors, receipt = compare(self.old, self.new)
        self.assertIn("parity mismatch: routing.json", errors)

    def test_missing_class_output_fails(self):
        (self.new / "dpip-events.json").unlink()
        errors, _ = compare(self.old, self.new)
        self.assertIn("missing required output: dpip-events.json", errors)

    def test_composition_registry_difference_fails(self):
        (self.new / "compositions.txt").write_text("other-composition\n")
        errors, _ = compare(self.old, self.new)
        self.assertIn("parity mismatch: compositions.txt", errors)

    def test_empty_route_not_accepted(self):
        (self.old / "routing.json").write_text("[]\n")
        (self.new / "routing.json").write_text("[]\n")
        errors, _ = compare(self.old, self.new)
        self.assertIn("empty or non-list routing result does not prove parity", errors)


if __name__ == "__main__":
    unittest.main()
