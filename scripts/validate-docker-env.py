#!/usr/bin/env python3
"""Validate the Docker deployment environment without printing secrets."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse


PLACEHOLDER_PREFIXES = (
    "replace-with",
    "change-me",
    "your-",
    "<",
)

REQUIRED_VALUES = {
    "MYSQL_ROOT_PASSWORD": 1,
    "ERP_DB_PASSWORD": 1,
    "MONGO_ROOT_PASSWORD": 1,
    "MONGODB_APP_PASSWORD": 1,
    "ERP_ADMIN_PASSWORD": 8,
    "DEEPSEEK_API_KEY": 8,
    "DEEPSEEK_BASE_URL": 8,
    "ALIBABA_API_KEY": 8,
    "OPEN_SANDBOX_API_KEY": 16,
    "AUTH_JWT_SECRET": 32,
}

URL_VALUES = (
    "DEEPSEEK_BASE_URL",
    "ALIBABA_BASE_URL",
    "OPEN_SANDBOX_DOMAIN",
)

URL_SAFE_MONGODB_PATTERN = re.compile(r"^[A-Za-z0-9._~-]+$")


def parse_env(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    duplicates: list[str] = []

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"第 {line_number} 行不是 KEY=VALUE 格式")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"第 {line_number} 行变量名无效：{key!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key in values:
            duplicates.append(key)
        values[key] = value

    return values, duplicates


def is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or normalized.startswith(PLACEHOLDER_PREFIXES)


def validate_url(key: str, value: str, errors: list[str]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{key} 必须是完整的 http/https URL")


def validate(path: Path) -> int:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        values, duplicates = parse_env(path)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"环境文件读取失败：{exc}", file=sys.stderr)
        return 1

    if duplicates:
        errors.append("存在重复变量：" + ", ".join(sorted(set(duplicates))))

    for key, minimum_length in REQUIRED_VALUES.items():
        value = values.get(key, "")
        if is_placeholder(value):
            errors.append(f"{key} 尚未配置或仍为占位值")
        elif len(value) < minimum_length:
            errors.append(f"{key} 长度不能少于 {minimum_length} 个字符")

    for key in (
        "MYSQL_ROOT_PASSWORD",
        "ERP_DB_PASSWORD",
        "MONGO_ROOT_PASSWORD",
        "MONGODB_APP_PASSWORD",
    ):
        value = values.get(key, "")
        if value and not is_placeholder(value) and len(value) < 16:
            warnings.append(f"{key} 少于建议的 16 个字符，后续应安排轮换")

    for key in URL_VALUES:
        value = values.get(key, "")
        if not value:
            errors.append(f"{key} 尚未配置")
        else:
            validate_url(key, value, errors)

    for key in ("MONGODB_APP_USER", "MONGODB_APP_PASSWORD"):
        value = values.get(key, "")
        if value and not URL_SAFE_MONGODB_PATTERN.fullmatch(value):
            errors.append(
                f"{key} 会直接写入 MongoDB URI，只能使用字母、数字、点、下划线、波浪线和连字符"
            )

    port_text = values.get("HTTP_PORT", "80")
    try:
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        errors.append("HTTP_PORT 必须是 1 到 65535 之间的整数")

    cookie_secure = values.get("AUTH_COOKIE_SECURE", "false").lower()
    if cookie_secure not in {"true", "false"}:
        errors.append("AUTH_COOKIE_SECURE 只能是 true 或 false")
    if cookie_secure == "true" and any(
        origin.strip().startswith("http://")
        for origin in values.get("CORS_ALLOWED_ORIGINS", "").split(",")
    ):
        warnings.append("AUTH_COOKIE_SECURE=true，但 CORS 中仍包含 HTTP 地址")

    if os.name == "posix":
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            warnings.append(
                f"{path} 当前权限为 {mode:04o}，生产环境建议执行 chmod 600 {path}"
            )

    for warning in warnings:
        print(f"警告：{warning}", file=sys.stderr)
    for error in errors:
        print(f"错误：{error}", file=sys.stderr)

    if errors:
        print(f"环境校验失败，共 {len(errors)} 项错误。", file=sys.stderr)
        return 1

    print("环境变量校验通过（未输出任何密钥）。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_file", type=Path)
    parser.add_argument("--get", metavar="KEY", help="只输出指定变量，供部署脚本内部使用")
    args = parser.parse_args()

    if not args.env_file.is_file():
        print(f"环境文件不存在：{args.env_file}", file=sys.stderr)
        return 1

    if args.get:
        try:
            values, _ = parse_env(args.env_file)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"环境文件读取失败：{exc}", file=sys.stderr)
            return 1
        if args.get not in values:
            return 2
        print(values[args.get])
        return 0

    return validate(args.env_file)


if __name__ == "__main__":
    raise SystemExit(main())
