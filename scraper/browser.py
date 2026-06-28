"""Page text extraction — uses Playwright (real browser) first,
falls back to HTTP requests when Playwright is unavailable.

Also supports direct price API lookups for JD.com and Tmall."""

import os
import re
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
        "text": _normalize_dangdang_prices(clean_text[:8000], url),
        "url": url,
    }


def _normalize_dangdang_prices(text: str, url: str) -> str:
    """Pre-process dangdang page text to normalize price labels for AI extraction."""
    if "dangdang.com" not in url:
        return text
    
    # Only process main product area, truncate at recommendations
    main_text = text
    for marker in ["为你推荐", "同类图书排行榜", "读了这本书的人还在读", "买过这本书的人还买过"]:
        idx = text.find(marker)
        if idx > 0:
            main_text = text[:idx]
            break
    
    is_ebook = "e.dangdang.com" in url
    
    # ── Extract 纸质售价 value for exclusion ──
    paper_price = None
    pm = re.search(r'纸质售价[^。\n]*?¥?\s*([\d,]+\.\d{2})', main_text)
    if pm:
        paper_price = pm.group(1)
    
    # ── Rule 1: Handle "售价+纸质售价" on the same line (both together) ──
    main_text = re.sub(
        r'售\s*价\s*[：:]\s*¥?\s*([\d,]+\.\d{2})\s*纸质售价[^。\n]*?¥?\s*[\d,]+\.?\d*',
        r'价格：¥\1',
        main_text
    )
    
    # ── Rule 2: For ebooks, find "价：¥59.00" (price with partial label) ──
    if is_ebook:
        lines = main_text.split('\n')
        for i, line in enumerate(lines):
            m = re.search(r'价\s*[：:]\s*¥\s*([\d,]+\.\d{2})', line)
            if m:
                price_val = m.group(1)
                if price_val != paper_price:
                    lines[i] = f'价格：¥{price_val}'
                    break
        main_text = '\n'.join(lines)
    
    # ── Rule 3: Handle standalone "售       价：¥59.00" ──
    main_text = re.sub(
        r'售\s*价\s*[：:]\s*¥?\s*([\d,]+\.\d{2})',
        r'价格：¥\1',
        main_text
    )
    
    # ── Rule 4: Handle "促销价:¥4.99 | ¥27.99" ──
    main_text = re.sub(
        r'促销\s*价\s*[：:]\s*¥?\s*([\d,]+\.?\d*)\s*[|｜].*?(?:¥?\s*[\d,]+\.?\d*)',
        r'价格：¥\1',
        main_text
    )
    
    # ── Rule 5: Handle standalone "促销价 ¥4.99" / "特价 ¥10.00" ──
    for pattern in [r'促销\s*价', r'特\s*价']:
        main_text = re.sub(
            rf'{pattern}\s*[：:]?\s*¥?\s*([\d,]+\.?\d*)',
            r'价格：¥\1',
            main_text
        )
    
    # Recombine: normalized main area + original footer content
    for marker in ["为你推荐", "同类图书排行榜", "读了这本书的人还在读", "买过这本书的人还买过"]:
        idx = text.find(marker)
        if idx > 0:
            return main_text + text[idx:]
    
    return main_text


def _playwright_text(url: str, timeout: int) -> dict:
    """Primary: fetch page text via Playwright (real browser).
    Handles JavaScript-rendered pages."""
    from playwright.sync_api import sync_playwright
    from scraper.login import load_storage_state

    # Try system Edge first, then Chrome, then Playwright's bundled Chromium
    browser = None
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-sandbox",
        "--disable-setuid-sandbox",
    ]
    with sync_playwright() as pw:
        for channel in ["msedge", "chrome", None]:
            try:
                kwargs = {"headless": True, "args": launch_args}
                if channel:
                    kwargs["channel"] = channel
                browser = pw.chromium.launch(**kwargs)
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
                    "Chrome/130.0.0.0 Safari/537.36"
                ),
            )
        else:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36"
                ),
            )
        page = context.new_page()
        # Hide automation from detection
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            window.chrome = { runtime: {} };
        """)
        page.goto(url, wait_until="networkidle", timeout=timeout)
        # Extra wait for dynamic content
        import time as _time
        _time.sleep(2)

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
            "text": _normalize_dangdang_prices(clean_text[:8000], url),
            "url": url,
        }


def _get_page_text_playwright(url: str, timeout: int = 30000) -> dict:
    """Try Playwright first, return None if unavailable."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        return _playwright_text(url, timeout)
    except Exception as e:
        # Log the actual Playwright error instead of swallowing it
        logger.warning("Playwright failed for %s: %s", url, e)
        print(f"[Playwright Error] {url}: {e}")
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
    # For known e-commerce platforms (JD, Tmall), try direct price API first
    api_result = _try_price_api(url)
    if api_result is not None:
        return api_result

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


