"""JSON-safe serialization helpers."""

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any


_SNAKE_PART = re.compile(r"_([a-z])")


def _camel_key(key: str) -> str:
    return _SNAKE_PART.sub(lambda match: match.group(1).upper(), key)


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {_camel_key(str(key)): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value

