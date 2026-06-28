"""E-commerce competitive price monitoring module.

Reuses scraper.browser and scraper.extractor for data collection.
Manages timed scraping, price change detection, and alerting via SQLite + APScheduler.
"""

from pricemon.db import (
    init_db, add_target, update_target, delete_target,
    get_target, get_all_targets,
    record_price, get_price_history, get_latest_price,
    add_alert, get_alerts, mark_alert_read,
    export_targets, import_targets,
)
from pricemon.targets import validate_target, normalize_price
from pricemon.tracker import process_price, get_price_trend
from pricemon.alerts import dispatch_alert
from pricemon.scheduler import init_scheduler, add_job, remove_job, run_now

__all__ = [
    "init_db", "add_target", "update_target", "delete_target",
    "get_target", "get_all_targets",
    "record_price", "get_price_history", "get_latest_price",
    "add_alert", "get_alerts", "mark_alert_read",
    "export_targets", "import_targets",
    "validate_target", "normalize_price",
    "process_price", "get_price_trend",
    "dispatch_alert",
    "init_scheduler", "add_job", "remove_job", "run_now",
]
