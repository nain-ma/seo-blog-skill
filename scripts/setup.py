#!/usr/bin/env python3
"""
DeepClick Blog Skill — 初始化配置向导
安装 skill 后运行一次，配置各站点的 WordPress Application Password。

用法：python3 setup.py
"""

import base64, json, sys, urllib.request, urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "deepclick-blog" / "sites.json"


def test_connection(url: str, user: str, password: str) -> tuple[bool, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/wp-json/wp/v2/users/me",
        headers={"Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return True, d.get("name", "unknown")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 401:
            return False, "认证失败：请检查用户名和 Application Password"
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def get_categories(url: str, user: str, password: str) -> list[dict]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/wp-json/wp/v2/categories?per_page=50",
        headers={"Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []


def setup_site(site_key: str, existing: dict = None) -> dict | None:
    print(f"\n{'='*50}")
    print(f"配置站点: {site_key}")
    print(f"{'='*50}")

    default_url = existing.get("url", f"https://{site_key}") if existing else f"https://{site_key}"
    default_user = existing.get("user", "") if existing else ""

    url = input(f"站点 URL [{default_url}]: ").strip() or default_url
    user = input(f"WordPress 用户名 [{default_user}]: ").strip() or default_user

    print("\n生成 Application Password：")
    print(f"  1. 打开 {url}/wp-admin/profile.php")
    print("  2. 滚到底部 → Application Passwords")
    print("  3. 输入名称（如 deepclick-blog）→ 生成 → 复制")
    password = input("粘贴 Application Password: ").strip()

    if not password:
        print("⚠️  已跳过")
        return existing

    print("  验证连接中...", end=" ", flush=True)
    ok, msg = test_connection(url, user, password)
    if not ok:
        print(f"❌ {msg}")
        retry = input("重试? (y/N): ").strip().lower()
        if retry == "y":
            return setup_site(site_key, existing)
        return existing
    print(f"✅ 连接成功，用户: {msg}")

    # 获取并展示分类
    cats = get_categories(url, user, password)
    en_cat = existing.get("en_category") if existing else None
    zh_cat = existing.get("zh_category") if existing else None

    if cats:
        print("\n  可用分类：")
        for c in cats[:20]:
            print(f"    [{c['id']}] {c['name']}")
        en_cat_input = input(f"  英文博客分类 ID [{en_cat or '留空'}]: ").strip()
        zh_cat_input = input(f"  中文博客分类 ID [{zh_cat or '留空'}]: ").strip()
        if en_cat_input:
            en_cat = int(en_cat_input)
        if zh_cat_input:
            zh_cat = int(zh_cat_input)

    return {
        "url": url,
        "user": user,
        "app_password": password,
        "en_category": en_cat,
        "zh_category": zh_cat,
    }


def main():
    print("🚀 DeepClick Blog Skill — 初始化配置")
    print("此向导帮你配置各 WordPress 站点的发布权限。")
    print("配置文件保存到: ~/.config/deepclick-blog/sites.json\n")

    # 加载已有配置
    existing_cfg = {}
    if CONFIG_PATH.exists():
        existing_cfg = json.loads(CONFIG_PATH.read_text())
        print(f"检测到已有配置，共 {len(existing_cfg)} 个站点：")
        for k, v in existing_cfg.items():
            ok, msg = test_connection(v["url"], v["user"], v["app_password"])
            status = f"✅ {msg}" if ok else f"❌ {msg}"
            print(f"  {k}: {status}")
        print()
        mode = input("(a) 新增站点  (r) 重新配置已有站点  (q) 退出 [a]: ").strip().lower() or "a"
        if mode == "q":
            return
    else:
        mode = "a"

    cfg = dict(existing_cfg)

    if mode == "a":
        print("\n输入要添加的站点域名（如 traffictalking.com），空行结束：")
        while True:
            site_key = input("站点: ").strip().rstrip("/")
            if not site_key:
                break
            site_data = setup_site(site_key, cfg.get(site_key))
            if site_data:
                cfg[site_key] = site_data

    elif mode == "r":
        print("\n选择要重新配置的站点：")
        keys = list(existing_cfg.keys())
        for i, k in enumerate(keys):
            print(f"  [{i+1}] {k}")
        selection = input("输入序号（逗号分隔，如 1,3）: ").strip()
        indices = [int(x.strip()) - 1 for x in selection.split(",") if x.strip().isdigit()]
        for idx in indices:
            if 0 <= idx < len(keys):
                site_data = setup_site(keys[idx], existing_cfg[keys[idx]])
                if site_data:
                    cfg[keys[idx]] = site_data

    # 保存
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"\n✅ 配置已保存：{CONFIG_PATH}")
    print(f"   共 {len(cfg)} 个站点已配置\n")

    # 最终验证
    print("最终连通性检查：")
    for site, c in cfg.items():
        ok, msg = test_connection(c["url"], c["user"], c["app_password"])
        print(f"  {'✅' if ok else '❌'} {site}: {msg}")


if __name__ == "__main__":
    main()
