import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import capture_toolkit_history as h


class HistoryCaptureTests(unittest.TestCase):
    def issue(self, number=4, comments=1):
        return {"number": number, "html_url": f"https://github.com/{h.REPOSITORY}/issues/{number}",
                "comments": comments, "body": "source issue body", "state": "closed"}

    def comment(self, number=4):
        return {"id": 11, "issue_url": f"https://api.github.com/repos/{h.REPOSITORY}/issues/{number}",
                "body": "source comment"}

    def event(self, number=4):
        return {"id": 15, "issue": {"number": number}, "event": "closed"}

    def test_core_issue_comments_events(self):
        a, b, c = h.assemble([self.issue()], [self.comment()], [self.event()])
        self.assertEqual((len(a), len(b), len(c)), (1, 1, 1))
        self.assertEqual(a[0]["body"], "source issue body")
        self.assertEqual(b[0]["body"], "source comment")

    def test_pull_requests_not_issues(self):
        issue = dict(self.issue(5, 0), pull_request={"url": "pr"})
        a, b, c = h.assemble([self.issue(), issue], [self.comment()], [self.event()])
        self.assertEqual(len(a), 1)

    def test_missing_comment_rejected(self):
        with self.assertRaisesRegex(h.CaptureError, "comment count mismatch"):
            h.assemble([self.issue()], [], [])

    def test_duplicate_issue_fails(self):
        with self.assertRaisesRegex(h.CaptureError, "duplicate"):
            h.assemble([self.issue(), self.issue()], [self.comment()], [self.event()])

    def test_wrong_source_issue_url_fails(self):
        wrong = dict(self.issue(), html_url="https://example.invalid")
        with self.assertRaisesRegex(h.CaptureError, "URL mismatch"):
            h.assemble([wrong], [self.comment()], [self.event()])

    def test_duplicate_comment_id_fails(self):
        with self.assertRaisesRegex(h.CaptureError, "comment"):
            h.assemble([self.issue(comments=2)], [self.comment(), self.comment()], [])

    def test_foreign_comments_not_retained(self):
        a, b, c = h.assemble([self.issue(comments=0)], [self.comment(8)], [self.event(8)])
        self.assertEqual((len(a), len(b), len(c)), (1, 0, 0))

    def test_issue_fetch_explicitly_includes_closed_history(self):
        urls = []
        def fake(url, token):
            urls.append(url)
            return []
        h.fetch_pages("issues", "fake", requester=fake)
        h.fetch_pages("issues/comments", "fake", requester=fake)
        self.assertIn("&state=all", urls[0])
        self.assertNotIn("state=all", urls[1])

    def test_pagination_until_short_page(self):
        seen = []
        def fake(url, token):
            page = int(url.split("page=")[-1].split("&", 1)[0])
            seen.append(page)
            return [{}] * 100 if page == 1 else [{"number": 1}]
        records, pages = h.fetch_pages("issues", "not-a-real-token", requester=fake)
        self.assertEqual((pages, len(records), seen), (2, 101, [1, 2]))

    def test_pagination_incomplete_fails(self):
        with self.assertRaisesRegex(h.CaptureError, "incomplete source pagination"):
            h.fetch_pages("issues", "test", limit=1, requester=lambda u, t: [{}] * 100)


if __name__ == "__main__":
    unittest.main()
