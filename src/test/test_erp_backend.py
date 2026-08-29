"""Contract tests for the Python ERP API without touching MySQL."""

from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from erp_backend.main import app
from erp_backend.schemas import OrderUpdate
from erp_backend.serialization import json_value


client = TestClient(app, raise_server_exceptions=False)


class ErpApiContractTests(unittest.TestCase):
    @patch("erp_backend.main.repository.search_suppliers")
    def test_supplier_search_uses_standard_response(self, search_suppliers):
        search_suppliers.return_value = [
            {
                "id": 1,
                "supplier_code": "SUP00001",
                "name": "博世汽车配件",
                "create_time": datetime(2026, 1, 2, 3, 4, 5),
            }
        ]

        response = client.get("/api/suppliers/search", params={"name": "博世"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"][0]["supplierCode"], "SUP00001")
        self.assertEqual(body["data"][0]["createTime"], "2026-01-02T03:04:05")
        search_suppliers.assert_called_once_with("博世")

    @patch("erp_backend.main.repository.list_parts")
    def test_part_page_accepts_java_style_supplier_id(self, list_parts):
        list_parts.return_value = {"records": [], "total": 0, "current": 2, "size": 20}

        response = client.get(
            "/api/parts/page",
            params={"current": 2, "size": 20, "supplierId": 9},
        )

        self.assertEqual(response.status_code, 200)
        list_parts.assert_called_once_with(
            current=2, size=20, name=None, category=None, supplier_id=9
        )

    def test_create_order_requires_details(self):
        response = client.post("/api/orders/create", json={"status": 1})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], 422)

    @patch("erp_backend.main.repository.create_order")
    def test_create_order_contract(self, create_order):
        create_order.return_value = {
            "id": 201,
            "order_number": "PO2026082800001",
            "total_amount": Decimal("20.00"),
            "order_detail": [],
        }
        response = client.post(
            "/api/orders/create",
            json={
                "orderNumber": "PO2026082800001",
                "orderDetail": [
                    {"partId": 1, "quantity": 2, "unitPrice": 10.00}
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["totalAmount"], 20.0)
        create_order.assert_called_once()

    def test_update_requires_at_least_one_field(self):
        response = client.put("/api/orders/update/1", json={})
        self.assertEqual(response.status_code, 422)

    def test_search_rejects_reversed_date_range(self):
        response = client.get(
            "/api/orders/search-details",
            params={"startDate": "2026-08-28", "endDate": "2026-01-01"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("startDate", response.json()["message"])

    def test_update_schema_keeps_omitted_order_identity_untouched(self):
        payload = OrderUpdate(status=2)
        self.assertEqual(payload.model_fields_set, {"status"})
        self.assertIsNone(payload.order_number)
        self.assertIsNone(payload.order_time)

    def test_serialization_converts_nested_snake_case(self):
        value = json_value(
            {"part_detail": {"purchase_price": Decimal("12.50")}}
        )
        self.assertEqual(value, {"partDetail": {"purchasePrice": 12.5}})


if __name__ == "__main__":
    unittest.main()

