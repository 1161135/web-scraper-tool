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
    print("  LOGIN MODE")
    print("=" * 50)
    print("  A browser window will open.")
    print("  1. Go to taobao.com and log in manually")
    print("  2. After login, come back to this terminal")
    print("  3. Press ENTER to save session and continue")
    print("=" * 50)

    with sync_playwright() as pw:
        # Try system Edge or Chrome
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = pw.chromium.launch(
                        headless=False, channel=channel
                    )
                else:
                    browser = pw.chromium.launch(headless=False)
                break
            except Exception:
                continue

        if browser is None:
            print("ERROR: No browser found. Install Edge or Chrome.")
            return False

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
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


def login_jd() -> bool:
    """Open a visible browser for the user to log into JD.com."""
    from playwright.sync_api import sync_playwright

    print("=" * 50)
    print("  LOGIN MODE - JD.com")
    print("=" * 50)
    print("  A browser window will open.")
    print("  1. Go to jd.com and log in manually")
    print("  2. After login, press ENTER to save session")
    print("=" * 50)

    with sync_playwright() as pw:
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = pw.chromium.launch(headless=False, channel=channel)
                else:
                    browser = pw.chromium.launch(headless=False)
                break
            except Exception:
                continue

        if browser is None:
            print("ERROR: No browser found.")
            return False

        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto("https://www.jd.com", wait_until="networkidle")

        input("  Press ENTER after you've logged in...")

        save_storage_state(context)
        browser.close()
        print("  JD.com session saved!")
        return True
