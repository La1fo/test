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


def _views_queries(contract):
    return [
        ("leaderboard", contract.leaderboard_view),
        ("public_users", contract.public_users_view),
        ("public_locations", contract.public_locations_view),
        ("achievements", contract.achievements_view),
        ("auth_users", contract.auth_users_view),
    ]


class TestDBContractValidation(unittest.TestCase):
    def _build_scripted_success(self, contract):
        scripted = {}
        for _, view in _views_queries(contract):
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
        )] = [
            ("user_id",), ("username",), ("total_gp",), ("rank_level",),
            ("gp_in_rank",), ("rank_name",), ("position",),
        ]
        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.public_users_view,),
        )] = [
            ("user_id",), ("username",), ("telegram_id",), ("total_gp",),
            ("rank_level",), ("gp_in_rank",), ("rank_name",), ("approved_locations",),
        ]
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
            ("achievement_id",), ("code",), ("name",), ("description",),
            ("completed_count",), ("is_seasonal",),
        ]
        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.auth_users_view,),
        )] = [
            ("user_id",), ("username",), ("telegram_id",), ("email",), ("hashed_password",),
        ]
        return scripted

    def test_validate_db_contract_success(self):
        contract = database.DBContract(
            "site_leaderboard", "site_public_users", "site_public_locations", "site_achievements_overview", "site_auth_users"
        )
        scripted = self._build_scripted_success(contract)
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

    def test_validate_db_contract_failure_missing_columns(self):
        contract = database.DBContract(
            "site_leaderboard", "site_public_users", "site_public_locations", "site_achievements_overview", "site_auth_users"
        )
        scripted = self._build_scripted_success(contract)
        # remove required leaderboard column 'position'
        scripted[(
            """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
            (contract.leaderboard_view,),
        )] = [
            ("user_id",), ("username",), ("total_gp",), ("rank_level",),
            ("gp_in_rank",), ("rank_name",),
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
            self.assertFalse(ok)
            self.assertTrue(any("position" in e for e in errors))
        finally:
            database.get_db_contract = old_contract
            database.get_connection = old_connection

    def test_legacy_mode_disabled_by_default(self):
        self.assertFalse(database.LEGACY_SCHEMA_COMPAT)
        with self.assertRaises(RuntimeError):
            database.resolve_table_mapping()


if __name__ == "__main__":
    unittest.main()
