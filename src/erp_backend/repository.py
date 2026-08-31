"""SQL operations for benefits and marketing-resource management."""

from datetime import date
from decimal import Decimal
import secrets
from typing import Any

from erp_backend import database
from erp_backend.schemas import (
    ReplenishmentCreate,
    ReplenishmentDetailInput,
    ReplenishmentUpdate,
)


RESOURCE_COLUMNS = """
    r.id, r.resource_code, r.name, r.model, r.specification, r.unit,
    r.unit_cost, r.face_value, r.quota_warning_value,
    r.provider_id, r.category, r.description, r.create_time, r.update_time
"""

PROVIDER_COLUMNS = """
    p.id, p.provider_code, p.name, p.contact_person, p.phone, p.email,
    p.address, p.service_rating, p.status, p.create_time, p.update_time
"""

REPLENISHMENT_COLUMNS = """
    id, replenishment_number, total_amount, status, replenishment_time,
    expected_activation_date, actual_activation_date, created_by, remark,
    create_time, update_time
"""


def search_providers(name: str) -> list[dict]:
    return database.fetch_all(
        f"SELECT {PROVIDER_COLUMNS} FROM benefit_provider p "
        "WHERE p.deleted = 0 AND p.name LIKE %s ORDER BY p.id LIMIT 100",
        (f"%{name}%",),
    )


def _attach_providers(rows: list[dict]) -> list[dict]:
    for row in rows:
        provider_id = row.get("provider_id")
        provider = None
        if provider_id is not None:
            provider = {
                "id": provider_id,
                "provider_code": row.pop("provider_code", None),
                "name": row.pop("provider_name", None),
                "service_rating": row.pop("provider_service_rating", None),
                "status": row.pop("provider_status", None),
            }
        else:
            row.pop("provider_code", None)
            row.pop("provider_name", None)
            row.pop("provider_service_rating", None)
            row.pop("provider_status", None)
        row["provider"] = provider
    return rows


def list_resources(
    *,
    current: int,
    size: int,
    name: str | None,
    category: str | None,
    provider_id: int | None,
) -> dict:
    filters = ["r.deleted = 0"]
    params: list[Any] = []
    if name:
        filters.append("r.name LIKE %s")
        params.append(f"%{name}%")
    if category:
        filters.append("r.category = %s")
        params.append(category)
    if provider_id is not None:
        filters.append("r.provider_id = %s")
        params.append(provider_id)

    where = " AND ".join(filters)
    total_row = database.fetch_one(
        f"SELECT COUNT(*) AS total FROM marketing_resource r WHERE {where}",
        tuple(params),
    )
    offset = (current - 1) * size
    rows = database.fetch_all(
        f"""
        SELECT {RESOURCE_COLUMNS},
               p.provider_code, p.name AS provider_name,
               p.service_rating AS provider_service_rating,
               p.status AS provider_status
        FROM marketing_resource r
        LEFT JOIN benefit_provider p ON p.id = r.provider_id AND p.deleted = 0
        WHERE {where}
        ORDER BY p.id
        LIMIT %s OFFSET %s
        """,
        tuple(params + [size, offset]),
    )
    return {
        "records": _attach_providers(rows),
        "total": int((total_row or {}).get("total", 0)),
        "current": current,
        "size": size,
    }


def search_resources(name: str) -> list[dict]:
    result = list_resources(
        current=1, size=100, name=name, category=None, provider_id=None
    )
    return result["records"]


def list_resources_by_provider(provider_id: int) -> list[dict]:
    result = list_resources(
        current=1,
        size=500,
        name=None,
        category=None,
        provider_id=provider_id,
    )
    return result["records"]


