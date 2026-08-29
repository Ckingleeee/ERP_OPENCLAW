"""SQL operations for the ERP API."""

from datetime import date
from decimal import Decimal
import secrets
from typing import Any

from erp_backend import database
from erp_backend.schemas import OrderCreate, OrderDetailInput, OrderUpdate


PART_COLUMNS = """
    p.id, p.part_code, p.name, p.model, p.specification, p.unit,
    p.purchase_price, p.suggested_retail_price, p.stock_warning_value,
    p.supplier_id, p.category, p.description, p.create_time, p.update_time
"""

SUPPLIER_COLUMNS = """
    s.id, s.supplier_code, s.name, s.contact_person, s.phone, s.email,
    s.address, s.credit_rating, s.status, s.create_time, s.update_time
"""

ORDER_COLUMNS = """
    id, order_number, total_amount, status, order_time,
    expected_delivery_date, actual_delivery_date, created_by, remark,
    create_time, update_time
"""


def search_suppliers(name: str) -> list[dict]:
    return database.fetch_all(
        f"SELECT {SUPPLIER_COLUMNS} FROM supplier s "
        "WHERE s.deleted = 0 AND s.name LIKE %s ORDER BY s.id LIMIT 100",
        (f"%{name}%",),
    )


def _attach_suppliers(rows: list[dict]) -> list[dict]:
    for row in rows:
        supplier_id = row.get("supplier_id")
        supplier = None
        if supplier_id is not None:
            supplier = {
                "id": supplier_id,
                "supplier_code": row.pop("supplier_code", None),
                "name": row.pop("supplier_name", None),
                "credit_rating": row.pop("supplier_credit_rating", None),
                "status": row.pop("supplier_status", None),
            }
        else:
            row.pop("supplier_code", None)
            row.pop("supplier_name", None)
            row.pop("supplier_credit_rating", None)
            row.pop("supplier_status", None)
        row["supplier"] = supplier
    return rows


