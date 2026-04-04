import asyncio
import unittest

from fastapi import HTTPException
from pydantic import ValidationError

from backend import main
from backend.api import add_location
from backend.schemas import AddLocationPreviewRequest, AddLocationSubmitRequest


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
        self.assertIn("/api/add-location/submit", paths)

    def test_add_location_page_renders_template(self):
        response = asyncio.run(main.add_location_page(request=None))
        self.assertEqual(response.template.name, "add-location.html")

    def test_form_config_contract(self):
        config = add_location.get_add_location_form_config()
        self.assertFalse(config.writer_integration_enabled)
        self.assertEqual(config.max_tags, 5)
        self.assertEqual(config.max_photos, 8)
        self.assertGreater(len(config.tag_catalog), 0)

    def test_preview_success(self):
        payload = AddLocationPreviewRequest(**self._valid_payload())
        preview = add_location.build_preview(payload)
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

    def test_submit_stub_honest_response(self):
        payload = AddLocationSubmitRequest(**{**self._valid_payload(), "idempotency_key": "test-key-12345"})
        with self.assertRaises(HTTPException) as exc:
            add_location.submit_stub(payload)
        self.assertEqual(exc.exception.status_code, 501)
        self.assertIn("Writer-side integration not connected", exc.exception.detail)

    def test_existing_reader_routes_still_registered(self):
        paths = {route.path for route in main.app.routes}
        for required in ["/", "/leaderboard", "/faq", "/profile/{user_id}"]:
            self.assertIn(required, paths)


if __name__ == "__main__":
    unittest.main()
