"""Live routing freshness must not erase independently pinned historical tag evidence."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / ".github/workflows/dtg-live-shadow.yml"
HISTORICAL_SHA = "7e2813c8daf867a21e4064513cc83612726aeb44"


class ShadowSourceEpochTests(unittest.TestCase):
    def test_historical_tags_bind_to_original_snapshot_not_live_route(self):
        content = FLOW.read_text(encoding="utf-8")
        self.assertIn("ref: " + HISTORICAL_SHA, content)
        self.assertIn("path: monitor-historical", content)
        self.assertIn("--findings monitor-historical/data/findings/2026/11/16.json", content)
        self.assertIn("--evidence registry/ops/migration/evidence/toolkit-1208-release-tags.json", content)
        self.assertNotIn(
            "--evidence registry/ops/migration/evidence/toolkit-1208-release-tags.json \\\n            --findings build/live/findings.json", content)

    def test_fresh_live_qualification_and_read_only_semantics_are_unchanged(self):
        content = FLOW.read_text(encoding="utf-8")
        self.assertIn("ref: main\n          path: monitor", content)
        self.assertIn("--lookback-days 2 --output build/live/findings.json", content)
        self.assertIn("--findings build/live/findings.json", content)
        self.assertIn("assert shadow['effects']['issues_created'] == 0", content)
        self.assertIn("assert receipt['cutover_authorized'] is False", content)
        self.assertNotIn("issues: write", content)


if __name__ == "__main__":
    unittest.main()
