import unittest
from contextlib import contextmanager

from backend.api import auth
from backend.database import DBContract
from backend.schemas import TelegramAuthPayload


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.query = ""
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row

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


class TestAuthUsesAuthUsersView(unittest.TestCase):
    def setUp(self):
        self.contract = DBContract(
            "site_leaderboard",
            "site_public_users",
            "site_public_locations",
            "site_achievements_overview",
            "site_auth_users",
        )

    def _patch_auth(self, cursor):
        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        old_contract = auth.get_db_contract
        old_conn = auth.get_connection
        old_verify_tg = auth.verify_telegram_auth
        old_verify_password = auth.verify_password
        old_create_token = auth.create_access_token
        auth.get_db_contract = lambda: self.contract
        auth.get_connection = fake_conn
        auth.verify_telegram_auth = lambda data, token: True
        auth.verify_password = lambda plain, hashed: True
        auth.create_access_token = lambda data: "token"

        def restore():
            auth.get_db_contract = old_contract
            auth.get_connection = old_conn
            auth.verify_telegram_auth = old_verify_tg
            auth.verify_password = old_verify_password
            auth.create_access_token = old_create_token

        return restore

    def test_email_login_uses_auth_users_view(self):
        cursor = FakeCursor((42, "hashed"))
        restore = self._patch_auth(cursor)
        try:
            response = auth.login_email(email="u@example.com", password="secret")
            self.assertEqual(response["user_id"], 42)
            self.assertIn(f"FROM {self.contract.auth_users_view}", cursor.query)
            self.assertNotIn(self.contract.public_users_view, cursor.query)
        finally:
            restore()

    def test_telegram_login_uses_auth_users_view(self):
        payload = TelegramAuthPayload(id=77, auth_date=123, hash="ok", first_name="u")
        cursor = FakeCursor((77,))
        restore = self._patch_auth(cursor)
        try:
            response = auth.login_telegram(payload)
            self.assertEqual(response["user_id"], 77)
            self.assertIn(f"FROM {self.contract.auth_users_view}", cursor.query)
            self.assertNotIn(self.contract.public_users_view, cursor.query)
        finally:
            restore()


if __name__ == "__main__":
    unittest.main()
