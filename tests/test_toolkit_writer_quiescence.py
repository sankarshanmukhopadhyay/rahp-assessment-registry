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
            return {"workflow_runs": []}
        result = guard.evaluate(fetch)
        self.assertTrue(result["quiescent_at_observation"])
        self.assertFalse(result["exclusive_lock_established"])
        self.assertFalse(result["cutover_authorized"])
        self.assertEqual(len(calls), len(guard.NONTERMINAL))

    def test_active_toolkit_writer_blocks(self):
        def fetch(url):
            if "status=in_progress" in url:
                return {"workflow_runs": [{
                    "id": 44, "path": ".github/workflows/dtg-portfolio-materiality-handoff.yml",
                    "status": "in_progress"
                }]}
            return {"workflow_runs": []}
        result = guard.evaluate(fetch)
        self.assertFalse(result["quiescent_at_observation"])
        self.assertEqual(result["active_writer_runs"][0]["id"], 44)

    def test_unrelated_workflow_is_not_classified_as_a_writer(self):
        def fetch(url):
            if "status=queued" in url:
                return {"workflow_runs": [{
                    "id": 9, "path": ".github/workflows/validate.yml",
                    "status": "queued"
                }]}
            return {"workflow_runs": []}
        result = guard.evaluate(fetch)
        self.assertTrue(result["quiescent_at_observation"])
        self.assertEqual(result["checked_nonterminal_runs"], 1)

    def test_malformed_or_partial_inventory_fails_closed(self):
        for response in ({}, {"workflow_runs": None},
                         {"workflow_runs": [{"path": ".github/workflows/instance-watch.yml",
                                             "status": "queued"}]}):
            with self.subTest(response=response):
                with self.assertRaises(guard.QuiescenceError):
                    guard.evaluate(lambda url: response)

    def test_wrong_status_for_matching_writer_fails_closed(self):
        def fetch(url):
            if "status=pending" in url:
                return {"workflow_runs": [{
                    "id": 17, "path": ".github/workflows/review-workers.yml",
                    "status": "completed"
                }]}
            return {"workflow_runs": []}
        with self.assertRaisesRegex(guard.QuiescenceError, "inconsistent"):
            guard.evaluate(fetch)

    def test_inventory_is_bounded(self):
        def fetch(url):
            return {"workflow_runs": [{
                "id": i, "path": ".github/workflows/validate.yml",
                "status": "queued"
            } for i in range(100)]}
        with self.assertRaisesRegex(guard.QuiescenceError, "pagination"):
            guard.evaluate(fetch)


if __name__ == "__main__":
    unittest.main()
