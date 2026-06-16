"""Page text extraction — uses Playwright (real browser) first,
falls back to HTTP requests when Playwright is unavailable."""

import requests
from bs4 import BeautifulSoup


def _requests_text(url: str, timeout: int) -> dict:
    """Fallback: fetch page text via HTTP requests + BeautifulSoup."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Edge/120.0.0.0 Safari/537.36"
        ),
    }
    resp = requests.get(url, headers=headers, timeout=timeout / 1000)
    resp.encoding = resp.apparent_encoding or "utf-8"
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url
    body_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in body_text.split("\n") if l.strip()]
    clean_text = "\n".join(lines)

    return {
        "title": title,
        "text": clean_text[:8000],
        "url": url,
    }


def _playwright_text(url: str, timeout: int) -> dict:
    """Primary: fetch page text via Playwright (real browser).
    Handles JavaScript-rendered pages."""
    from playwright.sync_api import sync_playwright
    from scraper.login import load_storage_state

    # Try system Edge first, then Chrome, then Playwright's bundled Chromium
    browser = None
    with sync_playwright() as pw:
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = pw.chromium.launch(
                        headless=True, channel=channel
                    )
                else:
                    browser = pw.chromium.launch(headless=True)
                break  # Successfully launched
            except Exception:
                continue  # Try next channel

        if browser is None:
            raise RuntimeError("No usable browser found. Install Edge or Chrome, or run: playwright install chromium")

        # Use saved login session if available
        saved_state = load_storage_state()
        if saved_state:
            context = browser.new_context(
                storage_state=saved_state,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Edge/120.0.0.0 Safari/537.36"
                ),
            )
        else:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Edge/120.0.0.0 Safari/537.36"
                ),
            )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout)

        title = page.title()

        # Extract visible text
        body_text = page.evaluate("""() => {
            const clone = document.body.cloneNode(true);
            clone.querySelectorAll('script, style, noscript, svg')
                .forEach(el => el.remove());
            return clone.innerText;
        }""")

        lines = [l.strip() for l in body_text.split("\n") if l.strip()]
        clean_text = "\n".join(lines)

        browser.close()

        return {
            "title": title,
            "text": clean_text[:8000],
            "url": url,
        }


def _get_page_text_playwright(url: str, timeout: int = 30000) -> dict:
    """Try Playwright first, return None if unavailable."""
    try:
        return _playwright_text(url, timeout)
    except Exception as e:
        # Suppress Playwright errors in auto mode — will fall back to requests
        return None


def get_page_text(url: str, timeout: int = 30000, prefer: str = "auto") -> dict:
    """Open a URL and extract visible text content.

    Args:
        url: Target webpage URL.
        timeout: Request timeout in ms (default 30s for Playwright, 15s for requests).
        prefer: 'playwright' to force browser, 'requests' to force HTTP,
                'auto' to try Playwright first, fall back to requests.

    Returns:
        Dict with keys: title, text, url.

    Raises:
        RuntimeError: If page fails to load.

    """
    if prefer == "playwright" or prefer == "auto":
        result = _get_page_text_playwright(url, timeout)
        if result is not None:
            return result
        if prefer == "playwright":
            raise RuntimeError(
                f"Playwright failed to load page: {url}. "
                "Try installing Playwright browsers: playwright install chromium"
            )

    # Fallback to requests
    try:
        # Use shorter timeout for requests (15s vs 30s)
        return _requests_text(url, timeout=min(timeout, 15000))
    except Exception as e:
        raise RuntimeError(f"Failed to load page: {url}") from e
