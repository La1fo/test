import unittest
from contextlib import contextmanager

from backend import database


class FakeCursor:
    def __init__(self, scripted_results):
        self.scripted_results = scripted_results
        self._last_query = ""
        self._last_params = None

    def execute(self, query, params=None):
        self._last_query = query
        self._last_params = params

    def fetchone(self):
        key = (self._last_query, self._last_params)
        value = self.scripted_results.get(key)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def fetchall(self):
        key = (self._last_query, self._last_params)
        value = self.scripted_results.get(key, [])
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

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


class TestDBContractValidation(unittest.TestCase):
    def test_validate_db_contract_success(self):
        contract = database.DBContract(
            leaderboard_view="site_leaderboard",
            public_users_view="site_public_users",
            public_locations_view="site_public_locations",
            achievements_view="site_achievements_overview",
        )

        scripted = {}
        for view in [
            contract.leaderboard_view,
            contract.public_users_view,
            contract.public_locations_view,
            contract.achievements_view,
        ]:
            scripted[(
                """
        SELECT 1
        FROM information_schema.views
        WHERE table_schema='public' AND table_name=%s
        LIMIT 1
        """,
                (view,),
            )] = (1,)

        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.leaderboard_view,),
        )] = [("user_id",), ("username",), ("gp_points",), ("rank_name",)]

        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.public_users_view,),
        )] = [("user_id",), ("username",), ("telegram_id",), ("email",), ("hashed_password",)]

        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.public_locations_view,),
        )] = [("location_id",), ("user_id",)]

        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.achievements_view,),
        )] = [
            ("achievement_id",),
            ("name",),
            ("description",),
            ("reward_points",),
            ("is_seasonal",),
        ]

        cursor = FakeCursor(scripted)

        @contextmanager
        def fake_get_connection(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        old_contract = database.get_db_contract
        old_connection = database.get_connection
        try:
            database.get_db_contract = lambda: contract
            database.get_connection = fake_get_connection
            ok, errors = database.validate_db_contract()
            self.assertTrue(ok)
            self.assertEqual(errors, [])
        finally:
            database.get_db_contract = old_contract
            database.get_connection = old_connection


if __name__ == "__main__":
    unittest.main()
