#!/usr/bin/env python3
"""
DeepClick Blog Skill — 初始化配置向导
安装 skill 后运行一次。每个站点只需提供 Application Password，
用户名和站点信息自动从 WordPress REST API 发现。

用法：python3 setup.py
"""

import base64, json, urllib.request, urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "deepclick-blog" / "sites.json"


def discover(url: str, app_password: str) -> dict | None:
    """
    只用 App Password 探测站点信息。
    WordPress REST API 的 Basic Auth 允许用 email 或 login 名 + App Password 直接认证，
    但我们不知道用户名——所以先尝试匿名发现用户名，再用 App Password 验证。
    实际上 WP 支持在 Basic Auth 中用 email 作为用户名。
    """
    url = url.rstrip("/")

    # 第一步：匿名拿 /wp-json/wp/v2/users?roles=administrator 或用 application-passwords 端点
    # 更可靠的方式：直接用 app_password 当密码，email 当用户名（WordPress 支持此形式）
    # 但我们不知道 email，所以先拿站点基本信息
    try:
        req = urllib.request.Request(f"{url}/wp-json/wp/v2/", headers={"User-Agent": "deepclick-blog-setup/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            site_info = json.loads(r.read())
            site_name = site_info.get("name", url)
            site_url = site_info.get("url", url)
    except Exception as e:
        return None, f"无法访问 {url}/wp-json/wp/v2/: {e}"

    # 第二步：枚举常见用户名格式 + App Password 尝试认证
    # WordPress 允许用 email、login name 作为 Basic Auth 用户名
    # 我们让用户只填 App Password，通过 /wp-json/wp/v2/users?context=edit 拿真实用户名
    # 但这需要先有认证... 先尝试用 App Password 本身验证（某些 WP 版本允许用 user_login 或 email）
    # 最直接：询问用户 email，用 email + App Password 验证
    return {"site_name": site_name, "site_url": site_url}, None


def verify_with_email(url: str, email: str, app_password: str) -> tuple[bool, dict]:
    """用 email + App Password 验证，成功后返回用户信息"""
    url = url.rstrip("/")
    token = base64.b64encode(f"{email}:{app_password}".encode()).decode()
    req = urllib.request.Request(
        f"{url}/wp-json/wp/v2/users/me",
        headers={"Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return True, {"name": d.get("name"), "login": d.get("slug"), "email": email}
    except urllib.error.HTTPError as e:
        return False, {"error": f"HTTP {e.code}: {e.read().decode()[:100]}"}
    except Exception as e:
        return False, {"error": str(e)}


def get_categories(url: str, email: str, app_password: str) -> list:
    token = base64.b64encode(f"{email}:{app_password}".encode()).decode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/wp-json/wp/v2/categories?per_page=50",
        headers={"Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []


def main():
    print("🚀 DeepClick Blog Skill — 初始化配置")
    print("配置文件：~/.config/deepclick-blog/sites.json\n")

    existing_cfg = {}
    if CONFIG_PATH.exists():
        existing_cfg = json.loads(CONFIG_PATH.read_text())
        print(f"已有 {len(existing_cfg)} 个站点配置。")

    cfg = dict(existing_cfg)

    # 一次性输入 email（所有站点共用）
    known_email = next((v["user"] for v in existing_cfg.values() if v.get("user")), "")
    email = input(f"WordPress 账号邮箱 [{known_email or '请输入'}]: ").strip() or known_email
    if not email:
        print("❌ 邮箱不能为空")
        return

    print("\n逐站点配置（空行结束）：")
    print("提示：在各站点后台 /wp-admin/profile.php 底部生成 Application Password\n")

    while True:
        site_key = input("站点域名（如 traffictalking.com）: ").strip().rstrip("/")
        if not site_key:
            break

        # 补全 URL
        url = site_key if site_key.startswith("http") else f"https://{site_key}"
        domain = site_key.replace("https://", "").replace("http://", "")

        app_password = input(f"  {domain} 的 Application Password: ").strip()
        if not app_password:
            print("  ⚠️  已跳过")
            continue

        print("  验证中...", end=" ", flush=True)
        ok, user_info = verify_with_email(url, email, app_password)
        if not ok:
            print(f"❌ {user_info.get('error')}")
            continue
        print(f"✅ 用户: {user_info['name']}")

        # 分类选择
        cats = get_categories(url, email, app_password)
        en_cat = existing_cfg.get(domain, {}).get("en_category")
        zh_cat = existing_cfg.get(domain, {}).get("zh_category")

        if cats:
            print("  分类列表：")
            for c in cats[:20]:
                print(f"    [{c['id']}] {c['name']}")
            v = input(f"  英文分类 ID [{en_cat or '留空'}]: ").strip()
            if v: en_cat = int(v)
            v = input(f"  中文分类 ID [{zh_cat or '留空'}]: ").strip()
            if v: zh_cat = int(v)

        cfg[domain] = {
            "url": url,
            "user": email,
            "app_password": app_password,
            "en_category": en_cat,
            "zh_category": zh_cat,
        }
        print(f"  ✅ {domain} 已保存\n")

    if not cfg:
        print("未配置任何站点，退出。")
        return

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"\n✅ 已保存 {len(cfg)} 个站点到 {CONFIG_PATH}")

    print("\n连通性检查：")
    for domain, c in cfg.items():
        ok, info = verify_with_email(c["url"], c["user"], c["app_password"])
        print(f"  {'✅' if ok else '❌'} {domain}: {info.get('name') or info.get('error')}")


if __name__ == "__main__":
    main()
