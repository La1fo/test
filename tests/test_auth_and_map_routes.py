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

    def test_username_login_success_sets_cookie(self):
        old_login = main.login_username
        main.login_username = lambda username, password: {"user_id": 42}
        try:
            req = SimpleNamespace()
            response = asyncio.run(main.login_username_page(req, username='friendly_user', password='x', next='/add-location'))
            self.assertEqual(response.status_code, 303)
            self.assertIn('set-cookie', response.headers)
        finally:
            main.login_username = old_login

    def test_username_login_failure_bubbles(self):
        old_login = main.login_username
        main.login_username = lambda username, password: (_ for _ in ()).throw(HTTPException(status_code=400, detail='bad'))
        try:
            with self.assertRaises(HTTPException):
                asyncio.run(main.login_username_page(SimpleNamespace(), username='a', password='b', next='/'))
        finally:
            main.login_username = old_login

    def test_register_success_sets_cookie(self):
        old_register = main.register_username_account
        old_ro = main.DB_READ_ONLY
        main.register_username_account = lambda username, password: 123
        main.DB_READ_ONLY = False
        try:
            response = asyncio.run(
                main.register_username_page(
                    SimpleNamespace(),
                    username="user1",
                    password="secret123",
                    confirm_password="secret123",
                    next="/profile/me",
                )
            )
            self.assertEqual(response.status_code, 303)
            self.assertIn("set-cookie", response.headers)
        finally:
            main.register_username_account = old_register
            main.DB_READ_ONLY = old_ro

    def test_register_password_mismatch(self):
        with self.assertRaises(HTTPException):
            asyncio.run(
                main.register_username_page(
                    SimpleNamespace(),
                    username="user1",
                    password="a",
                    confirm_password="b",
                    next="/profile/me",
                )
            )

    def test_register_invalid_username_bubbles(self):
        old_register = main.register_username_account
        old_ro = main.DB_READ_ONLY
        main.DB_READ_ONLY = False
        main.register_username_account = lambda **kwargs: (_ for _ in ()).throw(HTTPException(status_code=400, detail="Username invalid"))
        try:
            with self.assertRaises(HTTPException):
                asyncio.run(
                    main.register_username_page(
                        SimpleNamespace(),
                        username="user1",
                        password="secret123",
                        confirm_password="secret123",
                        next="/profile/me",
                    )
                )
        finally:
            main.register_username_account = old_register
            main.DB_READ_ONLY = old_ro

    def test_register_blocked_in_read_only_mode(self):
        old_ro = main.DB_READ_ONLY
        main.DB_READ_ONLY = True
        try:
            with self.assertRaises(HTTPException):
                asyncio.run(
                    main.register_username_page(
                        SimpleNamespace(),
                        username="user1",
                        password="secret123",
                        confirm_password="secret123",
                        next="/profile/me",
                    )
                )
        finally:
            main.DB_READ_ONLY = old_ro



    def test_admin_routes_registered(self):
        paths = {route.path for route in main.app.routes}
        self.assertIn("/moderation", paths)
        self.assertIn("/admin/users", paths)
        self.assertIn("/api/admin/pending-locations", paths)
        self.assertIn("/api/admin/locations/{location_id}/approve", paths)
        self.assertIn("/api/admin/users/{user_id}/grant", paths)

    def test_moderation_page_requires_admin_and_renders(self):
        old_require = main._require_admin
        old_loader = main._load_pending_locations
        main._require_admin = lambda request: 1
        main._load_pending_locations = lambda: ([], None)
        try:
            response = asyncio.run(main.moderation_page(SimpleNamespace(cookies={})))
            self.assertEqual(response.template.name, "moderation.html")
        finally:
            main._require_admin = old_require
            main._load_pending_locations = old_loader

    def test_admin_users_page_requires_admin_and_renders(self):
        old_require = main._require_admin
        old_loader = main._load_admin_users
        main._require_admin = lambda request: 1
        main._load_admin_users = lambda: ([], None)
        try:
            response = asyncio.run(main.admin_users_page(SimpleNamespace(cookies={})))
            self.assertEqual(response.template.name, "admin-users.html")
        finally:
            main._require_admin = old_require
            main._load_admin_users = old_loader

    def test_approve_and_grant_admin_endpoints_call_services(self):
        calls = []
        old_require = main._require_admin
        old_status = main._set_location_moderation_status
        old_grant = main._grant_admin
        main._require_admin = lambda request: 1
        main._set_location_moderation_status = lambda location_id, status: calls.append(("status", location_id, status))
        main._grant_admin = lambda user_id: calls.append(("grant", user_id))
        try:
            approve = asyncio.run(main.approve_location(55, SimpleNamespace(cookies={})))
            grant = asyncio.run(main.grant_admin(77, SimpleNamespace(cookies={})))
            self.assertEqual(approve.status_code, 200)
            self.assertEqual(grant.status_code, 200)
            self.assertIn(("status", 55, "approved"), calls)
            self.assertIn(("grant", 77), calls)
        finally:
            main._require_admin = old_require
            main._set_location_moderation_status = old_status
            main._grant_admin = old_grant

    def test_standalone_site_has_no_telegram_session_route(self):
        paths = {route.path for route in main.app.routes}
        self.assertNotIn("/api/session/telegram", paths)

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
                return [(1, 'A', 'D', 1.0, 2.0, 'legacy-id', 'legacy', None, 'tag1, tag2')]
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

    def test_map_tags_endpoint_fallbacks_when_db_catalog_empty(self):
        old_catalog = map_api.get_tag_catalog
        map_api.get_tag_catalog = lambda: []
        try:
            payload = map_api.map_tags()
            self.assertEqual(len(payload["tags"]), len(contract.TAG_CATALOG))
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
