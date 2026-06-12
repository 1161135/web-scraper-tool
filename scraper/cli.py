"""Command-line argument parsing for web-scraper."""

import argparse
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Namespace with .url (str), .fields (list[str]), .output (str)

    """
    parser = argparse.ArgumentParser(
        description="AI-powered web data extractor",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Target page URL to extract data from",
    )
    parser.add_argument(
        "--fields",
        required=True,
        help="Comma-separated field names to extract (e.g. 名称,价格,描述)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format (default: both)",
    )

    ns = parser.parse_args(argv)
    ns.fields = [f.strip() for f in ns.fields.split(",") if f.strip()]

    if not ns.fields:
        parser.error("At least one field must be specified in --fields")

    return ns


if __name__ == "__main__":
    args = parse_args()
    print(f"URL: {args.url}")
    print(f"Fields: {args.fields}")
    print(f"Output: {args.output}")
