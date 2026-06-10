import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from backend import add_location_service as service
from backend import add_location_contract as contract
from backend.schemas import AddLocationSubmitRequest


class FakeCursor:
    def __init__(self, scripted=None, fail_on_photo=False):
        self.scripted = scripted or {}
        self.fail_on_photo = fail_on_photo
        self.last_query = ""

    def execute(self, query, params=None):
        self.last_query = " ".join(query.split()).lower()
        self._params = params
        if self.fail_on_photo and "insert into photos" in self.last_query:
            raise RuntimeError("photo insert failed")

    def fetchone(self):
        q = self.last_query
        if "select location_id from site_submission_idempotency" in q:
            return self.scripted.get("idempotency")
        if "returning id" in q and "insert into users" in q:
            return (self.scripted.get("user_id", 1001),)
        if "returning id" in q and "insert into locations" in q:
            return (self.scripted.get("location_id", 501),)
        if "select id from users" in q:
            return (self.scripted.get("user_id", 42),)
        if "select id from tags" in q:
            tag = self._params[0]
            if tag == "bad":
                return None
            return (11,)
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False



class TestAddLocationService(unittest.TestCase):
    def setUp(self):
        self.old_media = service.MEDIA_ROOT
        self.old_ro = service.DB_READ_ONLY
        self.old_conn = service.get_connection

        self.tempdir = tempfile.TemporaryDirectory()
        service.MEDIA_ROOT = Path(self.tempdir.name)
        service.DB_READ_ONLY = False

    def tearDown(self):
        service.MEDIA_ROOT = self.old_media
        service.DB_READ_ONLY = self.old_ro
        service.get_connection = self.old_conn
        self.tempdir.cleanup()

    def _payload(self):
        return AddLocationSubmitRequest(
            name="Парк",
            description="Очень длинное описание доступного места",
            coordinates={"latitude": 50.1, "longitude": 30.2},
            tag_ids=["ramp"],
            photos=[{"temp_id": "11111111-1111-1111-1111-111111111111", "filename": "a.jpg", "mime_type": "image/jpeg", "size_bytes": 10}],
            idempotency_key="idem-key-123456",
        )

    def _patch_connection(self, cursor):
        @contextmanager
        def fake_conn(dict_cursor=False):
            _ = dict_cursor
            yield FakeConnection(cursor)

        service.get_connection = fake_conn


    def test_read_only_mode_blocks_submit(self):
        service.DB_READ_ONLY = True
        with self.assertRaises(HTTPException):
            service.submit_location(self._payload(), session_user_id=42)

    def test_submit_requires_site_session_user(self):
        with self.assertRaises(HTTPException):
            service.submit_location(self._payload())

    def test_submit_success(self):
        tmp_file = service.MEDIA_ROOT / "tmp" / "11111111-1111-1111-1111-111111111111-a.jpg"
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file.write_bytes(b"x")

        self._patch_connection(FakeCursor())
        result = service.submit_location(self._payload(), session_user_id=42)
        self.assertEqual(result.location_id, 501)
        self.assertFalse(result.duplicate)
        self.assertTrue((service.MEDIA_ROOT / "locations" / "501").exists())

    def test_idempotency_duplicate(self):
        cursor = FakeCursor(scripted={"idempotency": (777,)})
        self._patch_connection(cursor)
        result = service.submit_location(self._payload(), session_user_id=42)
        self.assertTrue(result.duplicate)
        self.assertEqual(result.location_id, 777)

    def test_rollback_and_file_cleanup_on_failure(self):
        tmp_file = service.MEDIA_ROOT / "tmp" / "11111111-1111-1111-1111-111111111111-a.jpg"
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file.write_bytes(b"x")

        self._patch_connection(FakeCursor(fail_on_photo=True))
        with self.assertRaises(RuntimeError):
            service.submit_location(self._payload(), session_user_id=42)

        self.assertFalse((service.MEDIA_ROOT / "locations" / "501" / "00-a.jpg").exists())

    def test_photo_resolver_supports_legacy_and_uploaded(self):
        self.assertEqual(service.resolve_photo_url("abc", "legacy", None), "/api/photos/abc")
        self.assertEqual(service.resolve_photo_url(None, "uploaded", "locations/1/a.jpg"), "/media/locations/1/a.jpg")

    def test_contract_catalog_matches_site_source_categories(self):
        self.assertEqual(len(contract.TAG_CATALOG), sum(len(v) for v in contract.TAG_CATEGORIES.values()))
        labels = {item["label"] for item in contract.TAG_CATALOG}
        for category, category_labels in contract.TAG_CATEGORIES.items():
            self.assertTrue(any(item["category"] == category for item in contract.TAG_CATALOG))
            for label in category_labels:
                self.assertIn(label, labels)


if __name__ == "__main__":
    unittest.main()
