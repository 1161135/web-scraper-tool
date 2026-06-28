"""Command-line argument parsing for web-scraper."""

import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Namespace with .url (str), .fields (list[str]), .output (str),
        .auto (bool), .limit (int), .login (bool), .clear_session (bool)

    """
    parser = argparse.ArgumentParser(
        description="AI-powered web data extractor",
    )
    parser.add_argument(
        "--url",
        help="Target page URL (product detail or search/list page)",
    )
    parser.add_argument(
        "--fields",
        help='Comma-separated field names (e.g. "Title, Price, Rating")',
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
        default=20,
        help="Max items to collect in auto mode (default: 20)",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open browser to log into a platform (Taobao/JD), saves session",
    )
    parser.add_argument(
        "--clear-session",
        action="store_true",
        help="Clear saved login session",
    )

    ns = parser.parse_args(argv)

    # Require --url and --fields only when not in login/clear-session mode
    if not ns.login and not ns.clear_session:
        if not ns.url:
            parser.error("the following arguments are required: --url")
        if not ns.fields:
            parser.error("the following arguments are required: --fields")

        ns.fields = [f.strip() for f in ns.fields.replace("，", ",").split(",") if f.strip()]
        if not ns.fields:
            parser.error("At least one field must be specified in --fields")

    return ns
