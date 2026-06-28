"""Flask Blueprint for the price monitoring web UI."""

import json
import os
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from pricemon.db import (
    get_all_targets, get_target, add_target, update_target, delete_target,
    get_price_history, get_alerts, mark_alert_read, get_unread_alert_count,
    export_targets, import_targets,
)
from pricemon.targets import validate_target
from pricemon.scheduler import add_job, remove_job, run_now
from pricemon.tracker import get_price_trend

bp = Blueprint("monitor", __name__, template_folder="templates",
               static_folder="static", url_prefix="/monitor")


@bp.route("/")
def dashboard():
    """Monitoring dashboard — overview of all targets."""
    targets = get_all_targets(enabled_only=False)
    unread = get_unread_alert_count()
    return render_template("monitor_dashboard.html", targets=targets, unread=unread)


@bp.route("/targets")
def list_targets():
    """Target management page."""
    targets = get_all_targets(enabled_only=False)
    unread = get_unread_alert_count()
    return render_template("monitor_targets.html", targets=targets, unread=unread)


@bp.route("/targets/add", methods=["GET", "POST"])
def add_target_page():
    """Add a new monitoring target."""
    unread = get_unread_alert_count()
    if request.method == "POST":
        data = {
            "name": request.form.get("name", "").strip(),
            "url": request.form.get("url", "").strip(),
            "fields": [f.strip() for f in request.form.get("fields", "").replace("，", ",").split(",") if f.strip()],
            "price_field": request.form.get("price_field", "价格").strip(),
            "schedule_seconds": int(request.form.get("schedule_seconds", 21600)),
            "min_price": _float_or_none(request.form.get("min_price")),
            "max_price": _float_or_none(request.form.get("max_price")),
            "max_change_pct": _float_or_none(request.form.get("max_change_pct", 10)),
        }
        
        # Check for duplicate URL
        existing = get_all_targets(enabled_only=False)
        dup = [t for t in existing if t["url"] == data["url"]]
        if dup:
            return render_template("monitor_target_form.html",
                errors=[f"该URL已在监控列表中：{dup[0]['name']}（无需重复添加）"],
                data=data, unread=unread, duplicate_id=dup[0]["id"])
        
        errors = validate_target(data)
        if errors:
            return render_template("monitor_target_form.html", errors=errors, data=data, unread=unread)

        try:
            target = add_target(data)
        except ValueError as e:
            # Duplicate URL detected
            dup = [t for t in get_all_targets(enabled_only=False) if t["url"] == data["url"]]
            dup_id = dup[0]["id"] if dup else None
            return render_template("monitor_target_form.html",
                errors=[str(e)], data=data, unread=unread, duplicate_id=dup_id)
        
        add_job(target)  # Register with scheduler
        return redirect(url_for("monitor.target_detail", id=target["id"]))

    # Pre-fill from GET parameters (from scraped data)
    prefill = {
        "name": request.args.get("name", ""),
        "url": request.args.get("url", ""),
        "fields": [f.strip() for f in request.args.get("fields", "").split(",") if f.strip()],
        "price_field": request.args.get("price_field", "价格"),
    }
    if prefill["url"]:
        return render_template("monitor_target_form.html", data=prefill, errors=None, unread=unread)
    return render_template("monitor_target_form.html", data=None, errors=None, unread=unread)


@bp.route("/target/<id>")
def target_detail(id: str):
    """Target detail with price trend chart."""
    target = get_target(id)
    if not target:
        return "Target not found", 404

    trend = get_price_trend(id, days=30)
    alerts = get_alerts(target_id=id, limit=20)
    unread = get_unread_alert_count()

    # Compute price statistics
    prices = [t["price"] for t in trend]
    stats = {}
    if prices:
        stats = {
            "min": min(prices),
            "max": max(prices),
            "avg": round(sum(prices) / len(prices), 2),
            "latest": prices[-1],
            "count": len(prices),
        }
        if len(prices) >= 2:
            first, last = prices[0], prices[-1]
            stats["total_change"] = round(last - first, 2)
            stats["total_change_pct"] = round((last - first) / first * 100, 2) if first else 0
        else:
            stats["total_change"] = 0
            stats["total_change_pct"] = 0

    return render_template(
        "monitor_target_detail.html",
        target=target, trend=trend, alerts=alerts, unread=unread,
        stats=stats,
    )


