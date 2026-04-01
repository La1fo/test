import unittest
from pathlib import Path


class TestTemplates(unittest.TestCase):
    def _read(self, name: str) -> str:
        return Path(f"/workspace/test/frontend/{name}").read_text()

    def test_pages_use_shared_theme_stylesheet(self):
        for page in (self._read("achievements.html"), self._read("leaderboard.html"), self._read("faq.html")):
            self.assertIn("/static/page-theme.css", page)
            self.assertIn('body class="site-theme"', page)

    def test_home_has_email_pill_and_new_hero(self):
        home = self._read("index.html")
        self.assertIn("friendlymapbot@gmail.com", home)
        self.assertIn("email-pill", home)
        self.assertNotIn("Планы", home)
        self.assertNotIn("доступных мест и получай награды", home)
        self.assertNotIn("🚀", home)
        self.assertIn("Добавляй метки и повышайте ранг", home)

    def test_nav_no_login_link(self):
        for file_name in ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html", "login.html"]:
            self.assertNotIn('href="/login"', self._read(file_name))

    def test_achievements_page_no_old_slogan(self):
        achievements = self._read("achievements.html")
        self.assertNotIn("Собирайте баллы, получайте награды и становитесь легендой города.", achievements)

    def test_faq_uses_same_interactive_patterns_as_achievements(self):
        achievements = self._read("achievements.html")
        faq = self._read("faq.html")
        for token in ["interactive-toggle", "expand-section", "expand-content"]:
            self.assertIn(token, achievements)
            self.assertIn(token, faq)

    def test_leaderboard_ui_uses_plain_gp_number(self):
        leaderboard = self._read("leaderboard.html")
        self.assertIn("{{ row.gp_display }}", leaderboard)
        self.assertNotIn("/100", leaderboard)
        self.assertNotIn("/400", leaderboard)
        self.assertNotIn("400+/400", leaderboard)

    def test_faq_no_stale_texts_and_no_support_block(self):
        faq = self._read("faq.html")
        self.assertNotIn("Находиться в разработке", faq)
        self.assertNotIn("chat-widget", faq)
        self.assertNotIn("/api/support", faq)

    def test_jivo_script_present_on_key_pages_and_not_duplicated(self):
        pages = ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html"]
        for file_name in pages:
            html = self._read(file_name)
            self.assertIn('/static/jivo-widget.js', html)
            self.assertEqual(html.count('/static/jivo-widget.js'), 1)

    def test_profile_ui_does_not_use_old_gp_labels(self):
        profile_template = self._read("profile.html")
        self.assertIn("GP:", profile_template)
        self.assertNotIn("Общий GP", profile_template)
        self.assertNotIn("GP в ранге", profile_template)
        self.assertNotIn("GP в текущем ранге", profile_template)


if __name__ == "__main__":
    unittest.main()
