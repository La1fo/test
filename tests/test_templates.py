import unittest
from pathlib import Path


class TestTemplates(unittest.TestCase):
    def _read(self, name: str) -> str:
        return Path(f"/workspace/test/frontend/{name}").read_text()

    def _assert_jivo_widget(self, file_name: str):
        html = self._read(file_name)
        script_tag = '<script src="//code.jivo.ru/widget/FaDWcuzcG6" async></script>'
        self.assertIn(script_tag, html)
        self.assertEqual(html.count(script_tag), 1)
        self.assertIn(f"{script_tag}\n</body>", html)

    def test_pages_use_shared_theme_stylesheet(self):
        for page in (self._read("achievements.html"), self._read("leaderboard.html"), self._read("faq.html")):
            self.assertIn("/static/page-theme.css", page)
            self.assertIn('body class="site-theme"', page)

    def test_home_has_email_pill_and_new_hero(self):
        home = self._read("index.html")
        self.assertIn("friendlymap@example.com", home)
        self.assertIn("email-pill", home)
        self.assertNotIn("Планы", home)
        self.assertNotIn("доступных мест и получай награды", home)
        self.assertNotIn("🚀", home)
        self.assertIn("Добавляй метки и повышайте ранг", home)

    def test_nav_is_auth_aware_and_has_no_logout(self):
        nav = self._read("_nav.html")
        self.assertIn('href="/login"', nav)
        self.assertIn('href="/profile/me"', nav)
        self.assertNotIn('href="/logout"', nav)

    def test_pages_use_shared_nav_include(self):
        for file_name in ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html", "login.html", "add-location.html", "map.html"]:
            self.assertIn('{% include "_nav.html" %}', self._read(file_name))

    def test_nav_has_add_location_link_on_key_pages(self):
        nav = self._read("_nav.html")
        self.assertIn('href="/add-location"', nav)
        self.assertIn('href="/map"', nav)

    def test_login_page_has_registration_and_telegram_blocks(self):
        login = self._read("login.html")
        self.assertIn("Регистрация", login)
        self.assertIn("regUsername", login)
        self.assertIn("/api/session/register", login)
        self.assertIn("Быстрый вход через Telegram", login)
        self.assertIn("/api/session/telegram", login)
        self.assertIn("telegram-widget.js", login)

    def test_logout_available_on_profile_page_only(self):
        profile = self._read("profile.html")
        self.assertIn("/logout?next=/", profile)
        for file_name in ["index.html", "achievements.html", "leaderboard.html", "faq.html", "login.html", "add-location.html", "map.html"]:
            self.assertNotIn("/logout?next=/", self._read(file_name))

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

    def test_no_stale_support_blocks_on_user_pages(self):
        pages = ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html", "login.html", "add-location.html", "map.html"]
        forbidden_tokens = ["chat-widget", "/api/support", "support-form", "support-block"]
        for file_name in pages:
            html = self._read(file_name)
            for token in forbidden_tokens:
                self.assertNotIn(token, html)

        faq = self._read("faq.html")
        self.assertNotIn("Находиться в разработке", faq)

    def test_jivo_script_present_on_home_page(self):
        self._assert_jivo_widget("index.html")

    def test_jivo_script_present_on_achievements_page(self):
        self._assert_jivo_widget("achievements.html")

    def test_jivo_script_present_on_leaderboard_page(self):
        self._assert_jivo_widget("leaderboard.html")

    def test_jivo_script_present_on_faq_page(self):
        self._assert_jivo_widget("faq.html")

    def test_jivo_script_present_on_profile_page(self):
        self._assert_jivo_widget("profile.html")

    def test_jivo_script_present_on_login_page(self):
        self._assert_jivo_widget("login.html")

    def test_jivo_script_present_on_add_location_page(self):
        self._assert_jivo_widget("add-location.html")

    def test_jivo_script_present_on_map_page(self):
        self._assert_jivo_widget("map.html")

    def test_profile_ui_does_not_use_old_gp_labels(self):
        profile_template = self._read("profile.html")
        self.assertIn("GP:", profile_template)
        self.assertNotIn("Общий GP", profile_template)
        self.assertNotIn("GP в ранге", profile_template)
        self.assertNotIn("GP в текущем ранге", profile_template)

    def test_key_pages_have_basic_html_shell(self):
        pages = ["index.html", "achievements.html", "leaderboard.html", "faq.html", "profile.html", "login.html", "add-location.html", "map.html"]
        for file_name in pages:
            html = self._read(file_name)
            self.assertIn("<body", html)
            self.assertIn("</body>", html)
            self.assertIn("</html>", html)

    def test_add_location_template_has_wizard_sections(self):
        page = self._read("add-location.html")
        for token in ["1. Название", "2. Описание", "3. Координаты", "4. Теги", "5. Фото", "6. Preview"]:
            self.assertIn(token, page)
        self.assertIn('/static/add-location.js', page)
        self.assertIn('id="pickerMap"', page)
        self.assertIn('Определить мою геопозицию', page)
        self.assertIn('type="hidden"', page)
        self.assertNotIn('placeholder="Введите широту"', page)
        self.assertNotIn('placeholder="Введите долготу"', page)
        self.assertIn("Для добавления локации нужна авторизация", page)

    def test_geolocation_hooks_present(self):
        add_js = Path("/workspace/test/frontend/add-location.js").read_text()
        map_page = self._read("map.html")
        self.assertIn("navigator.geolocation", add_js)
        self.assertIn("navigator.geolocation", map_page)
        self.assertIn("selectedTagLabels", add_js)

    def test_map_page_uses_db_tag_catalog_api(self):
        map_page = self._read("map.html")
        self.assertIn("/api/map/tags", map_page)
        self.assertIn("loadMapTags", map_page)
        self.assertIn("optgroup", map_page)
        self.assertIn("Вы просматриваете карту как гость", map_page)


if __name__ == "__main__":
    unittest.main()
