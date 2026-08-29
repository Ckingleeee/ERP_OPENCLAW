"""FastAPI implementation of the ERP service consumed by the MCP server."""

from contextlib import asynccontextmanager
from datetime import date
import logging

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from erp_backend import database, repository
from erp_backend.config import settings
from erp_backend.schemas import OrderCreate, OrderUpdate
from erp_backend.serialization import json_value


logger = logging.getLogger(__name__)


def success(data=None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": json_value(data)}


def error(message: str, *, code: int = 400, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "data": None},
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.check_db_on_startup:
        database.ping()
    yield


app = FastAPI(
    title="Motor Parts ERP API",
    version="1.0.0",
    description="Python ERP backend compatible with the project's MCP tools.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return error(str(exc), code=422, status_code=422)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return error(str(exc), code=400, status_code=400)


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    logger.exception("Unhandled ERP API error")
    return error("Internal server error", code=500, status_code=500)


@app.get("/")
def root():
    return success({"name": app.title, "version": app.version})


@app.get("/health")
def health():
    database.ping()
    return success({"status": "healthy", "database": settings.db_name})


@app.get("/api/suppliers/search")
def search_suppliers(name: str = Query(min_length=1, max_length=100)):
    return success(repository.search_suppliers(name.strip()))


@app.get("/api/parts/page")
def list_parts(
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=500),
    name: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=50),
    supplier_id: int | None = Query(default=None, alias="supplierId", gt=0),
):
    return success(
        repository.list_parts(
            current=current,
            size=size,
            name=name.strip() if name else None,
            category=category.strip() if category else None,
            supplier_id=supplier_id,
        )
    )


@app.get("/api/parts/search")
def search_parts(name: str = Query(min_length=1, max_length=100)):
    return success(repository.search_parts(name.strip()))


@app.get("/api/parts/supplier/{supplier_id}")
def list_parts_by_supplier(supplier_id: int):
    if supplier_id <= 0:
        return error("supplier_id must be greater than zero", code=422, status_code=422)
    return success(repository.list_parts_by_supplier(supplier_id))


@app.get("/api/inventory/warning")
def inventory_warnings():
    return success(repository.inventory_warnings())


@app.post("/api/orders/create")
def create_order(payload: OrderCreate):
    return success(repository.create_order(payload), "order created")


@app.put("/api/orders/update/{order_id}")
def update_order(order_id: int, payload: OrderUpdate):
    if order_id <= 0:
        return error("order_id must be greater than zero", code=422, status_code=422)
    order = repository.update_order(order_id, payload)
    if order is None:
        return error("order not found", code=404, status_code=404)
    return success(order, "order updated")


@app.get("/api/orders/search-details")
def search_order_details(
    part_name: str | None = Query(default=None, alias="partName", max_length=100),
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
):
    if start_date and end_date and start_date > end_date:
        return error("startDate cannot be later than endDate", code=422, status_code=422)
    return success(
        repository.search_order_details(
            part_name=part_name.strip() if part_name else None,
            start_date=start_date,
            end_date=end_date,
        )
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "erp_backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
