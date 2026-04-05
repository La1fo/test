import asyncio
import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from backend import main
from backend import add_location_contract as contract
from backend.api import map as map_api
from backend.session_auth import SESSION_COOKIE_NAME, create_session_cookie


class TestAuthAndMapRoutes(unittest.TestCase):
    def test_profile_me_requires_login(self):
        with self.assertRaises(HTTPException):
            asyncio.run(main.my_profile_page(SimpleNamespace(cookies={})))

    def test_profile_me_uses_profile_loader(self):
        old_loader = main._load_profile
        main._load_profile = lambda user_id: (SimpleNamespace(username='u', rank_name='r', gp_display='1', approved_locations=1), None)
        try:
            req = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(77)})
            response = asyncio.run(main.my_profile_page(req))
            self.assertEqual(response.template.name, 'profile.html')
        finally:
            main._load_profile = old_loader

    def test_email_login_success_sets_cookie(self):
        old_login = main.login_email
        main.login_email = lambda email, password: {"user_id": 42}
        try:
            req = SimpleNamespace()
            response = asyncio.run(main.login_email_page(req, email='a@b.c', password='x', next='/add-location'))
            self.assertEqual(response.status_code, 303)
            self.assertIn('set-cookie', response.headers)
        finally:
            main.login_email = old_login

    def test_email_login_failure_bubbles(self):
        old_login = main.login_email
        main.login_email = lambda email, password: (_ for _ in ()).throw(HTTPException(status_code=400, detail='bad'))
        try:
            with self.assertRaises(HTTPException):
                asyncio.run(main.login_email_page(SimpleNamespace(), email='a', password='b', next='/'))
        finally:
            main.login_email = old_login

    def test_telegram_login_success(self):
        old_validate = main.validate_telegram_init_data
        main.validate_telegram_init_data = lambda init_data: SimpleNamespace(telegram_id=99)
        try:
            response = asyncio.run(main.login_telegram_page(SimpleNamespace(), init_data='ok', next='/'))
            self.assertEqual(response.status_code, 303)
            self.assertIn('set-cookie', response.headers)
        finally:
            main.validate_telegram_init_data = old_validate

    def test_telegram_login_failure(self):
        old_validate = main.validate_telegram_init_data
        main.validate_telegram_init_data = lambda init_data: (_ for _ in ()).throw(HTTPException(status_code=403, detail='bad'))
        try:
            with self.assertRaises(HTTPException):
                asyncio.run(main.login_telegram_page(SimpleNamespace(), init_data='bad', next='/'))
        finally:
            main.validate_telegram_init_data = old_validate

    def test_map_route_renders(self):
        req = SimpleNamespace(cookies={})
        response = asyncio.run(main.map_page(req))
        self.assertEqual(response.template.name, 'map.html')

    def test_session_me_for_anonymous(self):
        req = SimpleNamespace(cookies={})
        response = asyncio.run(main.session_me(req))
        self.assertEqual(response.status_code, 200)
        self.assertIn('"authenticated":false', response.body.decode().lower())

    def test_session_me_for_authorized(self):
        req = SimpleNamespace(cookies={SESSION_COOKIE_NAME: create_session_cookie(88)})
        response = asyncio.run(main.session_me(req))
        self.assertEqual(response.status_code, 200)
        self.assertIn('"user_id":88', response.body.decode().replace(" ", ""))

    def test_map_api_returns_payload(self):
        old_conn = map_api.get_connection

        class C:
            def execute(self, q, params=None):
                _ = q
                self.params = params
            def fetchall(self):
                return [(1, 'A', 'D', 1.0, 2.0, 'legacy-id', 'telegram', None, 'tag1, tag2')]
            def __enter__(self): return self
            def __exit__(self, a,b,c): return False
        class Conn:
            def cursor(self): return C()
            def __enter__(self): return self
            def __exit__(self,a,b,c): return False

        map_api.get_connection = lambda: Conn()
        try:
            result = map_api.approved_locations()
            self.assertEqual(result[0]['id'], 1)
            self.assertIn('tag1', result[0]['tags'])
        finally:
            map_api.get_connection = old_conn

    def test_map_tags_endpoint_uses_db_catalog(self):
        old_catalog = map_api.get_tag_catalog
        map_api.get_tag_catalog = lambda: [{"id": "ramp", "label": "Пандус", "category": "Доступность"}]
        try:
            payload = map_api.map_tags()
            self.assertEqual(payload["tags"][0]["id"], "ramp")
        finally:
            map_api.get_tag_catalog = old_catalog

    def test_map_tags_endpoint_fallbacks_to_full_contract_catalog(self):
        old_catalog = map_api.get_tag_catalog
        map_api.get_tag_catalog = lambda: (_ for _ in ()).throw(RuntimeError("db down"))
        try:
            payload = map_api.map_tags()
            self.assertEqual(len(payload["tags"]), len(contract.TAG_CATALOG))
            self.assertEqual(payload["tags"][0]["category"], contract.TAG_CATALOG[0]["category"])
        finally:
            map_api.get_tag_catalog = old_catalog

    def test_map_api_accepts_search_and_tag_filters(self):
        old_conn = map_api.get_connection

        class C:
            def execute(self, q, params=None):
                self.query = q
                self.params = params
            def fetchall(self):
                return []
            def __enter__(self): return self
            def __exit__(self, a,b,c): return False
        class Conn:
            def __init__(self): self.cursor_obj = C()
            def cursor(self): return self.cursor_obj
            def __enter__(self): return self
            def __exit__(self,a,b,c): return False

        holder = Conn()
        map_api.get_connection = lambda: holder
        try:
            map_api.approved_locations(q='park', tag='кафе')
            self.assertIn('lower(l.name)', holder.cursor_obj.query.lower())
            self.assertEqual(holder.cursor_obj.params[-1], 'кафе')
        finally:
            map_api.get_connection = old_conn


if __name__ == '__main__':
    unittest.main()
