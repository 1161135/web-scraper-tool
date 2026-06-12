# 网页数据采集工具 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task using executing-plans or inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-based web scraper that takes a URL + field descriptions, uses Playwright to get page text, DeepSeek to extract fields, and saves to JSON/CSV.

**Architecture:** Four-module design — cli (argparse) → browser (Playwright) → extractor (DeepSeek API) → storage (JSON+CSV), orchestrated by run.py.

**Tech Stack:** Python 3.10+, Playwright, OpenAI-compatible DeepSeek API, no web framework.

**Project path:** `E:\web-scraper\`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `E:\web-scraper\requirements.txt`
- Create: `E:\web-scraper\.gitignore`
- Create: `E:\web-scraper\.env.example`
- Create: `E:\web-scraper\scraper\__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
playwright>=1.48.0
openai>=1.55.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create .gitignore**

```txt
.env
__pycache__/
*.pyc
output/
node_modules/
```

- [ ] **Step 3: Create .env.example**

```txt
# DeepSeek API
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

- [ ] **Step 4: Create scraper/__init__.py**

```python
# web-scraper package
```

- [ ] **Step 5: Install Playwright browsers**

Run: `pip install -r requirements.txt && playwright install chromium`

Expected: Playwright downloads Chromium browser.

- [ ] **Step 6: Init git repo**

Run (inside E:\web-scraper\):
```bash
git init
git add -A
git commit -m "chore: initial scaffold"
```

---

### Task 2: CLI Module — `scraper/cli.py`

**Files:**
- Create: `E:\web-scraper\scraper\cli.py`

Responsibility: Parse `--url` (required), `--fields` (required, comma-separated string), `--output` (optional, json/csv/both, default both).

- [ ] **Step 1: Write cli.py**

```python
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
```

- [ ] **Step 2: Quick test**

Run: `python scraper/cli.py --url "https://example.com" --fields "a,b"`

Expected: Prints "URL: https://example.com", "Fields: ['a', 'b']"

- [ ] **Step 3: Commit**

```bash
git add scraper/cli.py
git commit -m "feat: add CLI argument parsing"
```

---

### Task 3: Browser Module — `scraper/browser.py`

**Files:**
- Create: `E:\web-scraper\scraper\browser.py`

Responsibility: Accept a URL, open with Playwright, wait for page load, extract visible text content, return structured dict with `{title, text, url}`.

- [ ] **Step 1: Write browser.py**

```python
"""Playwright browser controller for page text extraction."""

from playwright.sync_api import sync_playwright


def get_page_text(url: str, timeout: int = 15000) -> dict:
    """Open a URL with Playwright and extract visible text.

    Args:
        url: Target webpage URL.
        timeout: Navigation timeout in ms (default 15s).

    Returns:
        Dict with keys: title, text, url.

    Raises:
        RuntimeError: If page fails to load.

    """
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout)

            title = page.title()
            # Extract visible text from the body
            body_text = page.evaluate("""() => {
                // Remove script, style, noscript elements
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll('script, style, noscript, svg')
                    .forEach(el => el.remove());
                return clone.innerText;
            }""")

            # Clean up excessive whitespace
            lines = [l.strip() for l in body_text.split("\n") if l.strip()]
            clean_text = "\n".join(lines)

            browser.close()

            return {
                "title": title,
                "text": clean_text[:8000],  # Cap at 8k chars for token budget
                "url": url,
            }
    except Exception as e:
        raise RuntimeError(f"Failed to load page: {url}") from e
```

- [ ] **Step 2: Quick test with real URL**

Run: `python -c "from scraper.browser import get_page_text; d = get_page_text('https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html'); print(d['title']); print(len(d['text']), 'chars')"`

Expected: Prints page title and character count (e.g. ~2000 chars). No crash.

- [ ] **Step 3: Commit**

```bash
git add scraper/browser.py
git commit -m "feat: add Playwright browser controller"
```

---

### Task 4: Extractor Module — `scraper/extractor.py`

**Files:**
- Create: `E:\web-scraper\scraper\extractor.py`

Responsibility: Accept page text + list of field names, build prompt, call DeepSeek API, parse returned JSON.

- [ ] **Step 1: Write extractor.py**

```python
"""DeepSeek-powered field extraction from page text."""

import json
import os

from openai import OpenAI


def _build_prompt(page_text: str, fields: list[str]) -> str:
    fields_str = ", ".join(fields)
    return f"""你是一个网页数据提取助手。请从以下网页内容中提取指定的信息。

需要提取的字段：{fields_str}

网页内容：
{page_text[:6000]}

请以JSON格式返回结果，只返回JSON，不要加任何额外文字。
如果某个字段找不到对应值，设为 null。
JSON的键名请使用中文，和用户指定的字段名一致。
"""


def extract_fields(page_text: str, fields: list[str]) -> dict:
    """Use DeepSeek to extract requested fields from page text.

    Args:
        page_text: The visible text content of the page.
        fields: List of field names to extract.

    Returns:
        Dict mapping field names to extracted values (str or None).

    Raises:
        RuntimeError: If API call fails after retry.

    """
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    prompt = _build_prompt(page_text, fields)

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content.strip()

            # Try to find JSON in the response (handle model wrapping it in ```json ... ```)
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            # Validate: ensure all requested fields are present
            for field in fields:
                if field not in result:
                    result[field] = None

            return result

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if attempt == 1:
                raise RuntimeError(
                    f"Failed to parse AI response after retry: {e}\nRaw: {content}"
                )
            continue
        except Exception as e:
            if attempt == 1:
                raise RuntimeError(f"DeepSeek API error after retry: {e}")
            continue

    return {f: None for f in fields}  # Fallback (should not reach)
