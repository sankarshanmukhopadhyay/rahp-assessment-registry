import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_history_archive import package, PackageError


class PackageHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "source"
        self.dst = self.root / "output"
        self.src.mkdir()
        self.meta = {"schema": "rahp-source-issue-history-export/v1",
                     "source_repository": "sankarshanmukhopadhyay/rahp-toolkit",
                     "complete_full_timeline_mirror": False, "records": {}}
        for key, lines in (("issues", [b'{"number":1}\n'] * 769),
                           ("comments", [b'{"id":1}\n']), ("events", [b'{"id":2}\n'])):
            content = b"".join(lines)
            (self.src / f"{key}.jsonl").write_bytes(content)
            self.meta["records"][key] = {
                "count": len(lines), "sha256": hashlib.sha256(content).hexdigest()
            }
        self.save()

    def save(self):
        (self.src / "manifest.json").write_text(json.dumps(self.meta))

    def test_deterministic_verified_roundtrip(self):
        a = package(self.src, self.dst)
        self.assertEqual(a["files"]["issues"]["source_count"], 769)
        raw = (self.src / "issues.jsonl").read_bytes()
        self.assertEqual(gzip.decompress((self.dst / "issues.jsonl.gz").read_bytes()), raw)
        one = (self.dst / "issues.jsonl.gz").read_bytes()
        package(self.src, self.dst)
        self.assertEqual((self.dst / "issues.jsonl.gz").read_bytes(), one)

    def test_missing_historical_coverage_fails(self):
        self.meta["records"]["issues"]["count"] = 57
        self.save()
        with self.assertRaisesRegex(PackageError, "incomplete"):
            package(self.src, self.dst)

    def test_tampered_raw_content_fails(self):
        (self.src / "events.jsonl").write_bytes(b"modified\n")
        with self.assertRaisesRegex(PackageError, "digest mismatch"):
            package(self.src, self.dst)

    def test_false_full_timeline_claim_fails(self):
        self.meta["complete_full_timeline_mirror"] = True
        self.save()
        with self.assertRaisesRegex(PackageError, "scope claim"):
            package(self.src, self.dst)

    def test_wrong_source_repository_fails(self):
        self.meta["source_repository"] = "unrelated/repository"
        self.save()
        with self.assertRaisesRegex(PackageError, "not Toolkit"):
            package(self.src, self.dst)

    def test_missing_content_fails(self):
        (self.src / "comments.jsonl").unlink()
        with self.assertRaises(FileNotFoundError):
            package(self.src, self.dst)


if __name__ == "__main__":
    unittest.main()
