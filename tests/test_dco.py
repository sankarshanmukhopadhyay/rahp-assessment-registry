import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_dco import signoff_matches


class DCOTest(unittest.TestCase):
    def test_valid_author_footer(self):
        self.assertTrue(signoff_matches("Example Author", "example@users.noreply.github.com",
            "fix: something\\n\\nSigned-off-by: Example Author <example@users.noreply.github.com>\\n".replace("\\n", "\n")))

    def test_wrong_author_is_rejected(self):
        self.assertFalse(signoff_matches("Example Author", "example@users.noreply.github.com",
            "fix: something\n\nSigned-off-by: Another Author <example@users.noreply.github.com>"))

    def test_wrong_email_is_rejected(self):
        self.assertFalse(signoff_matches("Example Author", "example@users.noreply.github.com",
            "fix: something\n\nSigned-off-by: Example Author <not-the-author@example.invalid>"))

    def test_prose_does_not_count(self):
        self.assertFalse(signoff_matches("Example Author", "example@users.noreply.github.com",
            "Please include Signed-off-by: Example Author <example@users.noreply.github.com>\n\nImplementation note."))

    def test_no_footer_is_rejected(self):
        self.assertFalse(signoff_matches("Example Author", "example@users.noreply.github.com", "fix: something"))

    def test_multiple_trailers(self):
        self.assertTrue(signoff_matches("Example Author", "example@users.noreply.github.com",
            "fix: something\n\nSigned-off-by: Example Author <example@users.noreply.github.com>\nReviewed-by: Reviewer <reviewer@example.invalid>"))
