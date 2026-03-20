#!/usr/bin/env python3
"""
Daily SEO Review (cron helper)

目标：把“每日发文任务”升级为“发文 + D+14 复盘待办 + SEO 来源流量汇总”。
- 默认会从 publish_log 生成待复盘清单。
- 同时尝试从 Cloudflare GraphQL Analytics 拉取 deepclick.com 的
  `utm_campaign=seo` 流量（按 requestSource=eyeball）。

示例：
  python3 seo_daily_review.py --publish-log ~/.openclaw/logs/deepclick-blog/publish_log.jsonl
"""

import argparse
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ8 = timezone(timedelta(hours=8))
CF_GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"


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


def fetch_cf_seo_traffic(
    zone_id: str,
    token: str,
    host: str,
    utm_key: str,
    utm_value: str,
    start: datetime,
    end: datetime,
):
    """Query Cloudflare GraphQL for traffic matching `utm` params.

    Returns:
        (ok: bool, payload: dict)
        payload includes keys: {kind,count,sources,message,query_used}
    """

    query = '''
    query ($zoneTag: String!, $filter: filter) {
      viewer {
        zones(filter: {zoneTag: $zoneTag}) {
          httpRequestsAdaptiveGroups(filter: $filter, limit: 1) {
            count
            sum {
              visits
            }
          }
        }
      }
    }
    '''

    base_filter = {
        "datetime_geq": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datetime_lt": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clientRequestHTTPHost": host,
        "requestSource": "eyeball",
    }

    # 优先尝试按 query string_like 过滤；部分 schema 可能不支持该字段，需回退。
    candidate_query_filters = [
        ("clientRequestQuery_like", f"%{utm_key}={utm_value}%"),
        ("clientRequestPath", "/contact-sales"),
        ("clientRequestPath_like", "%/contact-sales%"),
        (None, None),
    ]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last_err = ""
    for q_key, q_val in candidate_query_filters:
        filt = dict(base_filter)
        if q_key:
            filt[q_key] = q_val

        payload = {
            "query": query,
            "variables": {
                "zoneTag": zone_id,
                "filter": filt,
            },
        }

        try:
            resp = requests.post(CF_GRAPHQL_URL, json=payload, headers=headers, timeout=30)
        except Exception as e:
            return False, {"message": f"cloudflare request failed: {e}"}

        try:
            data = resp.json()
        except Exception:
            return False, {"message": f"invalid JSON response: {resp.text[:240]}"}

        if data.get("errors"):
            last_err = str(data["errors"][0].get("message", "")) if data.get("errors") else "unknown"
            continue

        zones = (data.get("data") or {}).get("viewer", {}).get("zones", []) or []
        if not zones:
            continue

        groups = zones[0].get("httpRequestsAdaptiveGroups", []) or []
        if not groups:
            return True, {
                "kind": "matched_no_data",
                "count": 0,
                "visits": 0,
                "query_used": q_key,
            }

        # 兜底聚合（通常只有 1 行）
        count = 0
        visits = 0
        for g in groups:
            count += int(g.get("count") or 0)
            s = g.get("sum") or {}
            visits += int(s.get("visits") or 0)

        return True, {
            "kind": "matched",
            "count": count,
            "visits": visits,
            "requests": count,
            "query_used": q_key or "none",
            "raw_count": count,
        }

    # 认证错误优先返回，不要误报成“字段不支持”
    if "authentication" in (last_err or "").lower():
        return False, {
            "message": f"CF GraphQL authentication error: {last_err}",
            "query_used": None,
        }

    return False, {
        "message": f"CF GraphQL field filter not supported. Last error: {last_err}",
        "query_used": None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish-log", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "publish_log.jsonl"))
    ap.add_argument("--out", default=str(Path.home() / ".openclaw" / "logs" / "deepclick-blog" / "daily-review.md"))
    ap.add_argument("--review-days", type=int, default=14)
    ap.add_argument("--traffic-window-days", type=int, default=1)
    ap.add_argument("--traffic-host", default="deepclick.com")
    ap.add_argument("--utm-key", default="utm_campaign")
    ap.add_argument("--utm-value", default="seo")
    ap.add_argument("--cf-zone-id", default=os.getenv("CLOUDFLARE_ZONE_ID", ""))
    ap.add_argument("--cf-token", default=os.getenv("CLOUDFLARE_API_TOKEN", ""))
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

    # SEO traffic section
    lines.append("## SEO 来源流量（deepclick.com / utm_campaign=seo）")
    lines.append("")
    if not args.cf_zone_id or not args.cf_token:
        lines.append("- ⚠️ 未配置 Cloudflare 凭证，无法拉取流量：")
        lines.append("  - `CLOUDFLARE_ZONE_ID`")
        lines.append("  - `CLOUDFLARE_API_TOKEN`（建议仅含 Analytics:Read 权限）")
        lines.append("")
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=max(args.traffic_window_days - 1, 0))
        end = now
        ok, metric = fetch_cf_seo_traffic(
            zone_id=args.cf_zone_id,
            token=args.cf_token,
            host=args.traffic_host,
            utm_key=args.utm_key,
            utm_value=args.utm_value,
            start=start,
            end=end,
        )
        if ok:
            if metric.get("kind") == "matched_no_data":
                lines.append(f"- 时间窗口：{start.strftime('%Y-%m-%d %H:%M')} ～ {end.strftime('%Y-%m-%d %H:%M')} CST")
                lines.append("- 当前未匹配到可计量数据（utm 条件可能没有命中或字段仍在迁移中）")
            elif metric.get("kind") == "matched":
                lines.append(f"- 时间窗口：{start.strftime('%Y-%m-%d %H:%M')} ～ {end.strftime('%Y-%m-%d %H:%M')} CST")
                lines.append(f"- host：`{args.traffic_host}`")
                lines.append(f"- 筛选字段：`{args.utm_key}`=`{args.utm_value}`（过滤键：`{metric.get('query_used') or 'n/a'}`）")
                lines.append(f"- SEO 会话量：**{metric.get('visits') or metric.get('count')}**")
                lines.append(f"- SEO 请求量：**{metric.get('requests') or metric.get('count')}**")
            else:
                lines.append(f"- 查询失败：{metric.get('message')}")
        else:
            lines.append(f"- 查询失败：{metric.get('message')}")
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
