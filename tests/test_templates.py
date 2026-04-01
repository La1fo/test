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

    def test_home_no_plans_old_slogan_or_rocket(self):
        home = Path("/workspace/test/frontend/index.html").read_text()
        self.assertNotIn("Планы", home)
        self.assertNotIn("доступных мест и получай награды", home)
        self.assertNotIn("🚀", home)
        self.assertIn("Добавляй метки и повышайте ранг", home)

    def test_nav_no_login_link(self):
        for file_name in ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html", "login.html"]:
            page = Path(f"/workspace/test/frontend/{file_name}").read_text()
            self.assertNotIn('href="/login"', page)

    def test_achievements_page_no_old_slogan(self):
        achievements = Path("/workspace/test/frontend/achievements.html").read_text()
        self.assertNotIn("Собирайте баллы, получайте награды и становитесь легендой города.", achievements)

    def test_leaderboard_ui_uses_plain_gp_number(self):
        leaderboard = Path("/workspace/test/frontend/leaderboard.html").read_text()
        self.assertIn("{{ row.gp_display }}", leaderboard)
        self.assertNotIn("/100", leaderboard)
        self.assertNotIn("/400", leaderboard)
        self.assertNotIn("400+/400", leaderboard)

    def test_faq_no_stale_texts_and_no_support_block(self):
        faq = Path("/workspace/test/frontend/faq.html").read_text()
        self.assertNotIn("Находиться в разработке", faq)
        self.assertNotIn("chat-widget", faq)
        self.assertNotIn("/api/support", faq)

    def test_profile_ui_does_not_use_old_gp_labels(self):
        profile_template = Path("/workspace/test/frontend/profile.html").read_text()
        self.assertIn("GP:", profile_template)
        self.assertNotIn("Общий GP", profile_template)
        self.assertNotIn("GP в ранге", profile_template)
        self.assertNotIn("GP в текущем ранге", profile_template)


if __name__ == "__main__":
    unittest.main()
