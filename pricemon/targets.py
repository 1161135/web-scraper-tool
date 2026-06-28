"""Monitoring target validation and normalization."""

import re
from typing import Any


def validate_target(data: dict) -> list[str]:
    """Validate a target dict. Returns list of error messages (empty = valid)."""
    errors = []

    if not data.get("name") or not str(data["name"]).strip():
        errors.append("名称 (name) 不能为空")

    if not data.get("url") or not str(data["url"]).strip():
        errors.append("URL 不能为空")
    else:
        url = str(data["url"]).strip()
        if not url.startswith(("http://", "https://")):
            errors.append("URL 必须以 http:// 或 https:// 开头")

    if not data.get("price_field"):
        errors.append("价格字段名 (price_field) 不能为空")

    fields = data.get("fields")
    if fields is None:
        pass  # Will be filled automatically
    elif isinstance(fields, (list, tuple)):
        if len(fields) == 0:
            errors.append("字段列表 (fields) 不能为空")
    elif not str(fields).strip():
        errors.append("字段列表 (fields) 不能为空")

    schedule = data.get("schedule_seconds", 21600)
    try:
        s = int(schedule)
        if s < 300:
            errors.append("采集间隔不能小于 300 秒（5 分钟）")
    except (ValueError, TypeError):
        errors.append("采集间隔必须是整数（秒）")

    for key in ("min_price", "max_price"):
        val = data.get(key)
        if val is not None:
            try:
                float(val)
            except (ValueError, TypeError):
                errors.append(f"{key} 必须是数字")

    return errors


def normalize_price(raw_value: Any) -> float | None:
    """Try to extract a numeric price from a raw extracted value.

    Handles: '¥31.00', '31.00元', '$99.99', '1,234.56', etc.
    Returns None if no price can be parsed.
    """
    if raw_value is None:
        return None

    text = str(raw_value).strip()
    if not text:
        return None

    # Remove common currency symbols and non-numeric characters except . and -
    text = text.replace(",", "").replace("，", "")
    # Extract first number (including decimal)
    match = re.search(r"-?\d+\.?\d*", text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None
