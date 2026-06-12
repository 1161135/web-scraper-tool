"""HTML report generator — creates a browser-viewable data report."""

import os
from datetime import datetime


def _html_template(title: str, url: str, timestamp: str, fields: list[str],
                   data: dict) -> str:
    """Generate a complete HTML page with the extracted data."""
    # Build table rows
    rows_html = ""
    for field in fields:
        value = data.get(field, "")
        if value is None:
            value = ""
        rows_html += f"""      <tr>
        <td class="field-name">{field}</td>
        <td class="field-value">{value}</td>
      </tr>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>采集结果 — {title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
    background: #f5f7fa;
    color: #1a1a2e;
    padding: 40px 20px;
  }}
  .container {{
    max-width: 800px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 8px;
    color: #1a1a2e;
  }}
  .meta {{
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 24px;
    line-height: 1.6;
  }}
  .meta a {{ color: #3b82f6; text-decoration: none; }}
  .meta a:hover {{ text-decoration: underline; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}
  th {{
    background: #1a1a2e;
    color: white;
    padding: 14px 20px;
    text-align: left;
    font-weight: 500;
    font-size: 14px;
  }}
  td {{
    padding: 14px 20px;
    border-bottom: 1px solid #e5e7eb;
    font-size: 14px;
    vertical-align: top;
  }}
  tr:last-child td {{ border-bottom: none; }}
  .field-name {{
    font-weight: 600;
    color: #374151;
    width: 120px;
    white-space: nowrap;
    background: #f9fafb;
  }}
  .field-value {{
    color: #1a1a2e;
    word-break: break-word;
  }}
  .badge {{
    display: inline-block;
    background: #dbeafe;
    color: #1d4ed8;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    margin-top: 16px;
  }}
  .footer {{
    margin-top: 16px;
    font-size: 12px;
    color: #9ca3af;
    text-align: center;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>📋 采集结果</h1>
  <div class="meta">
    <div>🔗 来源：<a href="{url}" target="_blank">{url}</a></div>
    <div>⏱️ 采集时间：{timestamp}</div>
  </div>

  <table>
    <thead>
      <tr><th>字段</th><th>值</th></tr>
    </thead>
    <tbody>
{rows_html}    </tbody>
  </table>

  <div class="badge">AI Agent 智能采集 · DeepSeek 驱动</div>
  <div class="footer">由 AI Agent 网页数据采集工具自动生成</div>
</div>
</body>
</html>"""


def save_html(data: dict, url: str, fields: list[str],
              out_dir: str) -> str:
    """Generate and save an HTML report of the extracted data.

    Args:
        data: Extracted field dict.
        url: Source URL.
        fields: List of field names in order.
        out_dir: Output directory path.

    Returns:
        Path to saved HTML file.

    """
    title = data.get("title", data.get(fields[0], url)) if fields else url
    if isinstance(title, str) and len(title) > 80:
        title = title[:80] + "..."

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = _html_template(
        title=str(title),
        url=url,
        timestamp=timestamp,
        fields=fields,
        data=data,
    )

    path = os.path.join(out_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
