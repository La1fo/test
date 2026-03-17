import unittest
from contextlib import contextmanager

from backend import main
from backend.database import DBContract


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

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
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return FakeCursor(self.rows)

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

    def test_load_leaderboard_contract_columns(self):
        rows = [
            (1, "alice", 102, 2, 2, "Ранг 2", 1),
            (2, "bob", 99, 1, 99, "Ранг 1", 2),
        ]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: self.contract
            main.get_connection = fake_conn
            result, warning = main._load_leaderboard()
            self.assertIsNone(warning)
            self.assertEqual(result[0].total_gp, 102)
            self.assertEqual(result[0].gp_in_rank, 2)
            self.assertEqual(result[0].rank_name, "Ранг 2")
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn

    def test_profile_rank_for_99_gp(self):
        rows = [(7, "neo", 99, None, None, None, 3)]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: self.contract
            main.get_connection = fake_conn
            profile, warning = main._load_profile(7)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_level, 1)
            self.assertEqual(profile.gp_in_rank, 99)
            self.assertEqual(profile.rank_name, "Ранг 1")
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn

    def test_profile_rank_for_102_gp(self):
        rows = [(8, "trinity", 102, None, None, None, 4)]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: self.contract
            main.get_connection = fake_conn
            profile, warning = main._load_profile(8)
            self.assertIsNone(warning)
            self.assertEqual(profile.rank_level, 2)
            self.assertEqual(profile.gp_in_rank, 2)
            self.assertEqual(profile.rank_name, "Ранг 2")
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn

    def test_achievements_via_contract_view(self):
        rows = [
            ("a1", "always", "Always", "desc", 10, False),
            ("a2", "season", "Season", "desc2", 20, True),
        ]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: self.contract
            main.get_connection = fake_conn
            permanent, seasonal, warning = main._load_achievements()
            self.assertIsNone(warning)
            self.assertEqual(permanent[0].code, "always")
            self.assertEqual(seasonal[0].code, "season")
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn


if __name__ == "__main__":
    unittest.main()
