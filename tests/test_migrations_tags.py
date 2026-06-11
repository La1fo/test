import unittest
from contextlib import contextmanager
from pathlib import Path

from backend import add_location_contract as contract
from backend import migrations


class RecorderCursor:
    def __init__(self, fetchone_result=None):
        self.calls = []
        self.fetchone_result = fetchone_result

    def execute(self, query, params=None):
        self.calls.append((" ".join(str(query).split()).lower(), params))

    def fetchone(self):
        return self.fetchone_result

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
        self.assertTrue(any("from information_schema.views" in q for q in queries))
        self.assertTrue(any('create view "public"."site_auth_users" as' in q for q in queries))


class TestMigrationIdentifierHelpers(unittest.TestCase):
    def test_split_relation_name_defaults_to_public_schema(self):
        self.assertEqual(migrations._split_relation_name("site_auth_users"), ("public", "site_auth_users"))

    def test_split_relation_name_accepts_explicit_schema(self):
        self.assertEqual(migrations._split_relation_name("custom.site_auth_users"), ("custom", "site_auth_users"))

    def test_split_relation_name_rejects_unsafe_identifier(self):
        with self.assertRaises(ValueError):
            migrations._split_relation_name("public.site_auth_users;DROP")



    def test_auth_schema_seeds_laifo_admin(self):
        migration_source = Path("/workspace/test/backend/migrations.py").read_text()
        self.assertIn("is_admin BOOLEAN DEFAULT FALSE", migration_source)
        self.assertIn("LOWER(username) = 'laifo'", migration_source)
        self.assertIn("SET is_admin = TRUE", migration_source)


if __name__ == "__main__":
    unittest.main()
