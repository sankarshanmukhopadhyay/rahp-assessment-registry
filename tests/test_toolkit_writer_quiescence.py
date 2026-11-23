import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_toolkit_writer_quiescence as guard


class ToolkitWriterQuiescenceTests(unittest.TestCase):
    def test_quiescent_empty_inventory_is_observation_only(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {"total_count": 0, "workflow_runs": []}
        result = guard.evaluate(fetch)
        self.assertTrue(result["quiescent_at_observation"])
        self.assertFalse(result["exclusive_lock_established"])
        self.assertFalse(result["cutover_authorized"])
        self.assertEqual(len(calls), len(guard.NONTERMINAL))

    def test_all_current_and_retired_toolkit_issue_writers_block(self):
        current = {f".github/workflows/{name}" for name in guard.CURRENT_WRITERS}
        historical = guard.HISTORICAL_WRITERS
        self.assertEqual(guard.WRITERS, current | historical)
        self.assertIn(".github/workflows/dtg-materiality-main.yml", guard.WRITERS)
        self.assertIn(".github/workflows/instance-monitor-main.yml", guard.WRITERS)
        self.assertIn(".github/workflows/instance-watch.yml", guard.WRITERS)
        self.assertIn(".github/workflows/dtg-portfolio-materiality-handoff.yml", guard.WRITERS)

        for path in sorted(guard.WRITERS):
            with self.subTest(path=path):
                def fetch(url):
                    if "status=in_progress" in url:
                        return {"total_count": 1, "workflow_runs": [{
                            "id": 44, "path": path, "status": "in_progress"
                        }]}
                    return {"total_count": 0, "workflow_runs": []}
                result = guard.evaluate(fetch)
                self.assertFalse(result["quiescent_at_observation"])
                self.assertEqual(result["active_writer_runs"], [{
                    "id": 44, "workflow": path, "status": "in_progress"
                }])
                self.assertFalse(result["exclusive_lock_established"])
                self.assertFalse(result["cutover_authorized"])

    def test_actual_current_monitor_run_cannot_look_quiescent(self):
        # GitHub's real run.path for the installed App monitor is the *new*
        # filename, not the predecessor instance-watch.yml.
        def fetch(url):
            if "status=queued" in url:
                return {"total_count": 1, "workflow_runs": [{
                    "id": 45089579389,
                    "path": ".github/workflows/instance-monitor-main.yml",
                    "status": "queued",
                }]}
            return {"total_count": 0, "workflow_runs": []}
        receipt = guard.evaluate(fetch)
        self.assertFalse(receipt["quiescent_at_observation"])
        self.assertEqual(receipt["active_writer_runs"][0]["id"], 45089579389)

    def test_unrelated_workflow_is_not_classified_as_a_writer(self):
        def fetch(url):
            if "status=queued" in url:
                return {"total_count": 1, "workflow_runs": [{
                    "id": 9, "path": ".github/workflows/validate.yml",
                    "status": "queued"
                }]}
            return {"total_count": 0, "workflow_runs": []}
        result = guard.evaluate(fetch)
        self.assertTrue(result["quiescent_at_observation"])
        self.assertEqual(result["checked_nonterminal_runs"], 1)

    def test_malformed_or_partial_inventory_fails_closed(self):
        for response in ({}, {"total_count": 0, "workflow_runs": None},
                         {"workflow_runs": [{"path": ".github/workflows/instance-watch.yml",
                                             "status": "queued"}]}):
            with self.subTest(response=response):
                with self.assertRaises(guard.QuiescenceError):
                    guard.evaluate(lambda url: response)

    def test_wrong_status_for_matching_writer_fails_closed(self):
        def fetch(url):
            if "status=pending" in url:
                return {"total_count": 1, "workflow_runs": [{
                    "id": 17, "path": ".github/workflows/review-workers.yml",
                    "status": "completed"
                }]}
            return {"total_count": 0, "workflow_runs": []}
        with self.assertRaisesRegex(guard.QuiescenceError, "inconsistent"):
            guard.evaluate(fetch)

    def test_nonempty_total_with_empty_page_fails_closed(self):
        with self.assertRaisesRegex(guard.QuiescenceError, "incomplete"):
            guard.evaluate(lambda url: {"total_count": 3, "workflow_runs": []})

    def test_missing_or_malformed_total_fails_closed(self):
        for bad in (None, True, "1", -1):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(guard.QuiescenceError, "total_count"):
                    guard.evaluate(lambda url: {
                        "total_count": bad, "workflow_runs": []})

    def test_total_and_pagination_drift_fail_closed(self):
        def fetch(url):
            if "status=queued" in url:
                if url.endswith("&page=1"):
                    return {"total_count": 101, "workflow_runs": [
                        {"id": i + 1, "path": ".github/workflows/validate.yml",
                         "status": "queued"} for i in range(100)]}
                return {"total_count": 102, "workflow_runs": [
                    {"id": 101, "path": ".github/workflows/validate.yml",
                     "status": "queued"}]}
            return {"total_count": 0, "workflow_runs": []}
        with self.assertRaisesRegex(guard.QuiescenceError, "changed"):
            guard.evaluate(fetch)

    def test_repeated_run_identity_across_pages_fails_closed(self):
        def fetch(url):
            if "status=queued" in url:
                if url.endswith("&page=1"):
                    return {"total_count": 101, "workflow_runs": [
                        {"id": i + 1, "path": ".github/workflows/validate.yml",
                         "status": "queued"} for i in range(100)]}
                return {"total_count": 101, "workflow_runs": [
                    {"id": 1, "path": ".github/workflows/validate.yml",
                     "status": "queued"}]}
            return {"total_count": 0, "workflow_runs": []}
        with self.assertRaisesRegex(guard.QuiescenceError, "repeated"):
            guard.evaluate(fetch)

    def test_consistent_multipage_inventory_is_accepted_as_observation(self):
        def fetch(url):
            if "status=queued" in url:
                if url.endswith("&page=1"):
                    return {"total_count": 101, "workflow_runs": [
                        {"id": i + 1, "path": ".github/workflows/validate.yml",
                         "status": "queued"} for i in range(100)]}
                return {"total_count": 101, "workflow_runs": [
                    {"id": 101, "path": ".github/workflows/validate.yml",
                     "status": "queued"}]}
            return {"total_count": 0, "workflow_runs": []}
        receipt = guard.evaluate(fetch)
        self.assertTrue(receipt["quiescent_at_observation"])
        self.assertEqual(receipt["checked_nonterminal_runs"], 101)
        self.assertFalse(receipt["cutover_authorized"])

    def test_inventory_is_bounded(self):
        def fetch(url):
            page = int(url.rsplit("page=", 1)[1])
            return {"total_count": 10000, "workflow_runs": [{
                "id": (page - 1) * 100 + i + 1, "path": ".github/workflows/validate.yml",
                "status": "queued"
            } for i in range(100)]}
        with self.assertRaisesRegex(guard.QuiescenceError, "pagination"):
            guard.evaluate(fetch)


if __name__ == "__main__":
    unittest.main()
