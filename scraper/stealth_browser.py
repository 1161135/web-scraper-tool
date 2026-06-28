"""Stealth browser — uses Playwright with advanced anti-detection measures.
Fixes京东/天猫等网站检测自动化浏览器的问题.

Usage:
    from scraper.stealth_browser import stealth_get_page_text
    result = stealth_get_page_text('https://item.jd.com/xxx.html')
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def stealth_get_page_text(url: str, timeout: int = 30000) -> dict | None:
    """Fetch page text using Playwright with advanced stealth measures."""
    from playwright.sync_api import sync_playwright
    from scraper.login import load_storage_state

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-sandbox", "--disable-setuid-sandbox",
        "--disable-infobars", "--disable-notifications",
    ]

    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ]});
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    window.chrome = { runtime: {} };
    """

    try:
        with sync_playwright() as pw:
            browser = None
            for channel in ["msedge", "chrome", None]:
                try:
                    kwargs = {"headless": True, "args": launch_args}
                    if channel:
                        kwargs["channel"] = channel
                    browser = pw.chromium.launch(**kwargs)
                    break
                except Exception:
                    continue
            if browser is None:
                raise RuntimeError("No browser found")

            saved_state = load_storage_state()
            ctx_kw = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080},
                "locale": "zh-CN",
                "timezone_id": "Asia/Shanghai",
            }
            if saved_state:
                ctx_kw["storage_state"] = saved_state
            context = browser.new_context(**ctx_kw)

            page = context.new_page()
            page.add_init_script(stealth_js)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            time.sleep(3)

            title = page.title()
            body_text = page.evaluate("""() => {
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll('script,style,noscript,svg,iframe').forEach(el => el.remove());
                return clone.innerText;
            }""")
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            browser.close()
            return {"title": title, "text": "\n".join(lines)[:10000], "url": url}
    except Exception as e:
        logger.warning("Stealth browser failed for %s: %s", url, e)
        return None
