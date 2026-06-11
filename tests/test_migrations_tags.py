import unittest
from contextlib import contextmanager

from backend import add_location_contract as contract
from backend import migrations


class RecorderCursor:
    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((" ".join(query.split()).lower(), params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class RecorderConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestMigrationsTagCatalog(unittest.TestCase):
    def test_ensure_add_location_schema_seeds_full_site_catalog(self):
        cursor = RecorderCursor()

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield RecorderConn(cursor)

        old_conn = migrations.get_connection
        migrations.get_connection = fake_conn
        try:
            migrations.ensure_add_location_schema()
        finally:
            migrations.get_connection = old_conn

        tag_upserts = [item for item in cursor.calls if "insert into tags" in item[0]]
        self.assertEqual(len(tag_upserts), len(contract.TAG_CATALOG))

        seeded_categories = {params[3] for _, params in tag_upserts}
        self.assertEqual(seeded_categories, set(contract.TAG_CATEGORIES.keys()))

        seeded_labels = {params[2] for _, params in tag_upserts}
        for labels in contract.TAG_CATEGORIES.values():
            for label in labels:
                self.assertIn(label, seeded_labels)

    def test_ensure_auth_schema_creates_auth_table(self):
        cursor = RecorderCursor()

        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield RecorderConn(cursor)

        old_conn = migrations.get_connection
        old_contract = migrations.get_db_contract
        migrations.get_connection = fake_conn
        migrations.get_db_contract = lambda: type("Contract", (), {"auth_users_view": "site_auth_users"})()
        try:
            migrations.ensure_auth_schema()
        finally:
            migrations.get_connection = old_conn
            migrations.get_db_contract = old_contract

        queries = [q for q, _ in cursor.calls]
        self.assertTrue(any("alter table if exists users" in q for q in queries))
        self.assertTrue(any("idx_users_email_lower_unique" in q for q in queries))
        self.assertTrue(any("create view %%i as" in q for q in queries))


if __name__ == "__main__":
    unittest.main()
