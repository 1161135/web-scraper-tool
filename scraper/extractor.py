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
            cont = response.choices[0].message.content.strip()

            # Try to find JSON in the response (handle model wrapping it in code blocks)
            if "```" in cont:
                cont = cont.split("```")[1]
                if cont.startswith("json"):
                    cont = cont[4:]
                cont = cont.strip()

            result = json.loads(cont)

            # Validate: ensure all requested fields are present
            for field in fields:
                if field not in result:
                    result[field] = None

            return result

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if attempt == 1:
                raise RuntimeError(
                    f"Failed to parse AI response after retry: {e}\nRaw: {cont}"
                )
            continue
        except Exception as e:
            if attempt == 1:
                raise RuntimeError(f"DeepSeek API error after retry: {e}")
            continue

    return {f: None for f in fields}  # Fallback (should not reach)
