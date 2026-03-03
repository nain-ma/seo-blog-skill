# WordPress 双语发布技术参考（Polylang Pro + Rank Math SEO）

## 前置配置（只需一次）

### 1. Application Password 生成
WordPress Admin → Users → Edit Profile → 滚动到 "Application Passwords" → 输入名称 → 添加 → **立即复制**

### 2. SEO 插件说明
**使用 Rank Math SEO**（当前站点配置）：字段默认已对 REST API 开放，**无需修改 functions.php**。

| 用途 | 字段名 |
|------|--------|
| SEO 标题 | `rank_math_title` |
| Meta 描述 | `rank_math_description` |
| 焦点关键词 | `rank_math_focus_keyword` |

> 如果改用 Yoast SEO，需要在 functions.php 中手动注册字段（见备注），键名为：
> `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw`

---

## 认证方式

```python
import base64

def get_auth_header(username: str, app_password: str) -> str:
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode()).decode()
    return f"Basic {token}"
```

---

## Polylang Pro 双语发布流程

### 步骤 1：发布英文版

```python
import requests

def publish_post(wp_url, auth_header, payload, lang, translations=None):
    params = {"lang": lang}
    if translations:
        params.update({f"translations[{k}]": v for k, v in translations.items()})

    response = requests.post(
        f"{wp_url}/wp-json/wp/v2/posts",
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        json=payload,
        params=params
    )
    response.raise_for_status()
    return response.json()

# 发布英文版
en_post = publish_post(
    wp_url="https://yoursite.com",
    auth_header=get_auth_header("admin", "xxxx xxxx xxxx xxxx xxxx xxxx"),
    payload={
        "title": "Why Meta Ads Have High CTR But Low CVR",
        "content": "<p>Article content here...</p>",
        "excerpt": "Short excerpt here",
        "status": "publish",
        "slug": "meta-ads-high-ctr-low-cvr-2025",
        "categories": [3],
        "meta": {
            "rank_math_title": "Why Meta Ads Have High CTR But Low CVR [2025]",
            "rank_math_description": "Your Meta ads get clicks but not conversions? Here are the 5 post-click friction points killing your CVR — and how to fix each one.",
            "rank_math_focus_keyword": "meta ads high ctr low cvr"
        }
    },
    lang="en"
)
en_post_id = en_post["id"]
```

### 步骤 2：发布中文版并关联翻译

```python
zh_post = publish_post(
    wp_url="https://yoursite.com",
    auth_header=auth_header,
    payload={
        "title": "为什么 Meta 广告点击率高但转化率低？",
        "content": "<p>文章内容...</p>",
        "excerpt": "摘要",
        "status": "publish",
        "slug": "meta-ads-high-ctr-low-cvr-2025-zh",
        "categories": [4],
        "meta": {
            "rank_math_title": "Meta 广告高点击低转化？5 个关键原因分析 [2025]",
            "rank_math_description": "Meta 广告点击率不错但转化率低？本文分析 5 个 post-click 流失节点及修复方案，帮助降低 CPA。",
            "rank_math_focus_keyword": "Meta 广告高点击低转化"
        }
    },
    lang="zh",  # 对应 Polylang 中配置的中文语言代码
    translations={"en": en_post_id}  # 关键：关联英文版
)
zh_post_id = zh_post["id"]
```

发布成功后，Polylang 会自动将两篇文章标记为互为翻译。

---

## 获取分类/标签 ID

```bash
# 列出所有分类
curl https://yoursite.com/wp-json/wp/v2/categories?per_page=100 \
  -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx"

# 列出所有标签
curl https://yoursite.com/wp-json/wp/v2/tags?per_page=100 \
  -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx"

# 按名称搜索
curl "https://yoursite.com/wp-json/wp/v2/categories?search=blog" \
  -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx"
```

---

## 验证翻译关联

```bash
curl "https://yoursite.com/wp-json/wp/v2/posts/{en_post_id}" \
  -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('translations'), d.get('lang'))"
# 应输出类似: {'en': 101, 'zh': 102} en
```

---

## 常见错误处理

| 错误码 | 原因 | 解决方案 |
|--------|------|---------|
| 401 | Application Password 无效 | 重新生成，注意带空格原样粘贴 |
| 403 | 用户权限不足 | 确保用户是 Editor 或 Admin 角色 |
| 400 `term_exists` | 分类 ID 不存在 | 检查分类 ID 是否正确 |
| 400 lang parameter | Polylang Free 版不支持 | 升级到 Polylang Pro |
| Rank Math meta 不生效 | Rank Math 版本过旧 | 升级到最新版本，字段默认开放 |

---

## 注意事项

1. **Polylang 语言代码**：确认与你在 Polylang → Languages 中配置的 slug 一致（可能是 `zh`、`zh-hans`、`zh_CN` 等）
2. **发布顺序**：必须先发英文，拿到 EN post ID 后再发中文并关联
3. **分类独立**：Polylang 中英文分类是独立的，需要分别维护 ID
4. **草稿模式**：发布前可先用 `"status": "draft"` 预览，确认内容正确后再改为 `"publish"`
