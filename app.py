#!/usr/bin/env python3
"""Web UI for the AI web scraper — run with: python app.py"""

import sys
import os
import time

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, url_for, session

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from scraper.browser import get_page_text
from scraper.extractor import extract_fields
from scraper.storage import save_all, save_batch
from scraper.reporter import save_html, save_batch_html
from scraper.scout import find_item_urls
from pricemon.blueprint import bp as monitor_bp
from pricemon.db import init_db
from pricemon.scheduler import init_scheduler

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()  # For session storage

# Initialize price monitoring
init_db()
app.register_blueprint(monitor_bp)
init_scheduler()


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    url = ""
    fields = ""
    mode = "single"

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        fields_raw = request.form.get("fields", "").strip()
        mode = request.form.get("mode", "single")

        if not url:
            error = "请输入要采集的网页URL"
        elif not fields_raw:
            error = "请输入要提取的字段（用逗号分隔）"
        else:
            field_list = [f.strip() for f in fields_raw.replace("，", ",").split(",") if f.strip()]
            fields = ", ".join(field_list)

            try:
                if mode == "auto":
                    result = _run_auto_web(url, field_list)
                else:
                    result = _run_single_web(url, field_list)
                # Store result in session (expires in 10 minutes)
                session["last_result"] = result
                session["last_result_time"] = __import__('time').time()
            except Exception as e:
                error = f"采集失败：{str(e)}"
    else:
        # Check for cached result (10 min expiry)
        import time
        last_result = session.get("last_result")
        last_time = session.get("last_result_time")
        if last_result and last_time and (time.time() - last_time) < 600:
            result = last_result
            url = result.get("url", url)
            fields = ", ".join(result.get("fields", []))
            mode = result.get("mode", mode)

    return render_template("index.html", result=result, error=error,
                           url=url, fields=fields, mode=mode)


def _apply_aliases(extracted: dict, page_data: dict, field_list: list[str]) -> dict:
    """Map user-friendly field names to internal data fields."""
    aliases = {"网址": "_url", "标题": "_title"}
    for user_field, internal_field in aliases.items():
        if user_field in field_list:
            # First try extracted (batch mode adds _url/_title before this call)
            val = extracted.get(internal_field)
            if val is None:
                # Fall back to page_data
                val = page_data.get(internal_field.lstrip("_"), "")
            extracted[user_field] = val if val else ""
    return extracted


def _run_single_web(url: str, field_list: list[str]) -> dict:
    page_data = get_page_text(url)
    extracted = extract_fields(page_data["text"], field_list)
    extracted = _apply_aliases(extracted, page_data, field_list)

    # Dangdang price override: use dedicated extractor for accuracy
    if "dangdang.com" in url:
        from scraper.dangdang_price import extract_dangdang_price
        dd_price = extract_dangdang_price(page_data["text"], url)
        print(f"  [dangdang_price] 提取结果: {dd_price} (AI提取: {extracted.get('价格', '无')})")
        if dd_price:
            for f in field_list:
                if "价" in f:
                    extracted[f] = dd_price
                    break
    saved = save_all(extracted, url, "both")
    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_html(extracted, url, field_list, out_dir)
    saved["html"] = html_path

    # Auto-generate a monitoring target name from scraped data
    title = page_data["title"]
    price_field = "价格"
    for f in field_list:
        if "价" in f or "price" in f.lower():
            price_field = f
            break

    return {
        "mode": "single",
        "title": title,
        "url": url,
        "data": extracted,
        "fields": field_list,
        "count": 1,
        "files": {fmt: os.path.abspath(p) for fmt, p in saved.items()},
        "monitor_add_url": url_for("monitor.add_target_page",
            _external=False) + f"?name={title[:50]}&url={url}&fields={','.join(field_list)}&price_field={price_field}",
    }


def _run_auto_web(url: str, field_list: list[str], limit: int = 20) -> dict:
    items = find_item_urls(url, max_items=limit)
    if not items:
        raise RuntimeError("未在页面中找到商品链接。试试单页模式？")

    all_data = []
    for item in items:
        item_url = item["url"]
        try:
            page_data = get_page_text(item_url)
            extracted = extract_fields(page_data["text"], field_list)
            extracted["_url"] = item_url
            extracted["_title"] = page_data["title"][:80]
            extracted = _apply_aliases(extracted, page_data, field_list)

            # Dangdang price override: use dedicated extractor for accuracy
            if "dangdang.com" in item_url:
                from scraper.dangdang_price import extract_dangdang_price
                dd_price = extract_dangdang_price(page_data["text"], item_url)
                if dd_price:
                    for f in field_list:
                        if "价" in f:
                            extracted[f] = dd_price
                            break

            # Generate monitor URL for each item
            price_field = "价格"
            for f in field_list:
                if "价" in f or "price" in f.lower():
                    price_field = f
                    break
            item_name = (page_data["title"] or item["text"])[:50]
            extracted["_monitor_url"] = url_for("monitor.add_target_page") + \
                f"?name={item_name}&url={item_url}&fields={','.join(field_list)}&price_field={price_field}"

            all_data.append(extracted)
        except Exception:
            fallback = {"_url": item_url, "_title": "[采集失败]",
                       **{f: None for f in field_list}}
            all_data.append(fallback)
        if len(all_data) < len(items):
            time.sleep(1)

    # Duplicate price detection
    _prices = {}
    for _d in all_data:
        for _f in field_list:
            if "价" in _f and _d.get(_f):
                _prices[str(_d[_f])] = _prices.get(str(_d[_f]), 0) + 1
                break
    for _p, _c in sorted(_prices.items(), key=lambda x: -x[1])[:3]:
        if _c >= max(3, len(all_data) * 0.4):
            print(f"  [重复价格警告] {_c}/{len(all_data)} 个商品都是 {_p}")

    saved = save_batch(all_data, url, field_list, "both")
    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_batch_html(all_data, url, field_list, out_dir)
    saved["html"] = html_path

    return {
        "mode": "auto",
        "title": f"批量采集 {len(all_data)} 项",
        "url": url,
        "data": all_data,
        "fields": field_list,
        "files": {fmt: os.path.abspath(p) for fmt, p in saved.items()},
    }


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    fields_raw = data.get("fields", "").strip()
    mode = data.get("mode", "single")

    if not url or not fields_raw:
        return jsonify({"error": "Missing url or fields"}), 400

    field_list = [f.strip() for f in fields_raw.replace("，", ",").split(",") if f.strip()]

    try:
        if mode == "auto":
            result = _run_auto_web(url, field_list)
        else:
            result = _run_single_web(url, field_list)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 网页数据采集工具")
    print("  基于 DeepSeek 智能提取")
    print("=" * 50)
    print("  启动：http://127.0.0.1:5000")
    print("  停止：Ctrl+C")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
