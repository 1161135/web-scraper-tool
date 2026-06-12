"""Page text extraction — tries Playwright first, falls back to HTTP requests."""

import re

import requests
from bs4 import BeautifulSoup


def _extract_text_from_html(html: str, url: str) -> dict:
    """Extract visible text from HTML using BeautifulSoup.

    Returns dict with keys: title, text, url.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer, header tags
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url

    # Get text and clean whitespace
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    clean_text = "\n".join(lines)

    return {
        "title": title,
        "text": clean_text[:8000],
        "url": url,
    }


def get_page_text(url: str, timeout: int = 15000) -> dict:
    """Open a URL and extract visible text content.

    Uses HTTP (requests + BeautifulSoup) for fast extraction.
    For JavaScript-rendered pages, Playwright can be used.

    Args:
        url: Target webpage URL.
        timeout: Request timeout in ms.

    Returns:
        Dict with keys: title, text, url.

    Raises:
        RuntimeError: If page fails to load.

    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        resp = requests.get(url, headers=headers, timeout=timeout / 1000)
        resp.raise_for_status()

        # Detect encoding
        resp.encoding = resp.apparent_encoding or "utf-8"

        return _extract_text_from_html(resp.text, url)

    except Exception as e:
        raise RuntimeError(f"Failed to load page: {url}") from e
