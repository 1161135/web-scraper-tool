#!/usr/bin/env python3
"""AI-powered web data extractor — entry point.

Usage:
    python run.py --url <URL> --fields "字段1,字段2"

"""

import sys
import os

from dotenv import load_dotenv

from scraper.cli import parse_args
from scraper.browser import get_page_text
from scraper.extractor import extract_fields
from scraper.storage import save_all


def main() -> None:
    load_dotenv()

    # Validate API key early
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Error: DEEPSEEK_API_KEY not set. Create a .env file with your key.")
        sys.exit(1)

    args = parse_args()

    print(f"🌐 正在打开页面: {args.url}")
    page_data = get_page_text(args.url)
    print(f"📄 页面标题: {page_data['title']}")
    print(f"📏 页面内容: {len(page_data['text'])} 字符")

    print(f"🤖 AI正在提取字段: {', '.join(args.fields)}")
    extracted = extract_fields(page_data["text"], args.fields)

    print(f"💾 正在保存数据 ({args.output})")
    saved = save_all(extracted, args.url, args.output)

    print("\n✅ 采集完成!")
    print(f"   数据: {extracted}")
    for fmt, path in saved.items():
        print(f"   {fmt.upper()}: {os.path.abspath(path)}")


if __name__ == "__main__":
    main()
