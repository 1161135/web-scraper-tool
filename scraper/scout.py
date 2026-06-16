"""AI Scout — analyzes a list page and finds item detail links.

Strategy:
1. Fetch all links from the list page via Playwright (or requests fallback)
2. Use heuristics to identify likely product links (URL pattern + text analysis)
3. Sort by relevance score
4. Return top N item URLs
"""

import re
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ===== Public API =====

def find_item_urls(url: str, max_items: int = 20) -> list[dict]:
    """Find item/product detail URLs on a list page.

    Args:
        url: The list/search page URL.
        max_items: Maximum number of item URLs to return.

    Returns:
        List of dicts: {url, text, score} sorted by score descending.
    """
    all_links = _fetch_page_links(url)

    if not all_links:
        raise RuntimeError(f"No links found on page: {url}")

    page_domain = urlparse(url).netloc

    for link in all_links:
        link["score"] = _score_link(link, page_domain)

    scored = sorted(all_links, key=lambda l: l["score"], reverse=True)

    seen_urls = set()
    result = []
    for link in scored:
        href = link["href"]
        clean_url = href.split("?")[0] if "?" in href else href

        if clean_url not in seen_urls and link["score"] > 10:
            seen_urls.add(clean_url)
            result.append({
                "url": href,
                "text": link["text"][:80],
                "score": link["score"],
            })
            if len(result) >= max_items:
                break

    return result


# ===== Link fetching (Playwright, fallback requests) =====

def _fetch_page_links(url: str) -> list[dict]:
    """Try Playwright first, fall back to requests."""
    try:
        return _fetch_with_playwright(url)
    except Exception:
        pass
    return _fetch_with_requests(url)


def _fetch_with_playwright(url: str) -> list[dict]:
    """Use Playwright (with saved session) to fetch page links."""
    import time as _time
    from playwright.sync_api import sync_playwright
    from scraper.login import load_storage_state

    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        if browser is None:
            raise RuntimeError("No browser available")

        saved_state = load_storage_state()
        ctx = browser.new_context(storage_state=saved_state) if saved_state else browser.new_context()
        page = ctx.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        _time.sleep(3)

        # Wait for product containers to render
        for sel in [".s-card", "[id^='item']", ".items", ".item",
                     "[class*='product']", "[class*='goods']",
                     "#mainsrp-itemlist"]:
            try:
                page.wait_for_selector(sel, timeout=3000)
                break
            except Exception:
                continue

        # Extract links using multiple strategies
        links = page.evaluate("""() => {
            const items = [];
            const seen = new Set();
            const add = (href, text) => {
                if (!href || !text || text.length < 4) return;
                const key = href + '|' + text;
                if (seen.has(key)) return;
                seen.add(key);
                items.push({href, text: text.substring(0, 80)});
            };

            // All visible links
            document.querySelectorAll('a[href]').forEach(a => {
                add(a.href.trim(), (a.innerText || '').trim());
            });

            // eBay: product cards li[id^="item"] > a[href*="/itm/"]
            document.querySelectorAll('li[id^="item"] a[href*="/itm/"]').forEach(a => {
                add(a.href.trim(), (a.innerText || '').trim());
            });

            // Taobao: data-id attributes
            document.querySelectorAll('[data-id]').forEach(el => {
                const id = el.getAttribute('data-id');
                if (id && id.match(/^\\d+$/)) {
                    add('https://item.taobao.com/item.htm?id=' + id, (el.innerText || '').trim());
                }
            });

            return items;
        }""")

        browser.close()
        return links


def _launch_browser(pw):
    """Try Edge, Chrome, then bundled Chromium."""
    for channel in ["msedge", "chrome", None]:
        try:
            kwargs = {"headless": True}
            if channel:
                kwargs["channel"] = channel
            return pw.chromium.launch(**kwargs)
        except Exception:
            continue
    return None


def _fetch_with_requests(url: str) -> list[dict]:
    """Fallback: HTTP requests + BeautifulSoup."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Edge/120.0.0.0 Safari/537.36"
        ),
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True)
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            continue
        if len(text) < 4:
            continue
        abs_url = urljoin(url, href)
        key = (abs_url, text)
        if key in seen:
            continue
        seen.add(key)
        links.append({"href": abs_url, "text": text.strip()})

    return links


# ===== Scorer =====

def _is_product_url(url: str) -> bool:
    patterns = [
        r"/product/", r"/item/", r"/itm/", r"/dp/", r"/detail/",
        r"/goods/", r"/sku/", r"/prod", r"-p-", r"/p/",
        r"item\.taobao\.com", r"detail\.tmall\.com",
    ]
    return any(re.search(p, url, re.IGNORECASE) for p in patterns)


def _score_link(link: dict, page_domain: str) -> int:
    url = link["href"]
    text = link["text"]
    score = 0

    if _is_product_url(url):
        score += 30
    if 8 <= len(text) <= 60:
        score += 15
    if re.search(r'[\u4e00-\u9fff]', text):
        score += 10

    link_domain = urlparse(url).netloc
    page_main = ".".join(urlparse(page_domain).netloc.split(".")[-2:]) if "." in page_domain else page_domain
    link_main = ".".join(link_domain.split(".")[-2:]) if "." in link_domain else link_domain
    if link_main == page_main:
        score += 5

    nav_kw = ["首页", "下一页", "上一页", "搜索", "登录", "注册",
              "购物车", "我的订单", "帮助", "分类", "品牌",
              "homepage", "sign in", "register", "cart"]
    for kw in nav_kw:
        if kw.lower() in text.lower():
            score -= 20

    if re.match(r'^\d+条?评?论?$', text):
        score -= 30

    return score
