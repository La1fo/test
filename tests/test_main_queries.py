import unittest
from contextlib import contextmanager

from backend import main
from backend.database import DBContract


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestMainQueries(unittest.TestCase):
    def setUp(self):
        self.contract = DBContract(
            "site_leaderboard",
            "site_public_users",
            "site_public_locations",
            "site_achievements_overview",
            "site_auth_users",
        )

    def _patch_connection(self, cursor):
        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        main.get_db_contract = lambda: self.contract
        main.get_connection = fake_conn

        def restore():
            main.get_db_contract = old_contract
            main.get_connection = old_conn

        return restore

    def test_load_leaderboard_uses_contract_view_and_new_names(self):
        rows = [(1, "alice", 102, 2, 2, "Ранг 2", 1)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            result, warning = main._load_leaderboard()
            self.assertIsNone(warning)
            self.assertIn(f"FROM {self.contract.leaderboard_view}", cursor.query)
            self.assertEqual(result[0].total_gp, 102)
            self.assertEqual(result[0].rank_level, 2)
            self.assertEqual(result[0].gp_in_rank, 2)
            self.assertEqual(result[0].rank_name, "🟢 Исследователь 2")
            self.assertEqual(result[0].gp_display, "2")
        finally:
            restore()


    def test_leaderboard_keeps_writer_rank_name_from_view(self):
        rows = [(10, "mira", 1450, 11, 400, "⭐ Мастер-картограф", 3)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            result, warning = main._load_leaderboard()
            self.assertIsNone(warning)
            self.assertEqual(result[0].rank_name, "⭐ Мастер-картограф")
            self.assertEqual(result[0].gp_display, "400")
        finally:
            restore()

    def test_profile_keeps_writer_rank_name_from_view(self):
        rows = [(11, "terra", 1300, 11, 400, "⭐ Мастер-картограф", 12)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            profile, warning = main._load_profile(11)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_name, "⭐ Мастер-картограф")
            self.assertEqual(profile.gp_display, "400")
        finally:
            restore()

    def test_profile_uses_contract_view_and_rank_for_99_gp(self):
        rows = [(7, "neo", 99, 1, 99, "Ранг 1", 3)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            profile, warning = main._load_profile(7)
            self.assertIsNone(warning)
            self.assertIn(f"FROM {self.contract.public_users_view}", cursor.query)
            self.assertEqual(profile.rank_level, 1)
            self.assertEqual(profile.gp_in_rank, 99)
            self.assertEqual(profile.rank_name, "🟢 Исследователь 1")
            self.assertEqual(profile.gp_display, "99")
        finally:
            restore()

    def test_profile_rank_for_102_gp(self):
        rows = [(8, "trinity", 102, 2, 2, "Ранг 2", 4)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            profile, warning = main._load_profile(8)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_level, 2)
            self.assertEqual(profile.gp_in_rank, 2)
            self.assertEqual(profile.rank_name, "🟢 Исследователь 2")
            self.assertEqual(profile.total_gp, 102)
            self.assertEqual(profile.gp_display, "2")
        finally:
            restore()

    def test_profile_rank_for_199_gp(self):
        rows = [(12, "switch", 199, 2, 99, "Ранг 2", 4)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            profile, warning = main._load_profile(12)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_name, "🟢 Исследователь 2")
            self.assertEqual(profile.gp_display, "99")
        finally:
            restore()

    def test_profile_shows_cartographer_at_900_plus(self):
        rows = [(9, "atlas", 950, 10, 50, "🟣 Картограф", 7)]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            profile, warning = main._load_profile(9)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_name, "🟣 Картограф")
            self.assertEqual(profile.gp_display, "50")
        finally:
            restore()

    def test_master_cartographer_only_for_top_10(self):
        self.assertEqual(main._writer_rank_name(1300, 5), "⭐ Мастер-картограф")
        self.assertEqual(main._writer_rank_name(1300, 11), "🟣 Картограф")
        self.assertEqual(main._writer_rank_name(1500, None), "🟣 Картограф")
        self.assertEqual(main._format_gp_display(1300, 400, "⭐ Мастер-картограф"), "400")
        self.assertEqual(main._format_gp_display(1500, 600, "⭐ Мастер-картограф"), "600")
        self.assertEqual(main._format_gp_display(102, 2, "🟢 Исследователь 2"), "2")
        self.assertEqual(main._format_gp_display(199, 99, "🟢 Исследователь 2"), "99")

    def test_achievements_uses_contract_view(self):
        rows = [
            ("a1", "always", "Always", "desc", 10, False),
            ("a2", "season", "Season", "desc2", 20, True),
        ]
        cursor = FakeCursor(rows)
        restore = self._patch_connection(cursor)
        try:
            permanent, seasonal, warning = main._load_achievements()
            self.assertIsNone(warning)
            self.assertIn(f"FROM {self.contract.achievements_view}", cursor.query)
            self.assertEqual(permanent[0].code, "always")
            self.assertEqual(seasonal[0].code, "season")
        finally:
            restore()


if __name__ == "__main__":
    unittest.main()
