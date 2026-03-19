#!/usr/bin/env python3
"""Google Autocomplete 字母扩展 — 从种子关键词生成长尾关键词列表."""

from __future__ import annotations

import argparse
import json
import string
import sys
import time
import urllib.request
import urllib.parse

AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"
REQUEST_DELAY = 0.3  # 秒


def fetch_suggestions(seed: str, lang: str, country: str) -> tuple[list[str], int]:
    """对单个种子词做字母扩展（空 + a-z），返回 (关键词列表, 错误数)."""
    keywords = set()
    errors = 0
    suffixes = [""] + list(string.ascii_lowercase)

    for suffix in suffixes:
        query = f"{seed} {suffix}".strip()
        params = urllib.parse.urlencode({
            "client": "chrome",
            "hl": lang,
            "gl": country,
            "q": query,
        })
        url = f"{AUTOCOMPLETE_URL}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 1:
                    keywords.update(data[1])
        except Exception:
            errors += 1
        time.sleep(REQUEST_DELAY)

    return sorted(keywords), errors


def main():
    parser = argparse.ArgumentParser(description="Google Autocomplete 长尾词扩展")
    parser.add_argument("--seeds", required=True, help="种子关键词，多个用逗号分隔")
    parser.add_argument("--lang", default="en", help="语言代码 (默认: en)")
    parser.add_argument("--country", default="US", help="国家代码 (默认: US)")
    args = parser.parse_args()

    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    all_keywords = set()
    total_errors = 0

    for seed in seeds:
        kws, errs = fetch_suggestions(seed, args.lang, args.country)
        all_keywords.update(kws)
        total_errors += errs

    result = {
        "keywords": sorted(all_keywords),
        "seed_count": len(seeds),
        "total": len(all_keywords),
        "errors": total_errors,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
