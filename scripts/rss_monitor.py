#!/usr/bin/env python3
"""竞品 RSS 抓取 — 监控行业博客新文章，去重输出."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import feedparser
except ImportError:
    print(json.dumps({"error": "feedparser not installed. Run: pip install feedparser"}))
    sys.exit(1)

RSS_SOURCES = [
    {"name": "Jon Loomer", "url": "https://www.jonloomer.com/feed/"},
    {"name": "VWO", "url": "https://vwo.com/blog/feed/"},
    {"name": "SEJ Paid Media", "url": "https://www.searchenginejournal.com/category/paid-media/feed/"},
    {"name": "Unbounce", "url": "https://unbounce.com/feed/"},
    {"name": "WordStream", "url": "https://www.wordstream.com/feed"},
    {"name": "CRO Weekly", "url": "https://tomvandenberg.substack.com/feed"},
]

SEEN_FILE = Path("~/.config/deepclick-blog/rss-seen.json").expanduser()


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text())
            return set(data.get("urls", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def save_seen(urls: set[str]):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps({
        "urls": sorted(urls),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def parse_published(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def fetch_source(source: dict, cutoff: datetime) -> list[dict]:
    articles = []
    feed = feedparser.parse(source["url"])
    if feed.bozo and not feed.entries:
        raise Exception(f"Feed parse error: {feed.bozo_exception}")
    for entry in feed.entries:
        pub = parse_published(entry)
        if pub and pub < cutoff:
            continue
        articles.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "published": pub.isoformat() if pub else "",
            "source": source["name"],
        })
    return articles


def main():
    parser = argparse.ArgumentParser(description="竞品 RSS 监控")
    parser.add_argument("--days", type=int, default=7, help="抓取最近 N 天的文章 (默认: 7)")
    parser.add_argument("--mark-seen", action="store_true", help="将本次新文章标记为已读")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    seen = load_seen()
    new_articles = []
    failed_sources = []

    for source in RSS_SOURCES:
        try:
            articles = fetch_source(source, cutoff)
            for a in articles:
                if a["url"] and a["url"] not in seen:
                    new_articles.append(a)
        except Exception as e:
            failed_sources.append({"name": source["name"], "error": str(e)})

    if args.mark_seen:
        new_urls = {a["url"] for a in new_articles if a["url"]}
        save_seen(seen | new_urls)

    result = {
        "new_articles": new_articles,
        "total_new": len(new_articles),
        "failed_sources": failed_sources,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
