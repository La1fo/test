import unittest
from contextlib import contextmanager

from backend import main
from backend.database import DBContract


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query):
        self.query = query

    def fetchall(self):
        return self.rows

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
    def test_load_leaderboard(self):
        rows = [
            ("alice", "Картограф", 1500),
            ("bob", "Исследователь 2", 320),
        ]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: DBContract(
                "site_leaderboard",
                "site_public_users",
                "site_public_locations",
                "site_achievements_overview",
            )
            main.get_connection = fake_conn

            result, warning = main._load_leaderboard()
            self.assertIsNone(warning)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].username, "@alice")
            self.assertEqual(result[0].points, 1500)
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn

    def test_load_achievements_split(self):
        rows = [
            ("a1", "Always", "desc", 100, False),
            ("a2", "Season", "desc2", 50, True),
        ]

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(rows)

        old_contract = main.get_db_contract
        old_conn = main.get_connection
        try:
            main.get_db_contract = lambda: DBContract(
                "site_leaderboard",
                "site_public_users",
                "site_public_locations",
                "site_achievements_overview",
            )
            main.get_connection = fake_conn

            permanent, seasonal, warning = main._load_achievements()
            self.assertIsNone(warning)
            self.assertEqual(len(permanent), 1)
            self.assertEqual(len(seasonal), 1)
            self.assertEqual(permanent[0].name, "Always")
            self.assertEqual(seasonal[0].name, "Season")
        finally:
            main.get_db_contract = old_contract
            main.get_connection = old_conn


if __name__ == "__main__":
    unittest.main()
