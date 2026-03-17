import unittest
from contextlib import contextmanager

from backend import database


VIEWS_QUERY = """
        SELECT 1
        FROM information_schema.views
        WHERE table_schema='public' AND table_name=%s
        LIMIT 1
        """
COLUMNS_QUERY = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """


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
        return value if isinstance(value, list) else [value]

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
    def setUp(self):
        self.contract = database.DBContract(
            "site_leaderboard",
            "site_public_users",
            "site_public_locations",
            "site_achievements_overview",
            "site_auth_users",
        )

    def _build_scripted_success(self):
        scripted = {}

        for view in (
            self.contract.leaderboard_view,
            self.contract.public_users_view,
            self.contract.public_locations_view,
            self.contract.achievements_view,
            self.contract.auth_users_view,
        ):
            scripted[(VIEWS_QUERY, (view,))] = (1,)

        scripted[(COLUMNS_QUERY, (self.contract.leaderboard_view,))] = [
            ("user_id",), ("username",), ("total_gp",), ("rank_level",),
            ("gp_in_rank",), ("rank_name",), ("position",),
        ]
        scripted[(COLUMNS_QUERY, (self.contract.public_users_view,))] = [
            ("user_id",), ("username",), ("telegram_id",), ("total_gp",),
            ("rank_level",), ("gp_in_rank",), ("rank_name",), ("approved_locations",),
        ]
        scripted[(COLUMNS_QUERY, (self.contract.public_locations_view,))] = [
            ("location_id",), ("user_id",),
        ]
        scripted[(COLUMNS_QUERY, (self.contract.achievements_view,))] = [
            ("achievement_id",), ("code",), ("name",), ("description",),
            ("completed_count",), ("is_seasonal",),
        ]
        scripted[(COLUMNS_QUERY, (self.contract.auth_users_view,))] = [
            ("user_id",), ("username",), ("telegram_id",), ("email",), ("hashed_password",),
        ]
        return scripted

    def _run_validation_with_script(self, scripted):
        cursor = FakeCursor(scripted)

        @contextmanager
        def fake_get_connection(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        old_contract = database.get_db_contract
        old_connection = database.get_connection
        try:
            database.get_db_contract = lambda: self.contract
            database.get_connection = fake_get_connection
            return database.validate_db_contract()
        finally:
            database.get_db_contract = old_contract
            database.get_connection = old_connection

    def test_validate_db_contract_success(self):
        ok, errors = self._run_validation_with_script(self._build_scripted_success())
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_failure_on_missing_site_auth_users(self):
        scripted = self._build_scripted_success()
        scripted[(VIEWS_QUERY, (self.contract.auth_users_view,))] = None
        ok, errors = self._run_validation_with_script(scripted)
        self.assertFalse(ok)
        self.assertTrue(any(self.contract.auth_users_view in err for err in errors))

    def test_failure_on_missing_telegram_id_in_site_public_users(self):
        scripted = self._build_scripted_success()
        scripted[(COLUMNS_QUERY, (self.contract.public_users_view,))] = [
            ("user_id",), ("username",), ("total_gp",), ("rank_level",),
            ("gp_in_rank",), ("rank_name",), ("approved_locations",),
        ]
        ok, errors = self._run_validation_with_script(scripted)
        self.assertFalse(ok)
        self.assertTrue(any("telegram_id" in err for err in errors))

    def test_failure_on_missing_description_in_achievements(self):
        scripted = self._build_scripted_success()
        scripted[(COLUMNS_QUERY, (self.contract.achievements_view,))] = [
            ("achievement_id",), ("code",), ("name",),
            ("completed_count",), ("is_seasonal",),
        ]
        ok, errors = self._run_validation_with_script(scripted)
        self.assertFalse(ok)
        self.assertTrue(any("description" in err for err in errors))

    def test_legacy_mode_disabled_by_default(self):
        self.assertFalse(database.LEGACY_SCHEMA_COMPAT)
        with self.assertRaises(RuntimeError):
            database.resolve_table_mapping()


if __name__ == "__main__":
    unittest.main()
