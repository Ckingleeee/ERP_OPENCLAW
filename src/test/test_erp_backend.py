"""Contract tests for the Python ERP API without touching MySQL."""

from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from erp_backend.main import app
from erp_backend.schemas import ReplenishmentUpdate
from erp_backend.serialization import json_value


client = TestClient(app, raise_server_exceptions=False)


class ErpApiContractTests(unittest.TestCase):
    @patch("erp_backend.main.repository.search_providers")
    def test_provider_search_uses_standard_response(self, search_providers):
        search_providers.return_value = [
            {
                "id": 1,
                "provider_code": "BP0001",
                "name": "星享数字权益",
                "create_time": datetime(2026, 1, 2, 3, 4, 5),
            }
        ]

        response = client.get("/api/providers/search", params={"name": "星享"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"][0]["providerCode"], "BP0001")
        self.assertEqual(body["data"][0]["createTime"], "2026-01-02T03:04:05")
        search_providers.assert_called_once_with("星享")

    @patch("erp_backend.main.repository.list_resources")
    def test_resource_page_accepts_camel_case_provider_id(self, list_resources):
        list_resources.return_value = {"records": [], "total": 0, "current": 2, "size": 20}

        response = client.get(
            "/api/resources/page",
            params={"current": 2, "size": 20, "providerId": 9},
        )

        self.assertEqual(response.status_code, 200)
        list_resources.assert_called_once_with(
            current=2, size=20, name=None, category=None, provider_id=9
        )

    def test_create_replenishment_requires_details(self):
        response = client.post("/api/replenishments/create", json={"status": 1})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], 422)

    @patch("erp_backend.main.repository.create_replenishment")
    def test_create_replenishment_contract(self, create_replenishment):
        create_replenishment.return_value = {
            "id": 201,
            "replenishment_number": "BR20260828001",
            "total_amount": Decimal("20.00"),
            "detail": [],
        }
        response = client.post(
            "/api/replenishments/create",
            json={
                "replenishmentNumber": "BR20260828001",
                "detail": [
                    {"resourceId": 1, "quantity": 2, "unitCost": 10.00}
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["totalAmount"], 20.0)
        create_replenishment.assert_called_once()

    def test_update_requires_at_least_one_field(self):
        response = client.put("/api/replenishments/update/1", json={})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_reversed_date_range(self):
        response = client.get(
            "/api/replenishments/search-details",
            params={"startDate": "2026-08-28", "endDate": "2026-01-01"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("startDate", response.json()["message"])

    def test_update_schema_keeps_omitted_identity_untouched(self):
        payload = ReplenishmentUpdate(status=2)
        self.assertEqual(payload.model_fields_set, {"status"})
        self.assertIsNone(payload.replenishment_number)
        self.assertIsNone(payload.replenishment_time)

    def test_serialization_converts_nested_snake_case(self):
        value = json_value(
            {"resource_detail": {"unit_cost": Decimal("12.50")}}
        )
        self.assertEqual(value, {"resourceDetail": {"unitCost": 12.5}})


if __name__ == "__main__":
    unittest.main()
