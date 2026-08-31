"""ERP backend configuration loaded from environment variables."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv(override=False)


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_host: str = os.getenv("ERP_API_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("ERP_API_PORT", "8080"))
    db_host: str = os.getenv("ERP_DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("ERP_DB_PORT", "3306"))
    db_user: str = os.getenv("ERP_DB_USER", "root")
    db_password: str = os.getenv("ERP_DB_PASSWORD", "")
    db_name: str = os.getenv("ERP_DB_NAME", "benefits_ops_db")
    db_connect_timeout: int = int(os.getenv("ERP_DB_CONNECT_TIMEOUT", "5"))
    check_db_on_startup: bool = _as_bool(
        os.getenv("ERP_DB_CHECK_ON_STARTUP"), default=True
    )


settings = Settings()
