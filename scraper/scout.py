"""AI Scout — analyzes a list page and finds item detail links.

Strategy:
1. Fetch all links from the list page
2. Use heuristics to identify likely product links (URL pattern + text analysis)
3. Sort by relevance score
4. Return top N item URLs
"""

import re
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def _fetch_page_links(url: str) -> list[dict]:
    """Fetch a page and extract all links with their text context.

    Returns list of {href, text} dicts.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
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

        links.append({
            "href": abs_url,
            "text": text.strip(),
        })

    return links


def _is_product_url(url: str) -> bool:
    """Heuristic: check if URL looks like a product detail page."""
    product_patterns = [
        r"/product/", r"/item/", r"/dp/", r"/detail/",
        r"/goods/", r"/sku/", r"/prod", r"-p-", r"/p/",
    ]
    for pattern in product_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def _score_link(link: dict, page_domain: str) -> int:
    """Score a link's likelihood of being a product page (higher = more likely)."""
    url = link["href"]
    text = link["text"]
    score = 0

    # Product URL patterns (strong signal)
    if _is_product_url(url):
        score += 30

    # Link text looks like a product name (8-60 chars, not a short label)
    if 8 <= len(text) <= 60:
        score += 15

    # Link text contains Chinese characters (product names)
    if re.search(r'[\u4e00-\u9fff]', text):
        score += 10

    # Same domain as list page (likely same site's products)
    link_domain = urlparse(url).netloc
    page_main = ".".join(urlparse(page_domain).netloc.split(".")[-2:]) if "." in page_domain else page_domain
    link_main = ".".join(link_domain.split(".")[-2:]) if "." in link_domain else link_domain
    if link_main == page_main:
        score += 5

    # Penalty: link text contains navigation keywords
    nav_keywords = ["首页", "下一页", "上一页", "搜索", "登录", "注册",
                    "购物车", "我的订单", "帮助", "分类", "品牌"]
    for kw in nav_keywords:
        if kw in text:
            score -= 20

    # Penalty: link text is a number-only or very short review count
    if re.match(r'^\d+条?评?论?$', text):
        score -= 30

    return score


def find_item_urls(url: str, max_items: int = 10) -> list[str]:
    """Find item/product detail URLs on a list page using heuristics.

    Args:
        url: The list/search page URL.
        max_items: Maximum number of item URLs to return.

    Returns:
        List of item detail page URLs.
    """
    all_links = _fetch_page_links(url)

    if not all_links:
        raise RuntimeError(f"No links found on page: {url}")

    page_domain = urlparse(url).netloc

    # Score and sort links
    for link in all_links:
        link["score"] = _score_link(link, page_domain)

    scored = sorted(all_links, key=lambda l: l["score"], reverse=True)

    # Take top scoring links, but skip duplicates
    seen_urls = set()
    result = []
    for link in scored:
        href = link["href"]
        # Clean tracking params for dedup
        clean_url = href.split("?")[0] if "?" in href else href

        if clean_url not in seen_urls and link["score"] > 10:
            seen_urls.add(clean_url)
            result.append(href)
            if len(result) >= max_items:
                break

    return result