def list_parts(
    *,
    current: int,
    size: int,
    name: str | None,
    category: str | None,
    supplier_id: int | None,
) -> dict:
    filters = ["p.deleted = 0"]
    params: list[Any] = []
    if name:
        filters.append("p.name LIKE %s")
        params.append(f"%{name}%")
    if category:
        filters.append("p.category = %s")
        params.append(category)
    if supplier_id is not None:
        filters.append("p.supplier_id = %s")
        params.append(supplier_id)

    where = " AND ".join(filters)
    total_row = database.fetch_one(
        f"SELECT COUNT(*) AS total FROM part p WHERE {where}", tuple(params)
    )
    offset = (current - 1) * size
    rows = database.fetch_all(
        f"""
        SELECT {PART_COLUMNS},
               s.supplier_code, s.name AS supplier_name,
               s.credit_rating AS supplier_credit_rating,
               s.status AS supplier_status
        FROM part p
        LEFT JOIN supplier s ON s.id = p.supplier_id AND s.deleted = 0
        WHERE {where}
        ORDER BY p.id
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return {
        "records": _attach_suppliers(rows),
        "total": int((total_row or {}).get("total", 0)),
        "current": current,
        "size": size,
    }


def search_parts(name: str) -> list[dict]:
    result = list_parts(current=1, size=100, name=name, category=None, supplier_id=None)
    return result["records"]


def list_parts_by_supplier(supplier_id: int) -> list[dict]:
    result = list_parts(
        current=1,
        size=500,
        name=None,
        category=None,
        supplier_id=supplier_id,
    )
    return result["records"]


def inventory_warnings() -> list[dict]:
    rows = database.fetch_all(
        f"""
        SELECT i.id AS inventory_id, i.part_id, i.current_quantity, i.safety_stock,
               i.last_inbound_time, i.last_outbound_time, i.warehouse_location,
               {PART_COLUMNS},
               s.supplier_code, s.name AS supplier_name,
               s.credit_rating AS supplier_credit_rating,
               s.status AS supplier_status
        FROM inventory i
        JOIN part p ON p.id = i.part_id AND p.deleted = 0
        LEFT JOIN supplier s ON s.id = p.supplier_id AND s.deleted = 0
        WHERE i.deleted = 0 AND i.current_quantity < i.safety_stock
        ORDER BY (i.safety_stock - i.current_quantity) DESC, i.id
        """
    )
    result = []
    part_keys = {
        "part_code", "name", "model", "specification", "unit", "purchase_price",
        "suggested_retail_price", "stock_warning_value", "supplier_id", "category",
        "description", "create_time", "update_time",
    }
    for row in rows:
        inventory = {
            key: row[key]
            for key in (
                "inventory_id", "part_id", "current_quantity", "safety_stock",
                "last_inbound_time", "last_outbound_time", "warehouse_location",
            )
        }
        inventory["id"] = inventory.pop("inventory_id")
        part = {"id": row["part_id"]}
        for key in part_keys:
            part[key] = row.get(key)
        supplier_id = row.get("supplier_id")
        part["supplier"] = None if supplier_id is None else {
            "id": supplier_id,
            "supplier_code": row.get("supplier_code"),
            "name": row.get("supplier_name"),
            "credit_rating": row.get("supplier_credit_rating"),
            "status": row.get("supplier_status"),
        }
        inventory["part_detail"] = part
        result.append(inventory)
    return result


def _generate_order_number() -> str:
    from datetime import datetime

    return f"PO{datetime.now():%Y%m%d}{secrets.randbelow(100000):05d}"


def _validate_parts(connection, details: list[OrderDetailInput]) -> None:
    part_ids = sorted({detail.part_id for detail in details})
    placeholders = ", ".join(["%s"] * len(part_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id FROM part WHERE deleted = 0 AND id IN ({placeholders})",
            tuple(part_ids),
        )
        found = {row["id"] for row in cursor.fetchall()}
    missing = sorted(set(part_ids) - found)
    if missing:
        raise ValueError(f"Unknown or deleted part IDs: {missing}")


def _detail_total(details: list[OrderDetailInput]) -> Decimal:
    return sum(
        (Decimal(detail.quantity) * detail.unit_price for detail in details),
        Decimal("0.00"),
    )


def _insert_details(connection, order_id: int, details: list[OrderDetailInput]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO order_detail (order_id, part_id, quantity, unit_price, remark)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (order_id, item.part_id, item.quantity, item.unit_price, item.remark)
                for item in details
            ],
        )


def create_order(payload: OrderCreate) -> dict:
    order_number = payload.order_number or _generate_order_number()
    total_amount = payload.total_amount
    calculated_total = _detail_total(payload.order_detail)
    if total_amount is None:
        total_amount = calculated_total

    with database.transaction() as connection:
        _validate_parts(connection, payload.order_detail)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO purchase_order (
                    order_number, total_amount, status, order_time,
                    expected_delivery_date, actual_delivery_date, created_by, remark
                ) VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), %s, %s, %s, %s)
                """,
                (
                    order_number, total_amount, payload.status, payload.order_time,
                    payload.expected_delivery_date, payload.actual_delivery_date,
                    payload.created_by, payload.remark,
                ),
            )
            order_id = cursor.lastrowid
        _insert_details(connection, order_id, payload.order_detail)
    return get_order(order_id)