def quota_warnings() -> list[dict]:
    rows = database.fetch_all(
        f"""
        SELECT q.id AS quota_id, q.resource_id, q.current_quota, q.safety_quota,
               q.last_replenished_time, q.last_redeemed_time, q.quota_pool,
               {RESOURCE_COLUMNS},
               p.provider_code, p.name AS provider_name,
               p.service_rating AS provider_service_rating,
               p.status AS provider_status
        FROM resource_quota q
        JOIN marketing_resource r ON r.id = q.resource_id AND r.deleted = 0
        LEFT JOIN benefit_provider p ON p.id = r.provider_id AND p.deleted = 0
        WHERE q.deleted = 0 AND q.current_quota < q.safety_quota
        ORDER BY (q.safety_quota - q.current_quota) DESC, q.id
        """
    )
    result = []
    resource_keys = {
        "resource_code", "name", "model", "specification", "unit", "unit_cost",
        "face_value", "quota_warning_value", "provider_id", "category",
        "description", "create_time", "update_time",
    }
    for row in rows:
        quota = {
            key: row[key]
            for key in (
                "quota_id", "resource_id", "current_quota", "safety_quota",
                "last_replenished_time", "last_redeemed_time", "quota_pool",
            )
        }
        quota["id"] = quota.pop("quota_id")
        resource = {"id": row["resource_id"]}
        for key in resource_keys:
            resource[key] = row.get(key)
        provider_id = row.get("provider_id")
        resource["provider"] = None if provider_id is None else {
            "id": provider_id,
            "provider_code": row.get("provider_code"),
            "name": row.get("provider_name"),
            "service_rating": row.get("provider_service_rating"),
            "status": row.get("provider_status"),
        }
        quota["resource_detail"] = resource
        result.append(quota)
    return result


def _generate_replenishment_number() -> str:
    from datetime import datetime

    return f"BR{datetime.now():%Y%m%d}{secrets.randbelow(100000):05d}"


def _validate_resources(
    connection, details: list[ReplenishmentDetailInput]
) -> None:
    resource_ids = sorted({detail.resource_id for detail in details})
    placeholders = ", ".join(["%s"] * len(resource_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id FROM marketing_resource "
            f"WHERE deleted = 0 AND id IN ({placeholders})",
            tuple(resource_ids),
        )
        found = {row["id"] for row in cursor.fetchall()}
    missing = sorted(set(resource_ids) - found)
    if missing:
        raise ValueError(f"Unknown or deleted resource IDs: {missing}")


def _detail_total(details: list[ReplenishmentDetailInput]) -> Decimal:
    return sum(
        (Decimal(detail.quantity) * detail.unit_cost for detail in details),
        Decimal("0.00"),
    )


def _insert_details(
    connection,
    replenishment_id: int,
    details: list[ReplenishmentDetailInput],
) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO replenishment_detail (
                replenishment_id, resource_id, quantity, unit_cost, remark
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (
                    replenishment_id,
                    item.resource_id,
                    item.quantity,
                    item.unit_cost,
                    item.remark,
                )
                for item in details
            ],
        )


