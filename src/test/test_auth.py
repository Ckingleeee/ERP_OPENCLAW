"""Contract tests for ERP login and signed session cookies."""

import unittest
from unittest.mock import patch

import bcrypt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_view import auth as auth_service
from api_view.api.auth import router


app = FastAPI()
app.include_router(router, prefix="/api")
client = TestClient(app, raise_server_exceptions=False)


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "correct-password"
        cls.user_row = {
            "id": 101,
            "username": "yyf",
            "password": bcrypt.hashpw(
                cls.password.encode("utf-8"), bcrypt.gensalt(rounds=4)
            ).decode("utf-8"),
            "real_name": "yyf",
            "role": "operations",
            "department": "信用卡运营部",
        }

    def setUp(self):
        client.cookies.clear()

    def test_login_rejects_invalid_password(self):
        with patch.object(auth_service, "find_active_user", return_value=self.user_row):
            response = client.post(
                "/api/auth/login",
                json={"username": "yyf", "password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("erp_session", response.cookies)

    def test_login_sets_httponly_cookie_and_me_returns_user(self):
        with (
            patch.object(auth_service, "AUTH_JWT_SECRET", "s" * 64),
            patch.object(auth_service, "find_active_user", return_value=self.user_row),
        ):
            login_response = client.post(
                "/api/auth/login",
                json={"username": "yyf", "password": self.password},
            )
            me_response = client.get("/api/auth/me")

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("HttpOnly", login_response.headers["set-cookie"])
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["user"]["user_id"], "yyf")
        self.assertEqual(me_response.json()["user"]["display_name"], "yyf")

    def test_me_requires_session(self):
        with patch.object(auth_service, "AUTH_DEMO_MODE", False):
            response = client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_demo_mode_creates_and_reuses_anonymous_browser_identity(self):
        with (
            patch.object(auth_service, "AUTH_JWT_SECRET", "s" * 64),
            patch.object(auth_service, "AUTH_DEMO_MODE", True),
        ):
            first_response = client.get("/api/auth/me")
            second_response = client.get("/api/auth/me")

        self.assertEqual(first_response.status_code, 200)
        self.assertIn("HttpOnly", first_response.headers["set-cookie"])
        first_user = first_response.json()["user"]
        second_user = second_response.json()["user"]
        self.assertTrue(first_user["is_demo"])
        self.assertTrue(first_user["user_id"].startswith("demo-"))
        self.assertEqual(first_user["user_id"], second_user["user_id"])

    def test_demo_mode_isolates_different_browsers(self):
        with (
            patch.object(auth_service, "AUTH_JWT_SECRET", "s" * 64),
            patch.object(auth_service, "AUTH_DEMO_MODE", True),
        ):
            first_response = client.get("/api/auth/me")
            client.cookies.clear()
            second_response = client.get("/api/auth/me")

        self.assertNotEqual(
            first_response.json()["user"]["user_id"],
            second_response.json()["user"]["user_id"],
        )

    def test_demo_mode_replaces_an_existing_named_user_session(self):
        with (
            patch.object(auth_service, "AUTH_JWT_SECRET", "s" * 64),
            patch.object(auth_service, "AUTH_DEMO_MODE", False),
            patch.object(auth_service, "find_active_user", return_value=self.user_row),
        ):
            login_response = client.post(
                "/api/auth/login",
                json={"username": "yyf", "password": self.password},
            )

        self.assertEqual(login_response.status_code, 200)

        with (
            patch.object(auth_service, "AUTH_JWT_SECRET", "s" * 64),
            patch.object(auth_service, "AUTH_DEMO_MODE", True),
            patch.object(auth_service, "find_active_user", return_value=self.user_row),
        ):
            me_response = client.get("/api/auth/me")

        user = me_response.json()["user"]
        self.assertTrue(user["is_demo"])
        self.assertNotEqual(user["user_id"], "yyf")


if __name__ == "__main__":
    unittest.main()