@bp.route("/target/<id>/edit", methods=["GET", "POST"])
def edit_target(id: str):
    """Edit a monitoring target."""
    target = get_target(id)
    if not target:
        return "Target not found", 404

    unread = get_unread_alert_count()
    if request.method == "POST":
        updates = {
            "name": request.form.get("name", "").strip(),
            "url": request.form.get("url", "").strip(),
            "fields": [f.strip() for f in request.form.get("fields", "").replace("，", ",").split(",") if f.strip()],
            "price_field": request.form.get("price_field", "价格").strip(),
            "schedule_seconds": int(request.form.get("schedule_seconds", 21600)),
            "min_price": _float_or_none(request.form.get("min_price")),
            "max_price": _float_or_none(request.form.get("max_price")),
            "max_change_pct": _float_or_none(request.form.get("max_change_pct", 10)),
            "enabled": request.form.get("enabled") == "on",
        }
        errors = validate_target(updates)
        if errors:
            return render_template("monitor_target_form.html", errors=errors, data=updates, edit=True, target_id=id, unread=unread)

        update_target(id, updates)
        updated = get_target(id)
        add_job(updated)  # Sync scheduler
        return redirect(url_for("monitor.target_detail", id=id))

    return render_template(
        "monitor_target_form.html", data=target, edit=True, target_id=id, unread=unread,
    )


@bp.route("/target/<id>/delete", methods=["POST"])
def delete_target_route(id: str):
    """Delete a monitoring target."""
    remove_job(id)
    delete_target(id)
    return redirect(url_for("monitor.list_targets"))


@bp.route("/target/<id>/run", methods=["POST"])
def run_target_now(id: str):
    """Manually trigger an immediate capture."""
    result = run_now(id)
    return redirect(url_for("monitor.target_detail", id=id))


@bp.route("/alerts")
def list_alerts():
    """Alert list page."""
    alerts = get_alerts(unread_only=False, limit=100)
    unread = get_unread_alert_count()
    return render_template("monitor_alerts.html", alerts=alerts, unread=unread)


@bp.route("/alerts/<int:id>/read", methods=["POST"])
def read_alert(id: int):
    """Mark an alert as read."""
    mark_alert_read(id)
    return redirect(url_for("monitor.list_alerts"))


# ── JSON API (for Chart.js) ──────────────────────────────────────────────

@bp.route("/api/targets")
def api_targets():
    """JSON: list all targets."""
    targets = get_all_targets(enabled_only=False)
    return jsonify(targets)


@bp.route("/api/target/<id>/history")
def api_target_history(id: str):
    """JSON: price history for Chart.js."""
    trend = get_price_trend(id, days=90)
    return jsonify({
        "labels": [t["captured_at"][:19] for t in trend],
        "prices": [t["price"] for t in trend],
    })


@bp.route("/api/alerts")
def api_alerts():
    """JSON: recent alerts."""
    alerts = get_alerts(unread_only=False, limit=50)
    return jsonify(alerts)


@bp.route("/api/targets/export")
def api_export():
    """JSON: export all targets."""
    targets = export_targets()
    return jsonify(targets)


@bp.route("/api/targets/import", methods=["POST"])
def api_import():
    """Import targets from JSON body."""
    data = request.get_json(force=True)
    if isinstance(data, list):
        count = 0
        skipped = 0
        for item in data:
            if "name" in item and "url" in item:
                try:
                    from pricemon.db import add_target
                    t = add_target(item)
                    if t.get("enabled", True):
                        add_job(t)
                    count += 1
                except ValueError:
                    skipped += 1
        return jsonify({"imported": count, "skipped_duplicates": skipped})
    return jsonify({"error": "Expected a JSON array"}), 400


def _float_or_none(val: str | None) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
