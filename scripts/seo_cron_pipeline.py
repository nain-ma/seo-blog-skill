#!/usr/bin/env python3
"""
Second-batch cron pipeline orchestrator

每日一键：
1) Radar -> SERP brief 候选池
2) SEO Daily Review (D+14)
3) SEO Quality Dashboard

说明：本脚本负责调度与产物，发文生成/发布由既有任务或上层 agent 调用 publish.py。
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{p.stderr or p.stdout}")
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="Radar brief candidate count")
    ap.add_argument("--logs-dir", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog"))
    args = ap.parse_args()

    logs = Path(args.logs_dir)
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    base = Path(__file__).resolve().parent
    brief_out = logs / f"serp-brief-{stamp}.json"
    review_out = logs / "daily-review.md"
    dash_out = logs / "quality-dashboard.md"

    run([sys.executable, str(base / "radar_serp_brief.py"), "--from-api", "--limit", str(args.limit), "--out", str(brief_out)])
    run([sys.executable, str(base / "seo_daily_review.py"), "--out", str(review_out)])
    run([sys.executable, str(base / "seo_quality_dashboard.py"), "--out", str(dash_out)])

    print("\n".join([
        f"brief: {brief_out}",
        f"review: {review_out}",
        f"dashboard: {dash_out}",
    ]))


if __name__ == "__main__":
    main()
