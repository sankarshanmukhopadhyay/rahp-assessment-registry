import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_archive_reference as index


class ArchiveReferenceTests(unittest.TestCase):
    def test_committed_indices_are_reproducible(self):
        rendered = index.render(ROOT)
        self.assertEqual(set(rendered), {
            "archive/issue-index.md", "archive/succession-index.md"})
        for path, content in rendered.items():
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_text(encoding="utf-8"), content)

    def test_full_source_coverage_without_implicit_succession(self):
        rendered = index.render(ROOT)
        full = rendered["archive/issue-index.md"]
        self.assertEqual(
            sum(line.startswith("| [#") for line in full.splitlines()), 769)
        self.assertIn("Toolkit #272", rendered["archive/succession-index.md"])
        self.assertIn("Registry #88", rendered["archive/succession-index.md"])
        self.assertIn("Registry #4", rendered["archive/succession-index.md"])
        self.assertIn("A dash means no *accepted*", full)

    def test_unaccepted_related_source_does_not_create_owner(self):
        # Verify the generator's rendering semantics independently of live case
        # count, without weakening the separate locator ownership validator.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "archive/snapshots").mkdir(parents=True)
            (root / "cases").mkdir()
            source = {"number": 9,
                      "url": "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/9",
                      "title": "Related finding | not a handoff",
                      "state": "open",
                      "classification": "external-assessment-candidate"}
            part = "archive/snapshots/toolkit-issues-2026-11-16-p1.json"
            (root / part).write_text(json.dumps([source]))
            (root / "archive/manifest.json").write_text(json.dumps({
                "partitions": [{"path": part}], "total_issues": 1}))
            (root / "cases/direct.json").write_text(json.dumps({
                "case_id": "direct-1", "owners": {
                    "handoff": "not_applicable", "admission": "direct",
                    "current_active_issue":
                    "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/10"}}))
            with patch.object(index, "verify", return_value={}):
                result = index.render(root)
            self.assertIn("Related finding \\| not a handoff", result["archive/issue-index.md"])
            self.assertIn(" | — |", result["archive/issue-index.md"])
            self.assertNotIn("Toolkit #9", result["archive/succession-index.md"])
            self.assertIn("direct-1", result["archive/succession-index.md"])


if __name__ == "__main__":
    unittest.main()
