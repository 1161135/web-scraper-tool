#!/usr/bin/env python3
"""Web UI for the AI web scraper — run with: python app.py"""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

# Ensure we can import scraper modules
sys.path.insert(0, os.path.dirname(__file__))

from scraper.browser import get_page_text
from scraper.extractor import extract_fields
from scraper.storage import save_all
from scraper.reporter import save_html

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    url = ""
    fields = ""

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        fields_raw = request.form.get("fields", "").strip()

        if not url:
            error = "请输入要采集的网页URL"
        elif not fields_raw:
            error = "请输入要提取的字段（用逗号分隔）"
        else:
            field_list = [f.strip() for f in fields_raw.split(",") if f.strip()]
            fields = ", ".join(field_list)

            try:
                # Step 1: Fetch page
                page_data = get_page_text(url)

                # Step 2: AI extraction
                extracted = extract_fields(page_data["text"], field_list)

                # Step 3: Save data
                saved = save_all(extracted, url, "both")

                # Step 4: Generate HTML report
                out_dir = os.path.dirname(next(iter(saved.values())))
                html_path = save_html(extracted, url, field_list, out_dir)
                saved["html"] = html_path

                result = {
                    "title": page_data["title"],
                    "url": url,
                    "data": extracted,
                    "files": {fmt: os.path.abspath(p) for fmt, p in saved.items()},
                }

            except Exception as e:
                error = f"采集失败：{str(e)}"

    return render_template("index.html", result=result, error=error, url=url, fields=fields)


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """JSON API endpoint for programmatic use."""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    fields_raw = data.get("fields", "").strip()

    if not url or not fields_raw:
        return jsonify({"error": "Missing url or fields"}), 400

    field_list = [f.strip() for f in fields_raw.split(",") if f.strip()]

    try:
        page_data = get_page_text(url)
        extracted = extract_fields(page_data["text"], field_list)
        saved = save_all(extracted, url, "both")
        out_dir = os.path.dirname(next(iter(saved.values())))
        html_path = save_html(extracted, url, field_list, out_dir)

        return jsonify({
            "success": True,
            "title": page_data["title"],
            "data": extracted,
            "files": {fmt: os.path.abspath(p) for fmt, p in saved.items()},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 网页数据采集工具 - Web 界面")
    print("=" * 50)
    print(f"  打开浏览器访问：http://127.0.0.1:5000")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