def create_replenishment(payload: ReplenishmentCreate) -> dict:
    replenishment_number = (
        payload.replenishment_number or _generate_replenishment_number()
    )
    total_amount = payload.total_amount
    calculated_total = _detail_total(payload.detail)
    if total_amount is None:
        total_amount = calculated_total

    with database.transaction() as connection:
        _validate_resources(connection, payload.detail)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO resource_replenishment (
                    replenishment_number, total_amount, status, replenishment_time,
                    expected_activation_date, actual_activation_date, created_by, remark
                ) VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), %s, %s, %s, %s)
                """,
                (
                    replenishment_number, total_amount, payload.status,
                    payload.replenishment_time, payload.expected_activation_date,
                    payload.actual_activation_date,
                    payload.created_by, payload.remark,
                ),
            )
            replenishment_id = cursor.lastrowid
        _insert_details(connection, replenishment_id, payload.detail)
    return get_replenishment(replenishment_id)


def update_replenishment(
    replenishment_id: int, payload: ReplenishmentUpdate
) -> dict | None:
    existing = database.fetch_one(
        "SELECT id FROM resource_replenishment WHERE id = %s AND deleted = 0",
        (replenishment_id,),
    )
    if existing is None:
        return None

    fields = {
        "replenishment_number": payload.replenishment_number,
        "total_amount": payload.total_amount,
        "status": payload.status,
        "replenishment_time": payload.replenishment_time,
        "expected_activation_date": payload.expected_activation_date,
        "actual_activation_date": payload.actual_activation_date,
        "created_by": payload.created_by,
        "remark": payload.remark,
    }
    supplied = set(payload.model_fields_set)

    with database.transaction() as connection:
        if payload.detail is not None:
            _validate_resources(connection, payload.detail)
            if "total_amount" not in supplied:
                fields["total_amount"] = _detail_total(payload.detail)
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
                    f"UPDATE resource_replenishment SET {', '.join(assignments)} "
                    "WHERE id = %s AND deleted = 0",
                    tuple(values + [replenishment_id]),
                )

        if payload.detail is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE replenishment_detail SET deleted = 1 "
                    "WHERE replenishment_id = %s AND deleted = 0",
                    (replenishment_id,),
                )
            _insert_details(connection, replenishment_id, payload.detail)
    return get_replenishment(replenishment_id)


def get_replenishment(replenishment_id: int) -> dict | None:
    replenishment = database.fetch_one(
        f"SELECT {REPLENISHMENT_COLUMNS} FROM resource_replenishment "
        "WHERE id = %s AND deleted = 0",
        (replenishment_id,),
    )
    if replenishment is None:
        return None
    replenishment["detail"] = database.fetch_all(
        """
        SELECT id, replenishment_id, resource_id, quantity, unit_cost, subtotal, remark,
               create_time, update_time
        FROM replenishment_detail
        WHERE replenishment_id = %s AND deleted = 0
        ORDER BY id
        """,
        (replenishment_id,),
    )
    return replenishment


def search_replenishment_details(
    *, resource_name: str | None, start_date: date | None, end_date: date | None
) -> list[dict]:
    filters = ["rd.deleted = 0", "rr.deleted = 0", "r.deleted = 0"]
    params: list[Any] = []
    if resource_name:
        filters.append("r.name LIKE %s")
        params.append(f"%{resource_name}%")
    if start_date:
        filters.append("DATE(rr.replenishment_time) >= %s")
        params.append(start_date)
    if end_date:
        filters.append("DATE(rr.replenishment_time) <= %s")
        params.append(end_date)

    rows = database.fetch_all(
        f"""
        SELECT rd.id, rd.replenishment_id, rd.resource_id, rd.quantity, rd.unit_cost,
               rd.subtotal, rd.remark, rd.create_time, rd.update_time,
               rr.replenishment_number, rr.replenishment_time,
               rr.status AS replenishment_status,
               r.resource_code, r.name AS resource_name, r.model AS resource_model,
               r.specification AS resource_specification, r.unit AS resource_unit,
               r.unit_cost AS reference_unit_cost, r.category, r.provider_id,
               p.provider_code, p.name AS provider_name,
               p.service_rating AS provider_service_rating,
               p.status AS provider_status
        FROM replenishment_detail rd
        JOIN resource_replenishment rr ON rr.id = rd.replenishment_id
        JOIN marketing_resource r ON r.id = rd.resource_id
        LEFT JOIN benefit_provider p ON p.id = r.provider_id AND p.deleted = 0
        WHERE {' AND '.join(filters)}
        ORDER BY rr.replenishment_time DESC, rd.id DESC
        LIMIT 1000
        """,
        tuple(params),
    )

    result = []
    for row in rows:
        detail = {
            key: row[key]
            for key in (
                "id", "replenishment_id", "resource_id", "quantity", "unit_cost",
                "subtotal", "remark", "create_time", "update_time",
                "replenishment_number", "replenishment_time",
                "replenishment_status",
            )
        }
        detail["resource_detail"] = {
            "id": row["resource_id"],
            "resource_code": row["resource_code"],
            "name": row["resource_name"],
            "model": row["resource_model"],
            "specification": row["resource_specification"],
            "unit": row["resource_unit"],
            "unit_cost": row["reference_unit_cost"],
            "category": row["category"],
            "provider_id": row["provider_id"],
        }
        provider_id = row["provider_id"]
        detail["provider"] = None if provider_id is None else {
            "id": provider_id,
            "provider_code": row["provider_code"],
            "name": row["provider_name"],
            "service_rating": row["provider_service_rating"],
            "status": row["provider_status"],
        }
        result.append(detail)
    return result
