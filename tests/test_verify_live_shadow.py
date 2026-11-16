import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_live_shadow import verify_shadow


class LiveShadowTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 16)
        self.source = [{"finding_id": "f001"}]
        self.routed = [{"finding": {"finding_id": "f001"}, "outcome": "combined"}]
        self.opts = {"source_date": "2026-11-16",
                     "toolkit_revision": "a" * 40,
                     "monitor_revision": "b" * 40,
                     "today": self.today}

    def check(self, source=None, fetched=None, opts=None):
        return verify_shadow(self.source if source is None else source,
                             self.source if fetched is None else fetched,
                             self.routed, [], [], [],
                             **(self.opts if opts is None else opts))

    def test_exact_source_can_qualify_shadow_only(self):
        errors, outcome = self.check()
        self.assertEqual(errors, [])
        self.assertEqual(outcome["effects"]["issues_created"], 0)
        self.assertEqual(outcome["effects"]["assurance_determination"], "not_assessed")
        self.assertTrue(outcome["effects"]["fresh_monitor_coverage"])

    def test_changed_main_snapshot_race_fails(self):
        errors, _ = self.check(fetched=[{"finding_id": "different"}])
        self.assertTrue(any("does not match pinned" in x for x in errors))

    def test_stale_snapshot_fails(self):
        options = dict(self.opts, source_date="2026-11-13")
        errors, _ = self.check(opts=options)
        self.assertTrue(any("two-day UTC" in x for x in errors))

    def test_future_snapshot_fails(self):
        options = dict(self.opts, source_date="2026-11-17")
        errors, _ = self.check(opts=options)
        self.assertTrue(any("two-day UTC" in x for x in errors))

    def test_two_day_boundary_valid(self):
        options = dict(self.opts, source_date="2026-11-14")
        errors, outcome = self.check(opts=options)
        self.assertEqual(errors, [])
        self.assertEqual(outcome["source"]["age_days"], 2)

    def test_missing_source_rejected(self):
        errors, _ = self.check(source=[])
        self.assertTrue(any("does not match pinned" in x for x in errors))

    def test_unpinned_toolkit_rejected(self):
        options = dict(self.opts, toolkit_revision="main")
        errors, _ = self.check(opts=options)
        self.assertTrue(any("immutable commit" in x for x in errors))


if __name__ == "__main__":
    unittest.main()
