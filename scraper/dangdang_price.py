# -*- coding: utf-8 -*-
"""Dangdang price extractor."""
import re

YEN = "[" + chr(165) + chr(65509) + "]"

def extract_dangdang_price(text, url):
    is_ebook = "e.dangdang.com" in url
    # Only search main product area (before recommendations/recommended section)
    main_text = text
    for marker in ["为你推荐", "同类图书排行榜", "读了这本书的人还在读", "买过这本书的人还买过"]:
        idx = text.find(marker)
        if idx > 0:
            main_text = text[:idx]
            break
    lines = main_text.split("\n")
    paper = _paper(main_text)
    def ok(v): return v is not None and _fmt(v) != paper
    # Priority 1: 促销价 (e.g. "促销价:¥4.99 | ¥27.99" -> take ¥4.99)
    m = re.search(r'促销\s*价[^。\n\d]*?[¥￥]?\s*([\d,]+\.?\d*)', main_text)
    if m and ok(m.group(1)): return _fmt(m.group(1))
    # Priority 2: 特价
    m = re.search(r'特\s*价[^。\n\d]*?[¥￥]?\s*([\d,]+\.?\d*)', main_text)
    if m and ok(m.group(1)): return _fmt(m.group(1))
    # Priority 3: 售价 (not 纸质售价)
    if is_ebook:
        m = re.search(r'(?<!纸)售\s*价\s*[：:]\s*[¥￥]?\s*([\d,]+\.\d{2})', main_text)
        if m and ok(m.group(1)): return _fmt(m.group(1))
    # Priority 4: "价：¥59.00" partial label
    if is_ebook:
        for line in lines:
            m = re.search(r'价\s*[：:]\s*[¥￥]\s*([\d,]+\.\d{2})', line)
            if m and ok(m.group(1)): return _fmt(m.group(1))
    # Priority 5: Any non-paper, non-strikethrough price
    for p in re.findall(r'[¥￥]\s*([\d,]+\.\d{2})', main_text):
        fp = _fmt(p)
        if fp != paper: return fp
    return None

def _paper(text):
    m = re.search("纸质售价[^。" + "\n" + r"\d]*?" + YEN + r"?\s*([\d,]+\.\d{2})", text)
    return _fmt(m.group(1)) if m else None

def _fmt(v):
    v = v.replace(",", "").strip()
    try: return chr(165) + "{:.2f}".format(float(v))
    except ValueError: return chr(165) + v
