#!/usr/bin/env python3
"""
SEO Quality Gate for DeepClick Blog

用途：发布前质量拦截，输出 0-100 分评分与是否允许 publish。
输入：JSON（文件或 stdin）
输出：JSON（评分明细 + 拦截原因）

示例：
  python3 seo_quality_gate.py --input article.json --min-score 75
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Tuple


def wc(text: str) -> int:
    t = text or ""
    en_words = len(re.findall(r"\b\w+\b", t))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", t))
    # 粗略换算：2 个中文字符约等于 1 个英文词长度单位
    return en_words + cjk_chars // 2


def has_any(text: str, kws: List[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in kws)


def score_keyword_intent(data: Dict) -> Tuple[int, str]:
    title = data.get("title", "")
    h1 = data.get("h1", "")
    primary = data.get("primary_keyword", "")
    intent = (data.get("search_intent", "") or "").lower()

    s = 0
    notes = []
    if primary and has_any(title, [primary]):
        s += 10
    else:
        notes.append("主关键词未出现在标题")

    if primary and has_any(h1, [primary]):
        s += 8
    else:
        notes.append("主关键词未出现在 H1")

    valid_intents = {"informational", "commercial", "transactional", "navigational"}
    if intent in valid_intents:
        s += 7
    else:
        notes.append("search_intent 缺失或非法")

    return s, "；".join(notes) if notes else "OK"


def score_structure(data: Dict) -> Tuple[int, str]:
    h2s = data.get("h2", []) or []
    body = data.get("content_markdown", "")
    words = wc(body)
    s = 0
    notes = []

    if 5 <= len(h2s) <= 10:
        s += 8
    else:
        notes.append(f"H2 数量建议 5-10，当前 {len(h2s)}")

    if words >= 1200:
        s += 8
    elif words >= 800:
        s += 5
        notes.append("字数偏少，建议 >=1200")
    else:
        notes.append("字数不足 800")

    if data.get("meta_title") and data.get("meta_desc"):
        s += 4
    else:
        notes.append("Meta Title/Description 不完整")

    return s, "；".join(notes) if notes else "OK"


def score_eeat(data: Dict) -> Tuple[int, str]:
    proofs = data.get("evidence", []) or []
    citations = data.get("citations", []) or []
    s = 0
    notes = []

    if len(proofs) >= 2:
        s += 10
    else:
        notes.append("证据点不足（<2）")

    if len(citations) >= 2:
        s += 10
    else:
        notes.append("引用来源不足（<2）")

    if data.get("has_limitations_note"):
        s += 5
    else:
        notes.append("缺少样本/口径限制说明")

    return s, "；".join(notes) if notes else "OK"


def score_cluster_and_links(data: Dict) -> Tuple[int, str]:
    internal_links = data.get("internal_links", []) or []
    cluster = data.get("topic_cluster", "")
    s = 0
    notes = []

    if len(internal_links) >= 3:
        s += 10
    else:
        notes.append("内链不足（<3）")

    if cluster:
        s += 10
    else:
        notes.append("缺少 topic_cluster")

    return s, "；".join(notes) if notes else "OK"


def score_cta_and_publish(data: Dict) -> Tuple[int, str]:
    ctas = data.get("ctas", {}) or {}
    title_unique = bool(data.get("title_unique", False))
    category_ok = bool(data.get("category_ok", False))
    s = 0
    notes = []

    if ctas.get("top") and ctas.get("middle") and ctas.get("bottom"):
        s += 8
    else:
        notes.append("CTA 三段不完整（top/middle/bottom）")

    if title_unique:
        s += 6
    else:
        notes.append("标题唯一性校验未通过")

    if category_ok:
        s += 4
    else:
        notes.append("分类未配置完整")

    return s, "；".join(notes) if notes else "OK"


def _cap(v: int, max_v: int) -> int:
    return max(0, min(v, max_v))


def _has_heading_leak(text: str) -> bool:
    # 出现在已渲染正文里的 markdown 标题符号，通常表示未正确转 HTML
    return bool(re.search(r"(^|\n)\s{0,3}#{1,6}\s+", text or ""))


def _has_todo_marker(data: Dict) -> bool:
    joined = "\n".join([
        str(data.get("primary_keyword", "")),
        "\n".join(data.get("secondary_keywords", []) or []),
        "\n".join(data.get("serp_top10_common", []) or []),
        str(data.get("content_gap", "")),
        str(data.get("content_markdown", ""))[:2000],
    ]).lower()
    return "todo" in joined or "待补" in joined


def _repetition_ratio(text: str) -> float:
    sents = [s.strip() for s in re.split(r"[。！？.!?]\s*", text or "") if s.strip()]
    if len(sents) < 6:
        return 0.0
    uniq = len(set(sents))
    return 1 - (uniq / len(sents))


def run(data: Dict, min_score: int) -> Dict:
    raw_blocks = {
        "keyword_intent_25": score_keyword_intent(data),
        "structure_20": score_structure(data),
        "eeat_25": score_eeat(data),
        "cluster_links_20": score_cluster_and_links(data),
        "cta_publish_15": score_cta_and_publish(data),
    }

    # 强制对齐各块上限，避免超 100 分
    caps = {
        "keyword_intent_25": 25,
        "structure_20": 20,
        "eeat_25": 25,
        "cluster_links_20": 20,
        "cta_publish_15": 15,
    }
    blocks = {k: (_cap(v[0], caps[k]), v[1]) for k, v in raw_blocks.items()}
    total = sum(v[0] for v in blocks.values())
    normalized = round(total * 100 / 105)

    hard_fails = []
    if not data.get("title_unique", False):
        hard_fails.append("title_not_unique")
    if not data.get("category_ok", False):
        hard_fails.append("category_missing")
    if len(data.get("evidence", []) or []) < 2:
        hard_fails.append("evidence_insufficient")

    body = data.get("content_markdown", "") or ""
    rendered = data.get("rendered_content", "") or ""
    if rendered and _has_heading_leak(rendered):
        hard_fails.append("markdown_heading_leak")
    if _has_todo_marker(data):
        hard_fails.append("todo_placeholder_found")
    if _repetition_ratio(body) >= 0.35:
        hard_fails.append("content_repetition_high")

    decision = "publish" if normalized >= min_score and not hard_fails else "draft"

    return {
        "score": normalized,
        "min_score": min_score,
        "decision": decision,
        "hard_fails": hard_fails,
        "blocks": {k: {"score": v[0], "note": v[1]} for k, v in blocks.items()},
    }


def load_input(path: str) -> Dict:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="-", help="JSON file path, or - for stdin")
    ap.add_argument("--min-score", type=int, default=75)
    args = ap.parse_args()

    data = load_input(args.input)
    result = run(data, args.min_score)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
