"""Price tracking and change detection engine."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from pricemon.db import get_target, record_price, get_latest_price, add_alert
from pricemon.targets import normalize_price
from pricemon.alerts import dispatch_alert

logger = logging.getLogger(__name__)


def process_price(target_id: str, price: float, raw_data: dict | None = None) -> dict:
    """Process a newly captured price: store, detect changes, generate alerts.

    Args:
        target_id: The monitoring target ID.
        price: The numeric price value.
        raw_data: Optional full extraction result for snapshot.

    Returns:
        Dict with keys: history_id, price, old_price, change_pct, alerts (list).
    """
    target = get_target(target_id)
    if target is None:
        raise ValueError(f"Target not found: {target_id}")

    old_price = target.get("last_price")

    # Record the price
    history_id = record_price(target_id, price, raw_data)

    result = {
        "history_id": history_id,
        "price": price,
        "old_price": old_price,
        "change_pct": 0.0,
        "alerts": [],
    }

    # Detect changes
    if old_price is not None and old_price != price:
        change = price - old_price
        change_pct = round(abs(change) / old_price * 100, 2)
        result["change_pct"] = change_pct

        direction = "rise" if price > old_price else "drop"
        threshold = target.get("max_change_pct", 10)

        if change_pct >= threshold:
            alert_data = {
                "alert_type": f"price_{direction}",
                "severity": "warning",
                "message": (
                    f"【{'涨价' if direction == 'rise' else '降价'}告警】"
                    f"{target['name']}：{old_price} → {price}"
                    f"（{'涨' if direction == 'rise' else '跌'}{change_pct}%）"
                ),
                "old_price": old_price,
                "new_price": price,
                "change_pct": change_pct if direction == "rise" else -change_pct,
            }
            alert_id = add_alert(target_id, alert_data)
            alert_data["id"] = alert_id
            dispatch_alert(alert_data, target)
            result["alerts"].append(alert_data)
            logger.warning("Price alert for %s: %s", target["name"], alert_data["message"])

    # Threshold check (always runs, even without prior price)
    alerts = _check_thresholds(target, price)
    for alert_data in alerts:
        alert_id = add_alert(target_id, alert_data)
        alert_data["id"] = alert_id
        dispatch_alert(alert_data, target)
        result["alerts"].append(alert_data)
        logger.warning("Threshold alert for %s: %s", target["name"], alert_data["message"])

    return result


def _check_thresholds(target: dict, price: float) -> list[dict]:
    """Check price against configured thresholds."""
    alerts = []
    min_p = target.get("min_price")
    max_p = target.get("max_price")

    if min_p is not None and price < min_p:
        alerts.append({
            "alert_type": "threshold_low",
            "severity": "critical",
            "message": (
                f"【低价告警】{target['name']}：当前价格 {price}"
                f"，低于设定阈值 {min_p}"
            ),
            "old_price": target.get("last_price"),
            "new_price": price,
            "change_pct": None,
        })

    if max_p is not None and price > max_p:
        alerts.append({
            "alert_type": "threshold_high",
            "severity": "critical",
            "message": (
                f"【高价告警】{target['name']}：当前价格 {price}"
                f"，高于设定阈值 {max_p}"
            ),
            "old_price": target.get("last_price"),
            "new_price": price,
            "change_pct": None,
        })

    return alerts


def get_price_trend(target_id: str, days: int = 30) -> list[dict]:
    """Get price history for chart display (oldest first)."""
    from pricemon.db import get_price_history

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_history = get_price_history(target_id, limit=500)
    # Filter by date and sort ascending for chart
    filtered = [
        {"price": h["price"], "captured_at": h["captured_at"]}
        for h in all_history
        if h["captured_at"] >= cutoff.isoformat()
    ]
    filtered.reverse()  # oldest first for chart
    return filtered
