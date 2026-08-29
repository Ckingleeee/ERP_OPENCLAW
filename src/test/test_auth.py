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
            "role": "purchase",
            "department": "采购部",
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
        response = client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
