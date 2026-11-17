import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/audit_toolkit_issue_writers.py"
SPEC = importlib.util.spec_from_file_location("audit_toolkit_issue_writers", MODULE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
REVISION = "a" * 40


def fixtures(base: Path):
    for name, spec in audit.EXPECTED.items():
        lines = ["name: test", "permissions:", "  issues: write"]
        lines.extend("python3 " + audit.PUBLISHER for _ in range(spec["publisher"]))
        lines.extend("python3 " + audit.INCIDENT for _ in range(spec["incident"]))
        lines.extend("python3 " + dep for dep in spec["consumer"])
        (base / name).write_text("\n".join(lines) + "\n")
    (base / "safe-other.yml").write_text("name: safe\npermissions:\n  contents: read\n")


class PublicationInventoryTests(unittest.TestCase):
    def with_fixture(self, apply):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            fixtures(path)
            return apply(path)

    def test_exact_inventory_is_not_cutover_authority(self):
        def exercise(path):
            errors, receipt = audit.audit(path, REVISION)
            self.assertEqual(errors, [])
            self.assertEqual(receipt["producer_call_count"], 10)
            self.assertEqual(receipt["incident_call_count"], 1)
            self.assertTrue(receipt["inventory_complete"])
            self.assertFalse(receipt["cutover_authorized"])
            self.assertFalse(receipt["registry_issue_publication_authorized"])
        self.with_fixture(exercise)

    def test_self_test_reference_is_not_a_writer(self):
        def exercise(path):
            (path / "validate.yml").write_text(
                "steps:\n  - run: python3 " + audit.INCIDENT + " /tmp/noop.json --self-test\n"
            )
            errors, report = audit.audit(path, REVISION)
            self.assertEqual(errors, [])
            self.assertEqual(report["incident_call_count"], 1)
        self.with_fixture(exercise)

    def test_multiline_transfer_preflight_is_not_a_publisher(self):
        def exercise(path):
            target = path / "dtg-portfolio-materiality-handoff.yml"
            with target.open("a") as out:
                out.write("          python3 " + audit.PUBLISHER + " " + chr(92) + "\n")
                out.write("            --check-transfers " + chr(92) + "\n")
                out.write("            out/combined.json out/dpip.json\n")
            errors, report = audit.audit(path, REVISION)
            self.assertEqual(errors, [])
            self.assertEqual(report["producer_call_count"], 10)
        self.with_fixture(exercise)

    def test_readonly_flag_in_separate_command_does_not_hide_writer(self):
        def exercise(path):
            target = path / "dtg-portfolio-materiality-handoff.yml"
            with target.open("a") as out:
                out.write("          python3 " + audit.PUBLISHER + " " + chr(92) + "\n")
                out.write("            --events out/combined.json\n")
                out.write("          echo --check-transfers\n")
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("publisher call-site drift" in e for e in errors))
        self.with_fixture(exercise)

    def test_unexpected_writer_fails_closed(self):
        def exercise(path):
            (path / "surprise.yml").write_text("permissions:\n  issues: write\n")
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("unknown issue-write workflow" in e for e in errors))
        self.with_fixture(exercise)

    def test_missing_publisher_fails(self):
        def exercise(path):
            target = path / "instance-watch.yml"
            target.write_text(target.read_text().replace(
                "python3 " + audit.PUBLISHER, "", 1))
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("publisher call-site drift" in e for e in errors))
        self.with_fixture(exercise)

    def test_removed_consumer_fails(self):
        def exercise(path):
            target = path / "dpip-lifecycle.yml"
            target.write_text(target.read_text().replace(
                "tools/dpip_return_reconcile.py", "tools/unknown.py"))
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("consumer drift" in e for e in errors))
        self.with_fixture(exercise)

    def test_unknown_direct_api_writer_fails(self):
        def exercise(path):
            (path / "safe-other.yml").write_text("steps:\n  - run: gh issue create --title incident\n")
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("direct issue API writer" in e for e in errors))
        self.with_fixture(exercise)

    def test_expected_workflow_missing_fails(self):
        def exercise(path):
            (path / "review-workers.yml").unlink()
            errors, _ = audit.audit(path, REVISION)
            self.assertTrue(any("expected workflow absent" in e for e in errors))
        self.with_fixture(exercise)

    def test_invalid_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned"):
            audit.audit(Path("."), "main")


if __name__ == "__main__":
    unittest.main()
