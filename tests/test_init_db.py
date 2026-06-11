import io
import unittest
from contextlib import redirect_stdout

from backend import init_db


class TestInitDBDiagnostics(unittest.TestCase):
    def test_human_readable_diagnostics_on_contract_errors(self):
        # Import module directly and monkeypatch symbols used in main()
        from backend import database

        old_database_dsn = database.DATABASE_DSN
        old_db_ro = database.DB_READ_ONLY
        old_bootstrap = database.DB_BOOTSTRAP_SCHEMA
        old_legacy = database.LEGACY_SCHEMA_COMPAT
        old_get_contract = database.get_db_contract
        old_validate = database.validate_db_contract

        contract = database.DBContract(
            "site_leaderboard",
            "site_public_users",
            "site_public_locations",
            "site_achievements_overview",
            "site_auth_users",
        )

        try:
            database.DATABASE_DSN = "postgresql://user:pass@db:5432/friendlymap"
            database.DB_READ_ONLY = True
            database.DB_BOOTSTRAP_SCHEMA = False
            database.LEGACY_SCHEMA_COMPAT = False
            database.get_db_contract = lambda: contract
            database.validate_db_contract = lambda: (
                False,
                [
                    "view 'site_auth_users' отсутствует",
                    "view 'site_public_users' не содержит колонки: telegram_id",
                ],
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = init_db.main()
            output = buf.getvalue()

            self.assertEqual(code, 1)
            self.assertIn("Автосоздание схемы: off", output)
            self.assertIn("Schema mode: strict-contract", output)
            self.assertIn("❌ DB contract невалиден:", output)
            self.assertIn("view 'site_auth_users' отсутствует", output)
            self.assertIn("не содержит колонки: telegram_id", output)
        finally:
            database.DATABASE_DSN = old_database_dsn
            database.DB_READ_ONLY = old_db_ro
            database.DB_BOOTSTRAP_SCHEMA = old_bootstrap
            database.LEGACY_SCHEMA_COMPAT = old_legacy
            database.get_db_contract = old_get_contract
            database.validate_db_contract = old_validate

    def test_bootstrap_runs_before_validation_even_when_runtime_is_read_only(self):
        from backend import database, migrations

        old_database_dsn = database.DATABASE_DSN
        old_db_ro = database.DB_READ_ONLY
        old_bootstrap = database.DB_BOOTSTRAP_SCHEMA
        old_legacy = database.LEGACY_SCHEMA_COMPAT
        old_get_contract = database.get_db_contract
        old_validate = database.validate_db_contract
        old_ensure = migrations.ensure_site_schema
        calls = []

        contract = database.DBContract(
            "site_leaderboard",
            "site_public_users",
            "site_public_locations",
            "site_achievements_overview",
            "site_auth_users",
        )

        try:
            database.DATABASE_DSN = "postgresql://user:pass@db:5432/friendlymap"
            database.DB_READ_ONLY = True
            database.DB_BOOTSTRAP_SCHEMA = True
            database.LEGACY_SCHEMA_COMPAT = False
            database.get_db_contract = lambda: contract
            migrations.ensure_site_schema = lambda: calls.append("bootstrap")

            def fake_validate():
                calls.append("validate")
                return True, []

            database.validate_db_contract = fake_validate

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = init_db.main()
            output = buf.getvalue()

            self.assertEqual(code, 0)
            self.assertEqual(calls, ["bootstrap", "validate"])
            self.assertIn("Режим БД: read-only", output)
            self.assertIn("Автосоздание схемы: on", output)
            self.assertIn("Создаём/обновляем таблицы и VIEW сайта", output)
        finally:
            database.DATABASE_DSN = old_database_dsn
            database.DB_READ_ONLY = old_db_ro
            database.DB_BOOTSTRAP_SCHEMA = old_bootstrap
            database.LEGACY_SCHEMA_COMPAT = old_legacy
            database.get_db_contract = old_get_contract
            database.validate_db_contract = old_validate
            migrations.ensure_site_schema = old_ensure


if __name__ == "__main__":
    unittest.main()
