import unittest
from pathlib import Path


class TestTemplates(unittest.TestCase):
    def test_pages_use_shared_theme_stylesheet(self):
        achievements = Path("/workspace/test/frontend/achievements.html").read_text()
        leaderboard = Path("/workspace/test/frontend/leaderboard.html").read_text()
        faq = Path("/workspace/test/frontend/faq.html").read_text()
        for page in (achievements, leaderboard, faq):
            self.assertIn("/static/page-theme.css", page)
            self.assertIn('body class="site-theme"', page)

    def test_profile_ui_does_not_use_old_gp_labels(self):
        profile_template = Path("/workspace/test/frontend/profile.html").read_text()
        self.assertIn("GP:", profile_template)
        self.assertNotIn("Общий GP", profile_template)
        self.assertNotIn("GP в ранге", profile_template)
        self.assertNotIn("GP в текущем ранге", profile_template)

    def test_leaderboard_ui_does_not_use_old_gp_labels(self):
        leaderboard_template = Path("/workspace/test/frontend/leaderboard.html").read_text()
        self.assertIn("<th>GP</th>", leaderboard_template)
        self.assertNotIn("Общий GP", leaderboard_template)
        self.assertNotIn("GP в ранге", leaderboard_template)
        self.assertNotIn("GP в текущем ранге", leaderboard_template)


if __name__ == "__main__":
    unittest.main()
