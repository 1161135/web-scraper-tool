"""Data persistence — JSON and CSV output."""

import csv
import json
import os
from datetime import datetime


def _output_dir() -> str:
    """Create and return timestamped output directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join("output", ts)
    os.makedirs(out, exist_ok=True)
    return out


def save_json(data: dict, out_dir: str, meta: dict | None = None) -> str:
    """Save extracted data as JSON with metadata.

    Args:
        data: Extracted field dict.
        out_dir: Output directory path.
        meta: Optional metadata (url, timestamp, etc.).

    Returns:
        Path to saved file.

    """
    payload = {
        "meta": meta or {},
        "data": data,
    }
    path = os.path.join(out_dir, "data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def save_csv(data: dict, out_dir: str) -> str:
    """Save extracted data as CSV (one row).

    Args:
        data: Extracted field dict.
        out_dir: Output directory path.

    Returns:
        Path to saved file.

    """
    path = os.path.join(out_dir, "data.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerow(data)
    return path


def save_all(data: dict, url: str, output_format: str = "both") -> dict[str, str]:
    """Save single-item data in requested formats.

    Args:
        data: Extracted field dict.
        url: Source URL (included in metadata).
        output_format: 'json', 'csv', or 'both'.

    Returns:
        Dict mapping format names to file paths.

    """
    out_dir = _output_dir()
    meta = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
    }

    saved = {}
    if output_format in ("json", "both"):
        p = save_json(data, out_dir, meta)
        saved["json"] = p
    if output_format in ("csv", "both"):
        p = save_csv(data, out_dir)
        saved["csv"] = p

    return saved


def save_json_batch(items: list[dict], out_dir: str, meta: dict | None = None) -> str:
    """Save multiple items as a JSON array.

    Args:
        items: List of extracted field dicts.
        out_dir: Output directory path.
        meta: Optional metadata dict.

    Returns:
        Path to saved file.

    """
    payload = {
        "meta": meta or {},
        "count": len(items),
        "items": items,
    }
    path = os.path.join(out_dir, "data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def save_csv_batch(items: list[dict], out_dir: str) -> str:
    """Save multiple items as CSV (multiple rows).

    Args:
        items: List of extracted field dicts.
        out_dir: Output directory path.

    Returns:
        Path to saved file.

    """
    # Collect all unique keys across all items
    all_keys: list[str] = []
    seen = set()
    for item in items:
        for k in item:
            if k not in seen:
                seen.add(k)
                all_keys.append(k)

    path = os.path.join(out_dir, "data.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for item in items:
            writer.writerow(item)
    return path


def save_batch(items: list[dict], source_url: str, fields: list[str],
               output_format: str = "both") -> dict[str, str]:
    """Save batch-collected items in requested formats.

    Args:
        items: List of extracted field dicts.
        source_url: The list/search page URL.
        fields: The field names extracted.
        output_format: 'json', 'csv', or 'both'.

    Returns:
        Dict mapping format names to file paths.

    """
    out_dir = _output_dir()
    meta = {
        "source_url": source_url,
        "fields": fields,
        "count": len(items),
        "timestamp": datetime.now().isoformat(),
    }

    saved = {}
    if output_format in ("json", "both"):
        p = save_json_batch(items, out_dir, meta)
        saved["json"] = p
    if output_format in ("csv", "both"):
        p = save_csv_batch(items, out_dir)
        saved["csv"] = p

    return saved
