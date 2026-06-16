#!/usr/bin/env python3
"""AI-powered web data extractor — entry point.

Usage:
    # Single product page
    python run.py --url <URL> --fields "字段1,字段2"

    # Batch: auto-detect items from a list/search page
    python run.py --url <LIST_URL> --fields "字段1,字段2" --auto --limit 10

"""

import sys
import os
import time

# Force UTF-8 output for Chinese characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
elif hasattr(sys, "setdefaultencoding"):
    reload(sys)
    sys.setdefaultencoding("utf-8")

from dotenv import load_dotenv

from scraper.cli import parse_args
from scraper.browser import get_page_text
from scraper.extractor import extract_fields
from scraper.storage import save_all, save_batch
from scraper.reporter import save_html, save_batch_html
from scraper.scout import find_item_urls
from scraper.login import login_taobao, login_jd, clear_session, has_session


def main() -> None:
    load_dotenv()

    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Error: DEEPSEEK_API_KEY not set. Create a .env file with your key.")
        sys.exit(1)

    args = parse_args()

    # Handle login/clear-session commands
    if args.clear_session:
        clear_session()
        print("Session cleared.")
        return

    if args.login:
        print("Which platform do you want to log into?")
        print("  1. Taobao (淘宝)")
        print("  2. JD.com (京东)")
        choice = input("Enter 1 or 2: ").strip()
        if choice == "2":
            login_jd()
        else:
            login_taobao()
        return

    if args.auto:
        _run_auto(args)
    else:
        _run_single(args)


def _run_single(args) -> None:
    """Original mode: extract fields from a single product page."""
    print(f"[URL] {args.url}")
    page_data = get_page_text(args.url)
    print(f"[TITLE] {page_data['title']}")
    print(f"[TEXT] {len(page_data['text'])} chars")

    print(f"[AI] Extracting fields: {', '.join(args.fields)}")
    extracted = extract_fields(page_data["text"], args.fields)

    print(f"[SAVE] Saving data ({args.output})")
    saved = save_all(extracted, args.url, args.output)

    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_html(extracted, args.url, args.fields, out_dir)
    saved["html"] = html_path

    print("\n[DONE] Extraction complete!")
    print(f"   Data: {extracted}")
    for fmt, path in saved.items():
        print(f"   {fmt.upper()}: {os.path.abspath(path)}")


def _run_auto(args) -> None:
    """Auto mode: find items on list page and batch-collect data."""
    print("=" * 50)
    print("  LIST PAGE MODE (--auto)")
    print(f"  URL: {args.url}")
    print(f"  Fields: {', '.join(args.fields)}")
    print(f"  Max items: {args.limit}")
    print("=" * 50)

    # Step 1: Find item URLs on the list page
    print(f"\n[1/3] Scanning list page for item links...")
    items = find_item_urls(args.url, max_items=args.limit)

    if not items:
        print("  No item links found. Try without --auto for single-page mode.")
        sys.exit(1)

    print(f"  Found {len(items)} items (score=confidence level):")
    print(f"  {'#':>3}  {'Score':>5}  {'Product Name':<40}  URL")
    print(f"  {'-'*3}  {'-'*5}  {'-'*40}  {'-'*50}")
    for i, item in enumerate(items, 1):
        name = item["text"][:38]
        print(f"  {i:>3}  {item['score']:>5}  {name:<40}  {item['url']}")

    # Step 2: Extract fields from each item
    print(f"\n[2/3] Extracting data from {len(items)} items...")
    all_data = []
    for i, item in enumerate(items, 1):
        url = item["url"]
        try:
            print(f"  [{i}/{len(items)}] {item['text'][:40]:40s} ", end="")
            page_data = get_page_text(url)
            extracted = extract_fields(page_data["text"], args.fields)
            extracted["_url"] = url
            extracted["_title"] = page_data["title"][:80]
            all_data.append(extracted)
            print(f"OK")
        except Exception as e:
            print(f"FAILED: {e}")
            all_data.append({"_url": url, "_title": "[FAILED]", **{f: None for f in args.fields}})

        # Small delay between requests
        if i < len(items):
            time.sleep(1)

    # Step 3: Save combined results
    print(f"\n[3/3] Saving {len(all_data)} items...")
    saved = save_batch(all_data, args.url, args.fields, args.output)

    out_dir = os.path.dirname(next(iter(saved.values())))
    html_path = save_batch_html(all_data, args.url, args.fields, out_dir)
    saved["html"] = html_path

    print("\n[DONE] Batch collection complete!")
    print(f"  Total items: {len(all_data)}")
    for fmt, path in saved.items():
        print(f"  {fmt.upper()}: {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
