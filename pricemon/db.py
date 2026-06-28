"""SQLite data layer for price monitoring.

Three tables:
- targets: monitoring target definitions
- price_history: captured price snapshots
- alerts: generated alert records
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


_DB_PATH = None


def _get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = os.getenv("PRICEMON_DB_PATH", "pricemon_data.db")
    return _DB_PATH


def set_db_path(path: str) -> None:
    """Override the database path (used for testing with :memory:)."""
    global _DB_PATH
    _DB_PATH = path


def _connect() -> sqlite3.Connection:
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initialize the database, creating tables if they don't exist."""
    if db_path:
        set_db_path(db_path)
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS targets (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            url             TEXT NOT NULL,
            fields          TEXT NOT NULL DEFAULT '[]',
            price_field     TEXT NOT NULL DEFAULT '价格',
            schedule_seconds INTEGER NOT NULL DEFAULT 21600,
            min_price       REAL,
            max_price       REAL,
            max_change_pct  REAL DEFAULT 10,
            enabled         INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            last_captured_at TEXT,
            last_price      REAL
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id     TEXT NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
            price         REAL NOT NULL,
            raw_data      TEXT,
            captured_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id     TEXT NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
            alert_type    TEXT NOT NULL,
            severity      TEXT NOT NULL DEFAULT 'warning',
            message       TEXT,
            old_price     REAL,
            new_price     REAL,
            change_pct    REAL,
            is_read       INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_price_history_target
            ON price_history(target_id, captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_target
            ON alerts(target_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_alerts_unread
            ON alerts(is_read, created_at DESC);
    """)
    conn.commit()
    conn.close()


# ── Target CRUD ──────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_target(data: dict) -> dict:
    """Add a new monitoring target. Returns the saved target dict.
    
    If a target with the same URL already exists, raises ValueError.
    """
    # Check for duplicate URL
    existing = get_all_targets(enabled_only=False)
    for t in existing:
        if t["url"] == data.get("url", ""):
            raise ValueError(f"该URL已在监控列表中：{t['name']}")
    
    target = {
        "id": data.get("id", uuid.uuid4().hex),
        "name": data["name"],
        "url": data["url"],
        "fields": json.dumps(data.get("fields", [data.get("price_field", "价格")]), ensure_ascii=False),
        "price_field": data.get("price_field", "价格"),
        "schedule_seconds": int(data.get("schedule_seconds", 21600)),
        "min_price": data.get("min_price"),
        "max_price": data.get("max_price"),
        "max_change_pct": float(data.get("max_change_pct", 10)),
        "enabled": 1 if data.get("enabled", True) else 0,
        "created_at": _now(),
        "updated_at": _now(),
        "last_captured_at": None,
        "last_price": None,
    }
    conn = _connect()
    conn.execute(
        """INSERT INTO targets (id, name, url, fields, price_field,
           schedule_seconds, min_price, max_price, max_change_pct,
           enabled, created_at, updated_at, last_captured_at, last_price)
           VALUES (:id, :name, :url, :fields, :price_field,
           :schedule_seconds, :min_price, :max_price, :max_change_pct,
           :enabled, :created_at, :updated_at, :last_captured_at, :last_price)""",
        target,
    )
    conn.commit()
    conn.close()
    return _row_to_target(target)


def update_target(target_id: str, updates: dict) -> dict | None:
    """Update a monitoring target. Returns updated target or None."""
    allowed = {"name", "url", "fields", "price_field", "schedule_seconds",
               "min_price", "max_price", "max_change_pct", "enabled"}
    sets = []
    params = {"id": target_id}
    for key, val in updates.items():
        if key in allowed:
            if key == "fields" and isinstance(val, list):
                val = json.dumps(val, ensure_ascii=False)
            if key == "enabled":
                val = 1 if val else 0
            sets.append(f"{key} = :{key}")
            params[key] = val
    if not sets:
        return get_target(target_id)
    sets.append("updated_at = :updated_at")
    params["updated_at"] = _now()

    conn = _connect()
    conn.execute(
        f"UPDATE targets SET {', '.join(sets)} WHERE id = :id",
        params,
    )
    conn.commit()
    conn.close()
    return get_target(target_id)


def delete_target(target_id: str) -> bool:
    """Delete a target and its related history + alerts. Returns True if deleted."""
    conn = _connect()
    cur = conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_target(target_id: str) -> dict | None:
    """Get a single target by ID."""
    conn = _connect()
    row = conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
    conn.close()
    return _row_to_target(row) if row else None


def get_all_targets(enabled_only: bool = True) -> list[dict]:
    """Get all targets, optionally only enabled ones."""
    conn = _connect()
    if enabled_only:
        rows = conn.execute(
            "SELECT * FROM targets WHERE enabled = 1 ORDER BY created_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM targets ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [_row_to_target(r) for r in rows]


def _row_to_target(row: sqlite3.Row) -> dict:
    d = dict(row)
    if isinstance(d.get("fields"), str):
        try:
            d["fields"] = json.loads(d["fields"])
        except (json.JSONDecodeError, TypeError):
            d["fields"] = [d.get("price_field", "价格")]
    d["enabled"] = bool(d["enabled"])
    return d


# ── Price History ────────────────────────────────────────────────────────

def record_price(target_id: str, price: float, raw_data: dict | None = None) -> int:
    """Record a price snapshot. Returns the history record ID."""
    captured_at = _now()
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO price_history (target_id, price, raw_data, captured_at) VALUES (?, ?, ?, ?)",
        (target_id, price, json.dumps(raw_data, ensure_ascii=False) if raw_data else None, captured_at),
    )
    # Also update the target's last_price and last_captured_at
    conn.execute(
        "UPDATE targets SET last_price = ?, last_captured_at = ?, updated_at = ? WHERE id = ?",
        (price, captured_at, captured_at, target_id),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def get_price_history(target_id: str, limit: int = 50) -> list[dict]:
    """Get price history for a target, newest first."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, price, captured_at FROM price_history "
        "WHERE target_id = ? ORDER BY captured_at DESC LIMIT ?",
        (target_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_price(target_id: str) -> float | None:
    """Get the most recent price for a target."""
    conn = _connect()
    row = conn.execute(
        "SELECT price FROM price_history WHERE target_id = ? ORDER BY captured_at DESC LIMIT 1",
        (target_id,),
    ).fetchone()
    conn.close()
    return row["price"] if row else None


def get_all_price_history(limit: int = 200) -> list[dict]:
    """Get all recent price records across all targets, newest first."""
    conn = _connect()
    rows = conn.execute(
        "SELECT ph.id, ph.target_id, t.name as target_name, ph.price, ph.captured_at "
        "FROM price_history ph JOIN targets t ON t.id = ph.target_id "
        "ORDER BY ph.captured_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Alerts ───────────────────────────────────────────────────────────────

def add_alert(target_id: str, alert_data: dict) -> int:
    """Record an alert. Returns the alert ID."""
    created_at = _now()
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO alerts (target_id, alert_type, severity, message,
           old_price, new_price, change_pct, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            target_id,
            alert_data["alert_type"],
            alert_data.get("severity", "warning"),
            alert_data.get("message", ""),
            alert_data.get("old_price"),
            alert_data.get("new_price"),
            alert_data.get("change_pct"),
            created_at,
        ),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def get_alerts(target_id: str | None = None, unread_only: bool = False, limit: int = 50) -> list[dict]:
    """Get alerts, optionally filtered."""
    conn = _connect()
    if target_id:
        if unread_only:
            rows = conn.execute(
                "SELECT a.*, t.name as target_name FROM alerts a "
                "JOIN targets t ON t.id = a.target_id "
                "WHERE a.target_id = ? AND a.is_read = 0 "
                "ORDER BY a.created_at DESC LIMIT ?",
                (target_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.*, t.name as target_name FROM alerts a "
                "JOIN targets t ON t.id = a.target_id "
                "WHERE a.target_id = ? ORDER BY a.created_at DESC LIMIT ?",
                (target_id, limit),
            ).fetchall()
    else:
        if unread_only:
            rows = conn.execute(
                "SELECT a.*, t.name as target_name FROM alerts a "
                "JOIN targets t ON t.id = a.target_id "
                "WHERE a.is_read = 0 ORDER BY a.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.*, t.name as target_name FROM alerts a "
                "JOIN targets t ON t.id = a.target_id "
                "ORDER BY a.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alert_read(alert_id: int) -> bool:
    """Mark an alert as read. Returns True if found."""
    conn = _connect()
    cur = conn.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_unread_alert_count() -> int:
    """Get the count of unread alerts."""
    conn = _connect()
    row = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE is_read = 0").fetchone()
    conn.close()
    return row["cnt"]


# ── Import / Export ──────────────────────────────────────────────────────

def export_targets(filepath: str | None = None) -> list[dict]:
    """Export all targets to a JSON-serializable list."""
    targets = get_all_targets(enabled_only=False)
    export = []
    for t in targets:
        export.append({
            "id": t["id"],
            "name": t["name"],
            "url": t["url"],
            "fields": t["fields"],
            "price_field": t["price_field"],
            "schedule_seconds": t["schedule_seconds"],
            "min_price": t["min_price"],
            "max_price": t["max_price"],
            "max_change_pct": t["max_change_pct"],
            "enabled": t["enabled"],
        })
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
    return export


def import_targets(data: list[dict]) -> int:
    """Import targets from a JSON list. Returns count imported."""
    count = 0
    for item in data:
        if "name" in item and "url" in item:
            add_target(item)
            count += 1
    return count
