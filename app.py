#!/usr/bin/env python3
"""Web UI for the AI web scraper — run with: python app.py"""

import sys
import os
import time

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from scraper.browser import get_page_text
from scraper.extractor import extract_fields
from scraper.storage import save_all, save_batch
from scraper.reporter import save_html, save_batch_html
from scraper.scout import find_item_urls

app = Flask(__name__)


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
            field_list = [f.strip() for f in fields_raw.split(",") if f.strip()]
            fields = ", ".join(field_list)

            try:
                if mode == "auto":
                    result = _run_auto_web(url, field_list)
                else:
                    result = _run_single_web(url, field_list)
            except Exception as e:
                error = f"采集失败：{str(e)}"

    return render_template("index.html", result=result, error=error,
                           url=url, fields=fields, mode=mode)


def _run_single_web(url: str, field_list: list[str]) -> dict:
    page_data = get_page_text(url)
    extracted = extract_fields(page_data["text"], field_list)
    saved = save_all(extracted, url, "both")
    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_html(extracted, url, field_list, out_dir)
    saved["html"] = html_path
    return {
        "mode": "single",
        "title": page_data["title"],
        "url": url,
        "data": extracted,
        "count": 1,
        "files": {fmt: os.path.abspath(p) for fmt, p in saved.items()},
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
            all_data.append(extracted)
        except Exception:
            all_data.append({"_url": item_url, "_title": "[采集失败]",
                           **{f: None for f in field_list}})
        if len(all_data) < len(items):
            time.sleep(1)

    saved = save_batch(all_data, url, field_list, "both")
    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_batch_html(all_data, url, field_list, out_dir)
    saved["html"] = html_path

    return {
        "mode": "auto",
        "title": f"批量采集 {len(all_data)} 项",
        "url": url,
        "data": all_data,
        "count": len(all_data),
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

    field_list = [f.strip() for f in fields_raw.split(",") if f.strip()]

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
