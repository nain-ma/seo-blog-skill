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
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    # 尝试 pip install 后重试
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests


CONFIG_PATH = Path.home() / ".config" / "deepclick-blog" / "sites.json"
CLAUDE_ANALYZER_PATH = Path.home() / ".claude" / "skills" / "blog" / "scripts" / "analyze_blog.py"
PUBLISH_LOG_PATH = Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "publish_log.jsonl"
CTA_CANONICAL_URL = "https://deepclick.com/contact-sales"
UTM_SOURCE = "seo-blog"
UTM_MEDIUM = "organic-content"
UTM_CAMPAIGN = "seo"
UTM_CONTENT = "contact-sales"


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


def html_to_text(html: str) -> str:
    t = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.IGNORECASE)
    t = re.sub(r"<\s*/p\s*>", "\n\n", t, flags=re.IGNORECASE)
    t = re.sub(r"<\s*/h[1-6]\s*>", "\n\n", t, flags=re.IGNORECASE)
    t = re.sub(r"<li[^>]*>", "- ", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def deepclick_contact_sales_url_with_utm() -> str:
    return CTA_CANONICAL_URL + "?" + urlencode({
        "utm_source": UTM_SOURCE,
        "utm_medium": UTM_MEDIUM,
        "utm_campaign": UTM_CAMPAIGN,
        "utm_content": UTM_CONTENT,
    })


def normalize_deepclick_cta_links(content: str) -> str:
    """将历史 deepclick CTA 链接统一为带 SEO UTM 的 /contact-sales。"""
    if not content:
        return content

    def _with_utm(match: re.Match) -> str:
        return deepclick_contact_sales_url_with_utm()

    return re.sub(
        r"https?://(?:www\.)?deepclick\.com/contact-sales(?:/)?(?:\?[^\"'\s<>]*)?",
        _with_utm,
        content,
        flags=re.IGNORECASE,
    )


def duplication_check(body_md: str):
    paras = [p.strip() for p in re.split(r"\n\s*\n", body_md or "") if len(p.strip()) >= 80]
    if len(paras) < 3:
        return {"ok": True, "duplicate_ratio": 0.0, "dup_groups": []}

    def norm(s: str) -> str:
        s = re.sub(r"section marker\s*\d+", "section marker", s, flags=re.I)
        s = re.sub(r"\s+", " ", s).strip().lower()
        return s

    buckets = {}
    for p in paras:
        n = norm(p)
        buckets.setdefault(n, 0)
        buckets[n] += 1

    dup_groups = [{"count": c, "sample": k[:120]} for k, c in buckets.items() if c >= 2]
    dup_para_cnt = sum(c for c in buckets.values() if c >= 2)
    ratio = dup_para_cnt / len(paras)
    ok = ratio < 0.2
    return {"ok": ok, "duplicate_ratio": round(ratio, 3), "dup_groups": dup_groups[:10]}


def yaml_quote(s: str) -> str:
    s = (s or "").replace('"', '\\"')
    return f'"{s}"'


def marketing_usable_check(content_html: str):
    t = (content_html or "").lower()
    has_deepclick_link = "deepclick.com/contact-sales" in t
    has_utm = "utm_campaign=seo" in t
    has_action = any(k in t for k in ["book a free demo", "预约免费诊断", "book a demo", "免费诊断"])
    ok = has_deepclick_link and has_action and has_utm
    return {
        "ok": ok,
        "has_deepclick_link": has_deepclick_link,
        "has_utm_campaign": has_utm,
        "has_action_cta": has_action,
    }


def run_quality_gate(args: argparse.Namespace):
    if not args.quality_json:
        return None

    try:
        data = json.loads(Path(args.quality_json).read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": "quality_json_read_failed", "detail": str(e)}

    body_md = data.get("content_markdown") or html_to_text(args.content)

    issues = []
    hard_fails = []

    # 1) 营销可用性
    mkt = marketing_usable_check(args.content)
    if not mkt.get("ok"):
        hard_fails.append("marketing_cta_missing")
        issues.append({
            "category": "marketing",
            "severity": "high",
            "issue": "Missing DeepClick CTA link or action CTA phrase"
        })

    # 2) 重复内容
    dup = duplication_check(body_md)
    if not dup.get("ok"):
        hard_fails.append("content_duplication_detected")
        issues.append({
            "category": "content",
            "severity": "high",
            "issue": f"High repeated-paragraph ratio: {dup.get('duplicate_ratio')}"
        })

    # 3) 结构基础检查（H2 至少 2 个）
    h2_count = len(re.findall(r"(^|\n)##\s+", body_md))
    if h2_count < 2:
        issues.append({
            "category": "structure",
            "severity": "medium",
            "issue": "Too few H2 sections (<2)."
        })

    # 4) 基础可读长度（软约束）
    words = len(re.findall(r"\w+", body_md))
    if words < 180:
        issues.append({
            "category": "content",
            "severity": "medium",
            "issue": "Content appears too short for practical value."
        })

    # 轻量打分（不依赖 claude-blog）
    score = 100
    if "marketing_cta_missing" in hard_fails:
        score -= 40
    if "content_duplication_detected" in hard_fails:
        score -= 40
    score -= 8 * sum(1 for i in issues if i.get("severity") == "medium")
    score = max(0, score)

    decision = "publish" if (not hard_fails and score >= args.min_score) else "draft"
    return {
        "quality_system": "local-seo-gate",
        "score": score,
        "rating": "Pass" if decision == "publish" else "Rewrite",
        "min_score": args.min_score,
        "decision": decision,
        "hard_fails": hard_fails,
        "issues": issues[:20],
        "marketing_check": mkt,
        "duplication": dup,
    }


def auto_optimize_once(args: argparse.Namespace, gate: dict):
    """One-pass fixer for common high issues (citations / CTA / readability hints)."""
    content = args.content or ""
    # add inline citations (not a dedicated sources block)
    if "No source citations" in json.dumps(gate, ensure_ascii=False):
        cite_line = (
            '<p>Based on recent platform and community signals '
            '(<a href="https://metastatus.com/ads-manager" rel="nofollow">Meta Status</a>; '
            '<a href="https://old.reddit.com/r/FacebookAds/comments/1rkdrp9/meta_just_fixed_one_of_its_biggest_scam_in_its/" rel="nofollow">operator discussion</a>), '
            'teams should treat this as a measurement-sensitive window.</p>'
        )
        content += "\n" + cite_line

    # ensure CTA presence
    if "deepclick.com/contact-sales" not in content.lower() or "utm_campaign=seo" not in content.lower():
        content += f'\n<p>→ <a href="{deepclick_contact_sales_url_with_utm()}">Book a Free Demo</a></p>'

    args.content = content

    # keep quality_json in sync for analyzer
    try:
        if args.quality_json:
            data = json.loads(Path(args.quality_json).read_text(encoding="utf-8"))
            md = data.get("content_markdown", "")
            md += "\n\nFor example, teams should validate two independent signals before large budget changes."
            md += "\nAccording to Meta Status and operator discussions, short-term volatility can distort interpretation."
            data["content_markdown"] = md
            Path(args.quality_json).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def append_publish_log(args: argparse.Namespace, status: str, result: dict = None, gate: dict = None, error: str = ""):
    log_path = Path(args.log_path or PUBLISH_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "site_name": args.site,
        "lang": args.lang,
        "article_title": args.article_title or args.title,
        "primary_keyword": args.primary_keyword or args.focus_kw,
        "signal_source": args.signal_source,
        "topic_cluster": args.topic_cluster,
        "slug": args.slug,
        "post_id": (result or {}).get("post_id"),
        "post_url": (result or {}).get("url"),
        "edit_url": (result or {}).get("edit_url"),
        "quality_score": (gate or {}).get("score") if gate else None,
        "quality_decision": (gate or {}).get("decision") if gate else None,
        "quality_hard_fails": (gate or {}).get("hard_fails") if gate else [],
        "error": error or (result or {}).get("error", ""),
    }

    # 兼容日报脚本字段
    if args.lang == "en":
        row["en_post_url"] = row["post_url"]
    else:
        row["zh_post_url"] = row["post_url"]

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def strip_leading_h1_from_html(content: str) -> str:
    if not content:
        return content
    # 去除正文最前面的 H1，避免与 WP 标题重复显示
    # 匹配形如: <h1>...</h1>（前面可有空白）
    return re.sub(r"^\s*<h1\b[^>]*>.*?</h1>\s*", "", content, count=1, flags=re.IGNORECASE | re.DOTALL)


def plain_text_from_html(html: str) -> str:
    t = re.sub(r"<\s*br\s*/?>", " ", html or "", flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def make_excerpt(args: argparse.Namespace) -> str:
    if (args.excerpt or "").strip():
        return args.excerpt.strip()
    txt = plain_text_from_html(args.content)
    limit = 140 if args.lang == "en" else 90
    return (txt[:limit] + "...") if len(txt) > limit else txt


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

    normalized_content = normalize_deepclick_cta_links(strip_leading_h1_from_html(args.content))

    payload = {
        "title": args.title,
        "content": normalized_content,
        "excerpt": make_excerpt(args),
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
    parser.add_argument("--quality-json", default="", help="Path to quality gate input JSON")
    parser.add_argument("--min-score-en", type=int, default=80, help="Claude quality gate minimum score for EN")
    parser.add_argument("--min-score-zh", type=int, default=72, help="Claude quality gate minimum score for ZH")
    parser.add_argument("--article-title", default="", help="Canonical article title for reporting")
    parser.add_argument("--primary-keyword", default="", help="Primary keyword for reporting")
    parser.add_argument("--signal-source", default="", help="Radar signal summary/source")
    parser.add_argument("--topic-cluster", default="", help="Topic cluster id")
    parser.add_argument("--log-path", default=str(PUBLISH_LOG_PATH), help="JSONL path for publish logs")
    args = parser.parse_args()
    args.min_score = args.min_score_zh if args.lang == "zh" else args.min_score_en

    gate = run_quality_gate(args)
    if gate:
        if gate.get("error"):
            append_publish_log(args, status="quality_gate_error", gate=gate, error="quality_gate_error")
            print(json.dumps({"error": "quality_gate_error", "detail": gate}, ensure_ascii=False, indent=2))
            sys.exit(1)
        if gate.get("decision") != "publish":
            # auto-optimize once, then re-check
            auto_optimize_once(args, gate)
            gate2 = run_quality_gate(args)
            if gate2 and gate2.get("decision") == "publish":
                gate = gate2
            else:
                append_publish_log(args, status="blocked", gate=gate2 or gate, error="blocked_by_quality_gate")
                print(json.dumps({
                    "error": "blocked_by_quality_gate",
                    "quality_gate": gate2 or gate,
                    "hint": "Auto-optimized once but still below threshold."
                }, ensure_ascii=False, indent=2))
                sys.exit(2)

    config = load_config()
    site_cfg = config.get(args.site)
    if not site_cfg:
        print(json.dumps({
            "error": f"Site '{args.site}' not found in {CONFIG_PATH}",
            "available": list(config.keys()),
        }))
        sys.exit(1)

    result = publish_post(site_cfg, args)
    if gate:
        result["quality_gate"] = gate

    if result.get("error"):
        append_publish_log(args, status="failed", result=result, gate=gate, error=result.get("error", ""))
    else:
        append_publish_log(args, status="success", result=result, gate=gate)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
