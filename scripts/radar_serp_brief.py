#!/usr/bin/env python3
"""
Radar -> SEO SERP Brief

把 DeepClick Radar digest 里的 signals 转成写作前 brief，避免直接“热点=发文”。

示例：
  python3 radar_serp_brief.py --from-api --limit 3 --out brief.json
  python3 radar_serp_brief.py --input digest.md --out brief.json
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_API = "https://radar.qiliangjia.one/api/digests?type=daily&limit=3&offset=0"


def parse_signals(md: str):
    lines = md.splitlines()
    signals = []
    cur = None
    for ln in lines:
        t = ln.strip()
        m = re.match(r"^(?:[•\-]\s+)?@?([^\s]+(?:\s+[^—-]+)?)\s*[—-]\s*(.*)$", t)
        if m and ("原文链接" not in t):
            cur = {"source": m.group(1).lstrip("@"), "summary": m.group(2).strip(), "url": ""}
            signals.append(cur)
            continue
        u = re.search(r"原文链接[:：]\s*(https?://\S+)", t)
        if u and cur:
            cur["url"] = u.group(1)
            cur = None
    return signals


def relevance_score(summary: str) -> int:
    s = (summary or "").lower()
    score = 0
    rules = [
        (["meta", "facebook", "ads policy", "advantage+"], 30),
        (["cvr", "conversion", "post-click", "landing page", "cro"], 30),
        (["cpa", "roi", "cost", "attribution"], 20),
        (["retarget", "re-engagement", "pwa", "push"], 10),
        (["appsflyer", "adjust", "kochava", "redtrack", "voluum"], 10),
    ]
    for kws, pts in rules:
        if any(k in s for k in kws):
            score += pts
    return min(score, 100)


def infer_intent(summary: str) -> str:
    s = (summary or "").lower()
    if any(k in s for k in ["benchmark", "report", "data", "trend"]):
        return "informational"
    if any(k in s for k in ["how", "fix", "optimize", "improve"]):
        return "commercial"
    return "informational"


def build_brief_item(sig: dict) -> dict:
    summary = sig.get("summary", "")
    score = relevance_score(summary)
    intent = infer_intent(summary)
    return {
        "signal": sig,
        "radar_relevance_score": score,
        "search_intent": intent,
        "primary_keyword": "TODO: fill by keyword discovery",
        "secondary_keywords": ["TODO"],
        "serp_top10_common": ["TODO: summarize top 10 SERP common structure"],
        "content_gap": "TODO: what incumbents miss that we can fill",
        "required_evidence": [
            "至少 2 条可验证数据（含来源）",
            "至少 1 个 DeepClick 实操案例或链路截图",
            "样本口径/限制说明"
        ],
        "business_angle": "对 CVR / CPA / ROI 的具体影响",
    }


def fetch_api(url: str) -> str:
    req = Request(url, headers={"User-Agent": "deepclick-blog-skill/1.0"})
    with urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items") or data.get("data") or []
    else:
        items = []

    if not items:
        return ""

    # 兼容 radar 返回结构：优先取最新 digest.content
    first = items[0]
    if isinstance(first, dict) and first.get("content"):
        return first["content"]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-api", action="store_true")
    ap.add_argument("--api-url", default=DEFAULT_API)
    ap.add_argument("--input", help="digest markdown file")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    md = ""
    if args.from_api:
        md = fetch_api(args.api_url)
    elif args.input:
        md = Path(args.input).read_text(encoding="utf-8")

    if not md:
        raise SystemExit("No digest content found")

    signals = parse_signals(md)
    briefs = [build_brief_item(s) for s in signals]
    briefs = sorted(briefs, key=lambda x: x["radar_relevance_score"], reverse=True)[: args.limit]

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "radar_serp_brief",
        "count": len(briefs),
        "briefs": briefs,
    }

    txt = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(txt)
    else:
        Path(args.out).write_text(txt, encoding="utf-8")
        print(f"written {args.out}")


if __name__ == "__main__":
    main()