def update_order(order_id: int, payload: OrderUpdate) -> dict | None:
    existing = database.fetch_one(
        "SELECT id FROM purchase_order WHERE id = %s AND deleted = 0", (order_id,)
    )
    if existing is None:
        return None

    fields = {
        "order_number": payload.order_number,
        "total_amount": payload.total_amount,
        "status": payload.status,
        "order_time": payload.order_time,
        "expected_delivery_date": payload.expected_delivery_date,
        "actual_delivery_date": payload.actual_delivery_date,
        "created_by": payload.created_by,
        "remark": payload.remark,
    }
    supplied = set(payload.model_fields_set)

    with database.transaction() as connection:
        if payload.order_detail is not None:
            _validate_parts(connection, payload.order_detail)
            if "total_amount" not in supplied:
                fields["total_amount"] = _detail_total(payload.order_detail)
                supplied.add("total_amount")

        assignments = []
        values = []
        for field_name, value in fields.items():
            if field_name in supplied:
                assignments.append(f"{field_name} = %s")
                values.append(value)
        if assignments:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE purchase_order SET {', '.join(assignments)} "
                    "WHERE id = %s AND deleted = 0",
                    tuple(values + [order_id]),
                )

        if payload.order_detail is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE order_detail SET deleted = 1 WHERE order_id = %s AND deleted = 0",
                    (order_id,),
                )
            _insert_details(connection, order_id, payload.order_detail)
    return get_order(order_id)


def get_order(order_id: int) -> dict | None:
    order = database.fetch_one(
        f"SELECT {ORDER_COLUMNS} FROM purchase_order "
        "WHERE id = %s AND deleted = 0",
        (order_id,),
    )
    if order is None:
        return None
    order["order_detail"] = database.fetch_all(
        """
        SELECT id, order_id, part_id, quantity, unit_price, subtotal, remark,
               create_time, update_time
        FROM order_detail
        WHERE order_id = %s AND deleted = 0
        ORDER BY id
        """,
        (order_id,),
    )
    return order


def search_order_details(
    *, part_name: str | None, start_date: date | None, end_date: date | None
) -> list[dict]:
    filters = ["od.deleted = 0", "po.deleted = 0", "p.deleted = 0"]
    params: list[Any] = []
    if part_name:
        filters.append("p.name LIKE %s")
        params.append(f"%{part_name}%")
    if start_date:
        filters.append("DATE(po.order_time) >= %s")
        params.append(start_date)
    if end_date:
        filters.append("DATE(po.order_time) <= %s")
        params.append(end_date)

    rows = database.fetch_all(
        f"""
        SELECT od.id, od.order_id, od.part_id, od.quantity, od.unit_price,
               od.subtotal, od.remark, od.create_time, od.update_time,
               po.order_number, po.order_time, po.status AS order_status,
               p.part_code, p.name AS part_name, p.model AS part_model,
               p.specification AS part_specification, p.unit AS part_unit,
               p.purchase_price, p.category, p.supplier_id,
               s.supplier_code, s.name AS supplier_name,
               s.credit_rating AS supplier_credit_rating, s.status AS supplier_status
        FROM order_detail od
        JOIN purchase_order po ON po.id = od.order_id
        JOIN part p ON p.id = od.part_id
        LEFT JOIN supplier s ON s.id = p.supplier_id AND s.deleted = 0
        WHERE {' AND '.join(filters)}
        ORDER BY po.order_time DESC, od.id DESC
        LIMIT 1000
        """,
        tuple(params),
    )

    result = []
    for row in rows:
        detail = {
            key: row[key]
            for key in (
                "id", "order_id", "part_id", "quantity", "unit_price", "subtotal",
                "remark", "create_time", "update_time", "order_number", "order_time",
                "order_status",
            )
        }
        detail["part_detail"] = {
            "id": row["part_id"],
            "part_code": row["part_code"],
            "name": row["part_name"],
            "model": row["part_model"],
            "specification": row["part_specification"],
            "unit": row["part_unit"],
            "purchase_price": row["purchase_price"],
            "category": row["category"],
            "supplier_id": row["supplier_id"],
        }
        supplier_id = row["supplier_id"]
        detail["supplier"] = None if supplier_id is None else {
            "id": supplier_id,
            "supplier_code": row["supplier_code"],
            "name": row["supplier_name"],
            "credit_rating": row["supplier_credit_rating"],
            "status": row["supplier_status"],
        }
        result.append(detail)
    return result