```

- [ ] **Step 2: Create .env with your key for local testing**

Create `E:\web-scraper\.env`:
```env
DEEPSEEK_API_KEY=sk-your-actual-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

(You paste your real key)

- [ ] **Step 3: Quick test with sample text**

Run: `python -c "from scraper.extractor import extract_fields; from dotenv import load_dotenv; load_dotenv(); r = extract_fields('书名：三体 价格：99元 库存：有货', ['书名','价格']); print(r)"`

Expected: `{'书名': '三体', '价格': '99元'}`

- [ ] **Step 4: Commit**

```bash
git add scraper/extractor.py
git commit -m "feat: add DeepSeek field extractor"
```

---

### Task 5: Storage Module — `scraper/storage.py`

**Files:**
- Create: `E:\web-scraper\scraper\storage.py`

Responsibility: Accept extracted data dict + output format, save to `output/<timestamp>/data.json` and/or `data.csv`.

- [ ] **Step 1: Write storage.py**

```python
"""Data persistence — JSON and CSV output."""

import csv
import json
import os
from datetime import datetime


def _output_dir() -> str:
    """Create and return timestamped output directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join("output", ts)
    os.makedirs(out, exist_ok=True)
    return out


def save_json(data: dict, out_dir: str, meta: dict | None = None) -> str:
    """Save extracted data as JSON with metadata.

    Args:
        data: Extracted field dict.
        out_dir: Output directory path.
        meta: Optional metadata (url, timestamp, etc.).

    Returns:
        Path to saved file.

    """
    payload = {
        "meta": meta or {},
        "data": data,
    }
    path = os.path.join(out_dir, "data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def save_csv(data: dict, out_dir: str) -> str:
    """Save extracted data as CSV (one row).

    Args:
        data: Extracted field dict.
        out_dir: Output directory path.

    Returns:
        Path to saved file.

    """
    path = os.path.join(out_dir, "data.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerow(data)
    return path


def save_all(data: dict, url: str, output_format: str = "both") -> dict[str, str]:
    """Save data in requested formats.

    Args:
        data: Extracted field dict.
        url: Source URL (included in metadata).
        output_format: 'json', 'csv', or 'both'.

    Returns:
        Dict mapping format names to file paths.

    """
    out_dir = _output_dir()
    meta = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
    }

    saved = {}
    if output_format in ("json", "both"):
        p = save_json(data, out_dir, meta)
        saved["json"] = p
    if output_format in ("csv", "both"):
        p = save_csv(data, out_dir)
        saved["csv"] = p

    return saved
```

- [ ] **Step 2: Quick test**

Run:
```bash
python -c "
from scraper.storage import save_all
result = save_all({'书名': '三体', '价格': '99元'}, 'https://example.com', 'both')
print(result)
"
```

Expected: Prints dict with json and csv paths. Check `output/` directory for actual files.

- [ ] **Step 3: Add output/ to .gitignore (already done in Task 1 — verify)**

Run: `grep "output/" .gitignore`

Expected: Shows `output/` line in gitignore.

- [ ] **Step 4: Commit**

```bash
git add scraper/storage.py
git commit -m "feat: add JSON/CSV storage"
```

---

### Task 6: Main Entry Point — `run.py`

**Files:**
- Create: `E:\web-scraper\run.py`

Responsibility: Load .env, parse CLI args, orchestrate browser → extractor → storage flow, print summary.

- [ ] **Step 1: Write run.py**

```python
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
```

- [ ] **Step 2: End-to-end test with a real public site**

Make sure `.env` has your DeepSeek key, then run:

```bash
cd /mnt/e/web-scraper
python run.py --url "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" --fields "书名,价格,库存状态,描述"
```

Expected:
1. Opens browser, loads page
2. Extracts text
3. DeepSeek returns structured data
4. Files saved to `output/<timestamp>/`
5. Console prints results

- [ ] **Step 3: Verify CSV opens correctly**

Open the CSV file in WPS/Excel or cat it:

```bash
cat output/*/data.csv
```

Expected: Headers + data row, comma-separated, readable.

- [ ] **Step 4: Test error handling**

Run without .env:
```bash
mv .env .env.bak && python run.py --url "https://example.com" --fields "a" && mv .env.bak .env
```

Expected: Error message about missing API key.

- [ ] **Step 5: Commit**

```bash
git add run.py
git commit -m "feat: add main entry point with orchestration"
git add -A && git commit -m "chore: finalize MVP"
```

---

### Task 7: Final Validation & Demo

- [ ] **Step 1: Clean run with different URL**

```bash
python run.py --url "https://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html" --fields "书名,价格,描述"
```

Expected: Works on a different page too — proves it's not hardcoded.

- [ ] **Step 2: Check output files exist**

```bash
ls -la output/*/
```

Expected: At least one timestamped folder with data.json and data.csv.

- [ ] **Step 3: README (optional)**

Create a one-page README.md with install & usage instructions.