def _try_price_api(url: str) -> dict | None:
    """Try fetching price from e-commerce platform APIs directly.

    Supports JD.com (p.3.cn, item-soa.jd.com) and Tmall (mdskip.taobao.com).
    Respects HTTP_PROXY/HTTPS_PROXY environment variables.
    Returns None if not applicable or API fails.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
    }
    # Respect system proxy settings
    proxies = {}
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        if var in os.environ:
            proxies[var.lower().rstrip("s") + "s"] = os.environ[var]
            break

    # ── Dangdang e-book: https://e.dangdang.com/products/PRODUCT_ID.html ──
    dd_match = re.search(r"e\.dangdang\.com/products/(\d+)\.html", url)
    if dd_match:
        product_id = dd_match.group(1)
        try:
            api_url = f"https://e.dangdang.com/api/product/info?productId={product_id}"
            resp = requests.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
                "Referer": f"https://e.dangdang.com/products/{product_id}.html",
            }, timeout=10, proxies=proxies or None)
            resp.raise_for_status()
            data = resp.json()
            price = None
            if isinstance(data, dict):
                price = data.get("data", {}).get("price") or data.get("price") or data.get("salePrice")
            if price:
                return {
                    "title": f"当当电子书 {product_id}",
                    "text": f"当当电子书标题\n售价: {price}\n",
                    "url": url,
                    "_price": float(price),
                }
        except Exception:
            pass

    # ── JD.com: https://item.jd.com/PRODUCT_ID.html ──
    jd_match = re.search(r"item\.jd\.com/(\d+)\.html", url)
    if jd_match:
        sku = jd_match.group(1)
        # Try multiple JD price APIs
        for api_url in [
            f"https://p.3.cn/prices/mgets?skuIds=J_{sku}",
            f"https://item-soa.jd.com/getMainSkuInfo?skuId={sku}",
        ]:
            try:
                resp = requests.get(api_url, headers=headers, timeout=10, proxies=proxies or None)
                resp.raise_for_status()
                data = resp.json()
                price = None
                if isinstance(data, list) and "p" in data[0]:
                    price = data[0]["p"]
                elif isinstance(data, dict):
                    price = data.get("price", {}).get("price") or data.get("jdPrice", {}).get("p")
                if price:
                    return {
                        "title": f"京东商品 {sku}",
                        "text": f"京东商品标题\n价格: {price}\n",
                        "url": url,
                        "_price": float(price),
                    }
            except Exception:
                continue

    # ── Tmall: https://detail.tmall.com/item.htm?id=XXXX ──
    tmall_match = re.search(r"(?:detail\.tmall|item\.taobao)\.com/.*[?&]id=(\d+)", url)
    if tmall_match:
        item_id = tmall_match.group(1)
        try:
            api_url = f"https://mdskip.taobao.com/core/initItemDetail.htm?itemId={item_id}"
            resp = requests.get(api_url, headers=headers, timeout=10, proxies=proxies or None)
            resp.raise_for_status()
            data = resp.json()
            # Extract price from the response
            price = None
            if "itemPriceResultDO" in data:
                price = data["itemPriceResultDO"].get("priceInfo", {}).get("price")
            elif "apiStack" in data:
                for stack in data.get("apiStack", []):
                    if "price" in str(stack.get("data", "")):
                        import json as _json
                        try:
                            d = _json.loads(stack["data"]) if isinstance(stack["data"], str) else stack["data"]
                            price = d.get("price", {}).get("price")
                        except Exception:
                            pass
            if price:
                return {
                    "title": f"天猫商品 {item_id}",
                    "text": f"天猫商品标题\n价格: {price}\n",
                    "url": url,
                    "_price": float(price),
                }
        except Exception:
            pass

    return None
