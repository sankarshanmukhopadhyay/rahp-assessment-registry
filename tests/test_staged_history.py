import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_staged_archive import check

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "archive/content/2026-11-16"


class StagedHistoryTests(unittest.TestCase):
    def test_real_package_valid(self):
        self.assertEqual(check(PACKAGE), [])

    def test_missing_archive_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            original = json.loads((PACKAGE / "manifest.json").read_text())
            (p / "manifest.json").write_text(json.dumps(original))
            failures = check(p)
            self.assertIn("missing issues archive", failures)

    def test_false_full_timeline_claim_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            original = json.loads((PACKAGE / "manifest.json").read_text())
            original["complete_full_timeline_mirror"] = True
            (p / "manifest.json").write_text(json.dumps(original))
            self.assertIn("false complete-timeline claim", check(p))

    def test_modified_compressed_bytes_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            original = json.loads((PACKAGE / "manifest.json").read_text())
            (p / "manifest.json").write_text(json.dumps(original))
            (p / "issues.jsonl.gz").write_bytes(b"not-the-original")
            self.assertIn("issues compressed digest mismatch", check(p))


if __name__ == "__main__":
    unittest.main()
