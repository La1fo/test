import io
import unittest
from contextlib import redirect_stdout

from backend import init_db


class TestInitDBDiagnostics(unittest.TestCase):
    def test_human_readable_diagnostics_on_contract_errors(self):
        # Import module directly and monkeypatch symbols used in main()
        from backend import database

        old_bot_db_url = database.BOT_DB_URL
        old_db_ro = database.DB_READ_ONLY
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
            database.BOT_DB_URL = "postgresql://user:pass@db:5432/friendlymap"
            database.DB_READ_ONLY = True
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
            self.assertIn("Schema mode: strict-contract", output)
            self.assertIn("❌ DB contract невалиден:", output)
            self.assertIn("view 'site_auth_users' отсутствует", output)
            self.assertIn("не содержит колонки: telegram_id", output)
        finally:
            database.BOT_DB_URL = old_bot_db_url
            database.DB_READ_ONLY = old_db_ro
            database.LEGACY_SCHEMA_COMPAT = old_legacy
            database.get_db_contract = old_get_contract
            database.validate_db_contract = old_validate


if __name__ == "__main__":
    unittest.main()
