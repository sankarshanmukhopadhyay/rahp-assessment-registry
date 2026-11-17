import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "scripts/check_history_publication.py"
SPEC = importlib.util.spec_from_file_location("check_history_publication", FILE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def make(directory, body="Ordinary history"):
    sizes = {"issues": 2, "comments": 1, "events": 1}
    meta = {}
    for kind, length in sizes.items():
        items = []
        for n in range(1, length + 1):
            item = {"body": body}
            if kind == "issues":
                item.update({"number": n, "html_url":
                             f"https://github.com/{module.SOURCE}/issues/{n}"})
            items.append(item)
        raw = "".join(json.dumps(x) + "\n" for x in items).encode()
        zipped = gzip.compress(raw, mtime=0)
        (directory / f"{kind}.jsonl.gz").write_bytes(zipped)
        meta[kind] = {"source_count": length, "gzip_bytes": len(zipped),
                      "gzip_sha256": hashlib.sha256(zipped).hexdigest(),
                      "raw_sha256": hashlib.sha256(raw).hexdigest()}
    (directory / "manifest.json").write_text(json.dumps({
        "schema": "rahp-registry-source-history-package/v1",
        "source_repository": module.SOURCE,
        "complete_full_timeline_mirror": False,
        "files": meta,
    }))
    return sizes


class SourceHistoryReviewTests(unittest.TestCase):
    def test_positive_integrity_does_not_authorize_publication(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            sizes = make(path)
            report = module.verify(path, sizes)
            self.assertTrue(report["source_history_integrity_verified"])
            self.assertFalse(report["privacy_approved"])
            self.assertFalse(report["archival_completion_gate_met"])

    def test_tampered_archive_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            sizes = make(path)
            with (path / "events.jsonl.gz").open("ab") as f:
                f.write(b"tamper")
            with self.assertRaisesRegex(module.HistoryError, "digest mismatch"):
                module.verify(path, sizes)

    def test_secret_is_counted_without_copying_value(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            value = "ghp_" + "a" * 38
            sizes = make(path, value + " contact@example.org")
            report = module.verify(path, sizes)
            self.assertGreater(report["verified"]["issues"]["potential_sensitive_records"]["github_token"], 0)
            self.assertGreater(report["verified"]["comments"]["contact_detail_records"], 0)
            self.assertNotIn(value, json.dumps(report))

    def test_wrong_issue_identity_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            sizes = make(path)
            original = (path / "issues.jsonl.gz").read_bytes()
            data = gzip.decompress(original).decode().splitlines()
            issue = json.loads(data[0])
            issue["html_url"] = "https://github.com/other/repo/issues/1"
            data[0] = json.dumps(issue)
            raw = ("\n".join(data) + "\n").encode()
            zipped = gzip.compress(raw, mtime=0)
            (path / "issues.jsonl.gz").write_bytes(zipped)
            info = json.loads((path / "manifest.json").read_text())
            info["files"]["issues"].update({
                "gzip_bytes": len(zipped),
                "gzip_sha256": hashlib.sha256(zipped).hexdigest(),
                "raw_sha256": hashlib.sha256(raw).hexdigest()})
            (path / "manifest.json").write_text(json.dumps(info))
            with self.assertRaisesRegex(module.HistoryError, "identity mismatch"):
                module.verify(path, sizes)


if __name__ == "__main__":
    unittest.main()
