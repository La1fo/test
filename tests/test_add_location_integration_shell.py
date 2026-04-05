import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError
from fastapi import HTTPException

from backend import main
from backend import add_location_contract as contract
from backend.api import add_location
from backend.api import map as map_api
from backend.schemas import AddLocationPreviewRequest, AddLocationSubmitRequest, PhotoMeta, PhotoUploadRequest
from backend.session_auth import SESSION_COOKIE_NAME, create_session_cookie


class TestAddLocationIntegrationShell(unittest.TestCase):
    def _valid_payload(self):
        return {
            "name": "Парк у реки",
            "description": "Есть пандус, просторный вход и доступный туалет.",
            "coordinates": {"latitude": 55.75, "longitude": 37.61},
            "tag_ids": ["ramp", "toilet"],
            "photos": [
                {
                    "temp_id": "tmp-1",
                    "filename": "photo1.jpg",
                    "mime_type": "image/jpeg",
                    "size_bytes": 1024,
                }
            ],
        }

    def test_add_location_route_registered(self):
        paths = {route.path for route in main.app.routes}
        self.assertIn("/add-location", paths)
        self.assertIn("/api/add-location/form-config", paths)
        self.assertIn("/api/add-location/preview", paths)
        self.assertIn("/api/add-location/upload", paths)
        self.assertIn("/api/add-location/submit", paths)
        self.assertIn("/map", paths)
        self.assertIn("/api/map/locations", paths)
        self.assertIn("/api/map/tags", paths)
        self.assertIn("/api/session/me", paths)

    def test_add_location_page_renders_template(self):
        anon = SimpleNamespace(cookies={})
        response = asyncio.run(main.add_location_page(request=anon))
        self.assertEqual(response.status_code, 303)

        auth_request = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(1)})
        response = asyncio.run(main.add_location_page(request=auth_request))
        self.assertEqual(response.template.name, "add-location.html")

    def test_form_config_contract(self):
        old_catalog = add_location.get_tag_catalog
        add_location.get_tag_catalog = lambda: contract.TAG_CATALOG
        config = add_location.get_add_location_form_config()
        add_location.get_tag_catalog = old_catalog
        self.assertEqual(config.writer_integration_enabled, contract.INTEGRATION_ENABLED)
        self.assertEqual(config.max_tags, contract.MAX_TAGS)
        self.assertEqual(config.max_photos, contract.MAX_PHOTOS)
        self.assertEqual(config.max_photo_size_mb, contract.MAX_PHOTO_SIZE_MB)
        self.assertEqual(config.allowed_photo_mime, contract.ALLOWED_PHOTO_MIME)
        self.assertEqual(config.tag_catalog, contract.TAG_CATALOG)
        self.assertGreaterEqual(len(config.tag_catalog), 50)

    def test_form_config_and_map_tags_use_same_db_source(self):
        db_catalog = [
            {"id": "cafe", "label": "кафе", "category": "Еда"},
            {"id": "park", "label": "парк", "category": "Отдых"},
        ]
        old_add_catalog = add_location.get_tag_catalog
        old_map_catalog = map_api.get_tag_catalog
        add_location.get_tag_catalog = lambda: db_catalog
        map_api.get_tag_catalog = lambda: db_catalog
        try:
            form_cfg = add_location.get_add_location_form_config()
            map_tags = map_api.map_tags()
            self.assertEqual(form_cfg.tag_catalog, map_tags["tags"])
        finally:
            add_location.get_tag_catalog = old_add_catalog
            map_api.get_tag_catalog = old_map_catalog

    def test_preview_success(self):
        payload = AddLocationPreviewRequest(**self._valid_payload())
        request = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(1)})
        preview = add_location.build_preview(payload, request=request)
        self.assertTrue(preview.valid)
        self.assertEqual(preview.normalized.name, "Парк у реки")

    def test_preview_requires_photo(self):
        payload = self._valid_payload()
        payload["photos"] = []
        with self.assertRaises(ValidationError):
            AddLocationPreviewRequest(**payload)

    def test_preview_tag_limit(self):
        payload = self._valid_payload()
        payload["tag_ids"] = ["a", "b", "c", "d", "e", "f"]
        with self.assertRaises(ValidationError):
            AddLocationPreviewRequest(**payload)

    def test_preview_coordinates_validation(self):
        payload = self._valid_payload()
        payload["coordinates"]["latitude"] = 100
        with self.assertRaises(ValidationError):
            AddLocationPreviewRequest(**payload)

    def test_submit_success_response_shape(self):
        payload = AddLocationSubmitRequest(**{**self._valid_payload(), "idempotency_key": "test-key-12345"})
        old_submit = add_location.submit_location
        add_location.submit_location = lambda **kwargs: SimpleNamespace(location_id=77, status="pending", duplicate=False)
        try:
            request = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(1)})
            response = add_location.submit(payload, request=request, x_telegram_init_data="signed-init-data")
            self.assertTrue(response.accepted)
            self.assertEqual(response.location_id, 77)
            self.assertEqual(response.status, "pending")
            self.assertFalse(response.duplicate)
        finally:
            add_location.submit_location = old_submit

    def test_submit_without_auth_is_forbidden(self):
        payload = AddLocationSubmitRequest(**{**self._valid_payload(), "idempotency_key": "test-key-12345"})
        with self.assertRaises(HTTPException):
            add_location.submit(payload, request=SimpleNamespace(cookies={}), x_telegram_init_data="")

    def test_preview_without_auth_is_forbidden(self):
        payload = AddLocationPreviewRequest(**self._valid_payload())
        with self.assertRaises(HTTPException):
            add_location.build_preview(payload, request=SimpleNamespace(cookies={}))

    def test_upload_without_auth_is_forbidden(self):
        payload = PhotoUploadRequest(files=[{"filename": "a.jpg", "mime_type": "image/jpeg", "content_base64": "YQ=="}])
        with self.assertRaises(HTTPException):
            add_location.upload_photos(payload, request=SimpleNamespace(cookies={}))

    def test_upload_endpoint_uses_service_layer(self):
        old_upload = add_location.save_temp_uploads
        add_location.save_temp_uploads = lambda files: [PhotoMeta(temp_id="tmp-1", filename="a.jpg", mime_type="image/jpeg", size_bytes=1)]
        try:
            payload = PhotoUploadRequest(files=[{"filename": "a.jpg", "mime_type": "image/jpeg", "content_base64": "YQ=="}])
            request = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(1)})
            response = add_location.upload_photos(payload, request=request)
            self.assertEqual(len(response), 1)
            self.assertEqual(response[0].temp_id, "tmp-1")
        finally:
            add_location.save_temp_uploads = old_upload

    def test_existing_reader_routes_still_registered(self):
        paths = {route.path for route in main.app.routes}
        for required in ["/", "/leaderboard", "/faq", "/profile/{user_id}"]:
            self.assertIn(required, paths)

    def test_readme_runtime_routes_match_current_main_runtime(self):
        readme = Path("/workspace/test/README.md").read_text()
        runtime_section = readme.split("## Runtime: какие VIEW использует сайт", 1)[1].split("##", 1)[0]
        self.assertIn("/leaderboard", runtime_section)
        self.assertIn("/profile/{user_id}", runtime_section)
        self.assertIn("/achievements", runtime_section)
        self.assertIn("/add-location", runtime_section)
        self.assertNotIn("/auth/telegram", runtime_section)
        self.assertNotIn("/auth/email/login", runtime_section)

    def test_preview_template_is_human_readable_not_raw_json_dump(self):
        page = Path("/workspace/test/frontend/add-location.html").read_text()
        self.assertIn("<strong>Название:</strong>", page)
        self.assertIn("<strong>Описание:</strong>", page)
        self.assertIn("<strong>Координаты:</strong>", page)
        self.assertIn("<strong>Теги:</strong>", page)
        self.assertIn("<strong>Фото:</strong>", page)
        self.assertNotIn("JSON.stringify(data.normalized", page)


if __name__ == "__main__":
    unittest.main()
