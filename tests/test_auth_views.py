import unittest
from contextlib import contextmanager

from fastapi import HTTPException

from backend.api import auth
from backend.database import DBContract


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
        old_verify_password = auth.verify_password
        old_create_token = auth.create_access_token
        auth.get_db_contract = lambda: self.contract
        auth.get_connection = fake_conn
        auth.verify_password = lambda plain, hashed: True
        auth.create_access_token = lambda data: "token"

        def restore():
            auth.get_db_contract = old_contract
            auth.get_connection = old_conn
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

    def test_register_email_account_creates_user_and_auth_rows(self):
        calls = []

        class RegCursor(FakeCursor):
            def __init__(self):
                super().__init__(row=None)
                self._last_query = ""
                self._params = None

            def execute(self, query, params=None):
                self._last_query = " ".join(query.split()).lower()
                self._params = params
                calls.append((self._last_query, params))

            def fetchall(self):
                if "information_schema.columns" in self._last_query:
                    return [("id",), ("username",), ("telegram_id",), ("moderation_locations",)]
                return []

            def fetchone(self):
                if "where lower(username)" in self._last_query:
                    return None
                if "where lower(email)" in self._last_query and "from users" in self._last_query:
                    return None
                if "returning id" in self._last_query and "insert into users" in self._last_query:
                    return (501,)
                return None

        cursor = RegCursor()
        conn = FakeConnection(cursor)
        conn.committed = False
        conn.rolled_back = False
        conn.commit = lambda: setattr(conn, "committed", True)
        conn.rollback = lambda: setattr(conn, "rolled_back", True)

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield conn

        old_conn = auth.get_connection
        old_ro = auth.DB_READ_ONLY
        auth.get_connection = fake_conn
        auth.DB_READ_ONLY = False
        try:
            user_id = auth.register_email_account(username="new_user", email="new@example.com", password="s3cr3tpass")
            self.assertEqual(user_id, 501)
            self.assertTrue(conn.committed)
            self.assertFalse(conn.rolled_back)
            self.assertTrue(any("insert into users" in q for q, _ in calls))
            self.assertFalse(any("insert into site_auth_accounts" in q for q, _ in calls))
        finally:
            auth.get_connection = old_conn
            auth.DB_READ_ONLY = old_ro

    def test_register_email_account_duplicate_email(self):
        class RegCursor(FakeCursor):
            def __init__(self):
                super().__init__(row=None)
                self._last_query = ""

            def execute(self, query, params=None):
                self._last_query = " ".join(query.split()).lower()

            def fetchall(self):
                if "information_schema.columns" in self._last_query:
                    return [("id",), ("username",)]
                return []

            def fetchone(self):
                if "where lower(username)" in self._last_query:
                    return None
                if "where lower(email)" in self._last_query and "from users" in self._last_query:
                    return (1,)
                return None

        conn = FakeConnection(RegCursor())
        conn.rollback = lambda: None
        conn.commit = lambda: None

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield conn

        old_conn = auth.get_connection
        old_ro = auth.DB_READ_ONLY
        auth.get_connection = fake_conn
        auth.DB_READ_ONLY = False
        try:
            with self.assertRaises(HTTPException):
                auth.register_email_account(username="new_user", email="dup@example.com", password="s3cr3tpass")
        finally:
            auth.get_connection = old_conn
            auth.DB_READ_ONLY = old_ro

    def test_login_after_registration_reads_local_auth_table(self):
        class Cursor:
            def __init__(self):
                self._last_query = ""
                self._params = None
                self.saved_hash = auth.get_password_hash("supersecret")

            def execute(self, query, params=None):
                self._last_query = " ".join(query.split()).lower()
                self._params = params

            def fetchone(self):
                if "select user_id, hashed_password" in self._last_query:
                    return (700, self.saved_hash)
                return None

            def fetchall(self):
                return []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        cursor = Cursor()

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        old_conn = auth.get_connection
        old_contract = auth.get_db_contract
        old_create_token = auth.create_access_token
        auth.get_connection = fake_conn
        auth.get_db_contract = lambda: self.contract
        auth.create_access_token = lambda data: "token"
        try:
            result = auth.login_email(email="new@example.com", password="supersecret")
            self.assertEqual(result["user_id"], 700)
            self.assertIn(self.contract.auth_users_view, cursor._last_query)
        finally:
            auth.get_connection = old_conn
            auth.get_db_contract = old_contract
            auth.create_access_token = old_create_token




if __name__ == "__main__":
    unittest.main()
