#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_ts(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def load_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            pass
    return rows


def main():
    ap = argparse.ArgumentParser(description="SEO quality dashboard from publish_log.jsonl")
    ap.add_argument("--publish-log", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "publish_log.jsonl"))
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "quality-dashboard.md"))
    args = ap.parse_args()

    rows = load_jsonl(Path(args.publish_log))
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    rows = [r for r in rows if (parse_ts(r.get("published_at", "")) or since) >= since]

    total = len(rows)
    by_status = Counter(r.get("status", "unknown") for r in rows)
    scores = [r.get("quality_score") for r in rows if isinstance(r.get("quality_score"), int)]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    blocked = by_status.get("blocked", 0)
    blocked_rate = round(blocked * 100 / total, 1) if total else 0

    fail_counter = Counter()
    for r in rows:
        for f in (r.get("quality_hard_fails") or []):
            fail_counter[f] += 1

    lines = []
    lines.append(f"# DeepClick SEO 质量看板（近 {args.days} 天）")
    lines.append("")
    lines.append("## 核心指标")
    lines.append(f"- 发布尝试总数：**{total}**")
    lines.append(f"- 成功：**{by_status.get('success', 0)}**")
    lines.append(f"- 失败：**{by_status.get('failed', 0)}**")
    lines.append(f"- 拦截：**{blocked}**（拦截率 {blocked_rate}%）")
    lines.append(f"- 平均质量分：**{avg_score}**")
    lines.append("")

    lines.append("## 高频拦截原因")
    if fail_counter:
        for k, v in fail_counter.most_common(10):
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- 无")

    lines.append("")
    lines.append("## 今日优先修订")
    low = [r for r in rows if isinstance(r.get("quality_score"), int) and r.get("quality_score") < 75]
    low = sorted(low, key=lambda x: x.get("quality_score", 0))[:10]
    if not low:
        lines.append("- 无低分文章")
    else:
        for r in low:
            lines.append(f"- [{r.get('site_name')}/{r.get('lang')}] {r.get('article_title')} | score={r.get('quality_score')} | {r.get('post_url') or r.get('slug')}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
