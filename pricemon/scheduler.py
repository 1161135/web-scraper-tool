"""APScheduler integration for timed price monitoring."""

import logging
import threading
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from pricemon.db import get_all_targets, get_target
from pricemon.tracker import process_price
from pricemon.targets import normalize_price

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def init_scheduler() -> BackgroundScheduler:
    """Initialize the background scheduler and start all enabled jobs."""
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return _scheduler

        _scheduler = BackgroundScheduler(
            daemon=True,
            job_defaults={
                "coalesce": True,        # Combine missed runs into one
                "max_instances": 1,       # Don't run concurrently
                "misfire_grace_time": 300, # Allow 5 min delay before skipping
            },
        )

        # Load and schedule all enabled targets
        targets = get_all_targets(enabled_only=True)
        for t in targets:
            _add_target_job(t)

        _scheduler.start()
        logger.info("Scheduler started with %d jobs", len(targets))
        return _scheduler


def stop_scheduler() -> None:
    """Shut down the scheduler."""
    global _scheduler
    with _lock:
        if _scheduler:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            logger.info("Scheduler stopped")


def add_job(target: dict) -> None:
    """Add or update a job for a target."""
    global _scheduler
    with _lock:
        if _scheduler is None:
            return
        # Remove existing job if any
        job_id = f"monitor_{target['id']}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)

        if target.get("enabled", True):
            _add_target_job(target)


def _add_target_job(target: dict) -> None:
    """Internal: create a scheduler job for a target."""
    if _scheduler is None:
        return

    job_id = f"monitor_{target['id']}"
    interval = target.get("schedule_seconds", 21600)

    _scheduler.add_job(
        _execute_capture,
        trigger=IntervalTrigger(seconds=interval),
        id=job_id,
        name=target.get("name", "unknown"),
        args=[target["id"]],
        replace_existing=True,
    )
    logger.debug(
        "Scheduled job %s for '%s' every %ds",
        job_id, target.get("name"), interval,
    )


def remove_job(target_id: str) -> None:
    """Remove a target's scheduled job."""
    global _scheduler
    with _lock:
        if _scheduler is None:
            return
        job_id = f"monitor_{target_id}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
            logger.debug("Removed job %s", job_id)


def run_now(target_id: str) -> dict | None:
    """Manually trigger an immediate capture for a target.

    Returns the process_price result dict, or None if target not found.
    """
    target = get_target(target_id)
    if target is None:
        logger.warning("run_now: target not found: %s", target_id)
        return None

    return _execute_capture(target_id)


def _execute_capture(target_id: str) -> dict | None:
    """Execute one full capture cycle for a target.

    Called by APScheduler or manually via run_now.
    """
    from scraper.browser import get_page_text
    from scraper.extractor import extract_fields

    target = get_target(target_id)
    if target is None:
        logger.warning("Capture skipped: target %s not found", target_id)
        return None

    logger.info("Capturing price for '%s': %s", target["name"], target["url"])

    try:
        # Step 1: Fetch page text (try normal methods first)
        page_data = get_page_text(target["url"])

        # Step 2: Check if price was obtained via direct API
        if "_price" in page_data:
            # Direct API hit — no AI extraction needed
            price = page_data["_price"]
            extracted = {"_api_price": price}
            logger.info("Got price via API for '%s': %s", target["name"], price)

        # Check if page looks empty or blocked (JD/Tmall verification pages)
        elif len(page_data.get("text", "")) < 100 or "验证" in page_data.get("text", "")[:50]:
            # Try stealth browser as fallback
            logger.info("Page blocked for '%s', trying stealth browser...", target["name"])
            try:
                from scraper.stealth_browser import stealth_get_page_text
                stealth_data = stealth_get_page_text(target["url"])
                if stealth_data and len(stealth_data.get("text", "")) > 100:
                    page_data = stealth_data
                    logger.info("Stealth browser succeeded for '%s'", target["name"])
            except Exception as se:
                logger.warning("Stealth browser also failed: %s", se)
            
            # Extract via AI
            fields = target.get("fields", [target.get("price_field", "价格")])
            extracted = extract_fields(page_data["text"], fields)
            price_field = target.get("price_field", "价格")
            raw_price = extracted.get(price_field)
            price = normalize_price(raw_price)
        else:
            # Step 2: Extract fields via AI (normal path)
            fields = target.get("fields", [target.get("price_field", "价格")])
            extracted = extract_fields(page_data["text"], fields)
            price_field = target.get("price_field", "价格")
            raw_price = extracted.get(price_field)
            price = normalize_price(raw_price)

        if price is None:
            logger.warning(
                "Could not parse price for '%s': field=%s raw=%s",
                target["name"], price_field, raw_price,
            )
            return None

        # Step 4: Process the price (store + detect changes + alert)
        result = process_price(target_id, price, extracted)
        logger.info(
            "Captured price for '%s': %s (change: %s%%)",
            target["name"], price, result["change_pct"],
        )
        return result

    except Exception as e:
        logger.error("Capture failed for '%s': %s", target["name"], e)
        return None
