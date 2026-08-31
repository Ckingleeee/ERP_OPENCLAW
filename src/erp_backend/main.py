"""FastAPI implementation of the ERP service consumed by the MCP server."""

from contextlib import asynccontextmanager
from datetime import date
import logging

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from erp_backend import database, repository
from erp_backend.config import settings
from erp_backend.schemas import ReplenishmentCreate, ReplenishmentUpdate
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
    title="Card Benefits Operations API",
    version="1.0.0",
    description="Credit-card benefits and marketing-resource operations backend.",
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


@app.get("/api/providers/search")
def search_providers(name: str = Query(min_length=1, max_length=100)):
    return success(repository.search_providers(name.strip()))


@app.get("/api/resources/page")
def list_resources(
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=500),
    name: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=50),
    provider_id: int | None = Query(default=None, alias="providerId", gt=0),
):
    return success(
        repository.list_resources(
            current=current,
            size=size,
            name=name.strip() if name else None,
            category=category.strip() if category else None,
            provider_id=provider_id,
        )
    )


@app.get("/api/resources/search")
def search_resources(name: str = Query(min_length=1, max_length=100)):
    return success(repository.search_resources(name.strip()))


@app.get("/api/resources/provider/{provider_id}")
def list_resources_by_provider(provider_id: int):
    if provider_id <= 0:
        return error("provider_id must be greater than zero", code=422, status_code=422)
    return success(repository.list_resources_by_provider(provider_id))


@app.get("/api/quotas/warning")
def quota_warnings():
    return success(repository.quota_warnings())


@app.post("/api/replenishments/create")
def create_replenishment(payload: ReplenishmentCreate):
    return success(repository.create_replenishment(payload), "replenishment created")


@app.put("/api/replenishments/update/{replenishment_id}")
def update_replenishment(
    replenishment_id: int, payload: ReplenishmentUpdate
):
    if replenishment_id <= 0:
        return error(
            "replenishment_id must be greater than zero", code=422, status_code=422
        )
    replenishment = repository.update_replenishment(replenishment_id, payload)
    if replenishment is None:
        return error("replenishment not found", code=404, status_code=404)
    return success(replenishment, "replenishment updated")


@app.get("/api/replenishments/search-details")
def search_replenishment_details(
    resource_name: str | None = Query(
        default=None, alias="resourceName", max_length=100
    ),
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
):
    if start_date and end_date and start_date > end_date:
        return error("startDate cannot be later than endDate", code=422, status_code=422)
    return success(
        repository.search_replenishment_details(
            resource_name=resource_name.strip() if resource_name else None,
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
