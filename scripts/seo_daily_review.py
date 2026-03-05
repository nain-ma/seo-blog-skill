#!/usr/bin/env python3
"""
Daily SEO Review (cron helper)

目标：把“每日发文任务”升级为“发文 + D+14 复盘待办”。
当前版本先生成复盘清单（收录/排名/CTR/停留/CTA 点击），便于后续接 Search Console API。

示例：
  python3 seo_daily_review.py --publish-log ~/.openclaw/logs/deepclick-blog/publish_log.jsonl
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ8 = timezone(timedelta(hours=8))


def parse_dt(s: str):
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).astimezone(TZ8)
        except Exception:
            continue
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish-log", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "publish_log.jsonl"))
    ap.add_argument("--out", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "daily-review.md"))
    ap.add_argument("--review-days", type=int, default=14)
    args = ap.parse_args()

    logs = load_jsonl(Path(args.publish_log))
    now = datetime.now(TZ8)

    due = []
    for r in logs:
        ts = parse_dt(r.get("published_at", ""))
        if not ts:
            continue
        if (now - ts).days >= args.review_days:
            due.append(r)

    lines = []
    lines.append(f"# DeepClick SEO Daily Review ({now.strftime('%Y-%m-%d %H:%M')} CST)")
    lines.append("")
    lines.append("## 今日复盘队列（D+14）")
    lines.append("")
    if not due:
        lines.append("- 今日无到期复盘文章。")
    else:
        for i, r in enumerate(due, 1):
            lines.append(f"### {i}. {r.get('article_title','(untitled)')}")
            lines.append(f"- URL: {r.get('en_post_url') or r.get('zh_post_url') or 'N/A'}")
            lines.append(f"- Primary KW: `{r.get('primary_keyword','')}`")
            lines.append("- 采集指标待填：")
            lines.append("  - [ ] 是否收录")
            lines.append("  - [ ] 平均排名")
            lines.append("  - [ ] CTR")
            lines.append("  - [ ] 平均停留时长")
            lines.append("  - [ ] Demo 点击率")
            lines.append("- 建议动作：")
            lines.append("  - [ ] 改标题（若 CTR 低）")
            lines.append("  - [ ] 改 H2 结构（若排名卡 11-20）")
            lines.append("  - [ ] 补证据与案例（若停留低）")
            lines.append("  - [ ] 调整 CTA（若点击率低）")
            lines.append("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
