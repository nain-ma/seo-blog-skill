#!/usr/bin/env python3
"""
DeepClick Blog Publisher
直接调用 WordPress REST API 发布文章，绕过 wpcom-mcp。

用法：
  python3 publish.py --site traffictalking.com --lang en --title "..." --content "..." --slug "..." \
                     [--categories 132592] [--status publish] [--meta-title "..."] \
                     [--meta-desc "..."] [--focus-kw "..."] [--excerpt "..."]

Credentials 从 ~/.config/deepclick-blog/sites.json 读取，格式见下方。
返回 JSON：{"post_id": 123, "url": "https://...", "edit_url": "https://...", "status": "publish"}
"""

import argparse
import base64
import json
import sys
import os
from pathlib import Path

try:
    import requests
except ImportError:
    # 尝试 pip install 后重试
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests


CONFIG_PATH = Path.home() / ".config" / "deepclick-blog" / "sites.json"

# sites.json 格式示例：
# {
#   "traffictalking.com": {
#     "url": "https://traffictalking.com",
#     "user": "your_username",
#     "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
#     "en_category": 132592,
#     "zh_category": 132594
#   },
#   "googlepwa.blog": {
#     "url": "https://googlepwa.blog",
#     "user": "your_username",
#     "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
#     "en_category": null,
#     "zh_category": null
#   }
# }


def load_config():
    if not CONFIG_PATH.exists():
        print(json.dumps({
            "error": f"Config not found: {CONFIG_PATH}",
            "hint": f"Create {CONFIG_PATH} with site credentials. See script header for format."
        }))
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    return f"Basic {token}"


def publish_post(site_cfg: dict, args: argparse.Namespace) -> dict:
    url = site_cfg["url"].rstrip("/")
    auth = get_auth_header(site_cfg["user"], site_cfg["app_password"])
    headers = {"Authorization": auth, "Content-Type": "application/json"}

    # 分类：优先用命令行参数，其次用配置文件
    if args.categories:
        category_id = int(args.categories)
    else:
        key = "en_category" if args.lang == "en" else "zh_category"
        category_id = site_cfg.get(key)

    payload = {
        "title": args.title,
        "content": args.content,
        "excerpt": args.excerpt or "",
        "status": args.status,
        "slug": args.slug,
    }
    if category_id:
        payload["categories"] = [category_id]

    # Rank Math SEO meta
    meta = {}
    if args.meta_title:
        meta["rank_math_title"] = args.meta_title
    if args.meta_desc:
        meta["rank_math_description"] = args.meta_desc
    if args.focus_kw:
        meta["rank_math_focus_keyword"] = args.focus_kw
    if meta:
        payload["meta"] = meta

    resp = requests.post(
        f"{url}/wp-json/wp/v2/posts",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not resp.ok:
        return {
            "error": f"HTTP {resp.status_code}",
            "body": resp.text[:500],
            "site": args.site,
            "lang": args.lang,
        }

    post = resp.json()
    post_id = post["id"]
    post_url = post.get("link", f"{url}/?p={post_id}")
    edit_url = f"{url}/wp-admin/post.php?post={post_id}&action=edit"

    return {
        "post_id": post_id,
        "url": post_url,
        "edit_url": edit_url,
        "status": post.get("status"),
        "slug": post.get("slug"),
        "site": args.site,
        "lang": args.lang,
    }


def main():
    parser = argparse.ArgumentParser(description="Publish post to WordPress via REST API")
    parser.add_argument("--site", required=True, help="Site key in sites.json, e.g. traffictalking.com")
    parser.add_argument("--lang", required=True, choices=["en", "zh"], help="Post language")
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True, help="HTML content")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--excerpt", default="")
    parser.add_argument("--categories", default=None, help="Category ID (overrides sites.json)")
    parser.add_argument("--status", default="publish", choices=["publish", "draft"])
    parser.add_argument("--meta-title", default="", help="Rank Math SEO title")
    parser.add_argument("--meta-desc", default="", help="Rank Math meta description")
    parser.add_argument("--focus-kw", default="", help="Rank Math focus keyword")
    args = parser.parse_args()

    config = load_config()
    site_cfg = config.get(args.site)
    if not site_cfg:
        print(json.dumps({
            "error": f"Site '{args.site}' not found in {CONFIG_PATH}",
            "available": list(config.keys()),
        }))
        sys.exit(1)

    result = publish_post(site_cfg, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
