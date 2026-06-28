"""Login handler — opens a browser for manual login, saves session for later use."""

import os
import json
from pathlib import Path

SESSION_FILE = Path(__file__).parent.parent / ".browser_session.json"


def save_storage_state(context) -> None:
    """Save browser storage state (cookies, localStorage) to file."""
    state = context.storage_state()
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"  Session saved to {SESSION_FILE}")


def load_storage_state() -> dict | None:
    """Load previously saved storage state."""
    if SESSION_FILE.exists():
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def has_session() -> bool:
    """Check if a saved session exists."""
    return SESSION_FILE.exists()


def clear_session() -> None:
    """Delete saved session."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("  Session cleared.")


def login_taobao() -> bool:
    """Open a visible browser for the user to log into Taobao.

    Returns True if login was successful, False otherwise.
    """
    from playwright.sync_api import sync_playwright

    print("=" * 50)
    print("  LOGIN MODE - Taobao")
    print("=" * 50)
    print("  A browser window will open.")
    print("  1. Go to taobao.com and log in manually")
    print("  2. After login, come back to this terminal")
    print("  3. Press ENTER to save session and continue")
    print("=" * 50)

    with sync_playwright() as pw:
        browser = _launch_stealth_browser(pw, headless=False)
        if browser is None:
            print("ERROR: No browser found. Install Edge or Chrome.")
            return False

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
        )
        page = _stealth_page(context)
        page.goto("https://www.taobao.com", wait_until="networkidle")

        input("  Press ENTER after you've logged in...")

        # Check if login was successful
        current_url = page.url
        if "login" in current_url.lower():
            print("  It seems you haven't logged in yet. Try again?")
            retry = input("  Press ENTER to retry, type 'skip' to save anyway: ")
            if retry.lower() != "skip":
                browser.close()
                return False

        # Save session
        save_storage_state(context)
        browser.close()
        print("  Login session saved! You can now scrape Taobao data.")
        return True


def _launch_stealth_browser(pw, headless: bool = False):
    """Launch browser with anti-detection measures."""
    browser = None
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-web-security",
        "--no-sandbox",
        "--disable-setuid-sandbox",
    ]
    for channel in ["msedge", "chrome", None]:
        try:
            kwargs = {"headless": headless, "args": launch_args}
            if channel:
                kwargs["channel"] = channel
            browser = pw.chromium.launch(**kwargs)
            break
        except Exception:
            continue
    return browser


def _stealth_page(context):
    """Create a page with stealth scripts to hide automation."""
    page = context.new_page()
    # Override webdriver detection
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
        window.chrome = { runtime: {} };
    """)
    return page


def login_jd() -> bool:
    """Open a visible browser for the user to log into JD.com."""
    from playwright.sync_api import sync_playwright

    print("=" * 50)
    print("  LOGIN MODE - JD.com")
    print("=" * 50)
    print("  A browser window will open.")
    print("  1. Log into JD.com in the browser")
    print("  2. After login, come back to this terminal")
    print("  3. Press ENTER to save session")
    print("=" * 50)

    with sync_playwright() as pw:
        browser = _launch_stealth_browser(pw, headless=False)
        if browser is None:
            print("ERROR: No browser found. Install Edge or Chrome.")
            return False

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
        )
        page = _stealth_page(context)
        page.goto("https://passport.jd.com/new/login.aspx", wait_until="networkidle")
        print("  Please log into JD.com using QR code or account...")

        input("  Press ENTER after you've logged in...")

        save_storage_state(context)
        browser.close()
        print("  JD.com session saved!")
        return True
