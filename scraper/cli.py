"""Command-line argument parsing for web-scraper."""

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Namespace with .url (str), .fields (list[str]), .output (str),
        .auto (bool), .limit (int)

    """
    parser = argparse.ArgumentParser(
        description="AI-powered web data extractor",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Target page URL (product detail or search/list page)",
    )
    parser.add_argument(
        "--fields",
        required=True,
        help="Comma-separated field names (e.g. 名称,价格,描述)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-detect and batch-collect items from a list/search page",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max items to collect in auto mode (default: 5)",
    )

    ns = parser.parse_args(argv)
    ns.fields = [f.strip() for f in ns.fields.split(",") if f.strip()]

    if not ns.fields:
        parser.error("At least one field must be specified in --fields")

    return ns
