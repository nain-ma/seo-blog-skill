---
name: deepclick-blog
description: 为 DeepClick 生成 SEO 优化的中英双语博客并发布到 WordPress。从行业雷达 API 获取信号，转化为面向增长负责人和广告买手的内容。当用户提到"写博客"、"发一篇文章"、"内容营销"、"DeepClick 博客"、"生成博文"、"行业热点发文"、"blog post"、"content marketing for DeepClick"时使用此 skill。支持自动模式（拉取最新 digest 选题）和手动模式（用户指定话题）。
---

# DeepClick 双语博客生成 Skill

## 配置检查（每次调用时）

检查配置文件是否存在：

```bash
python3 -c "
import json; from pathlib import Path
p = Path('~/.config/deepclick-blog/sites.json').expanduser()
print('ok' if p.exists() and json.loads(p.read_text()) else 'missing')
"
```

输出 `missing` 时，进入初始化流程。

### 初始化流程

**第一步**：询问 WordPress 账号邮箱。

**第二步**：询问各站点的 Application Password（进入站点后台 → Users → Profile → 底部 Application Passwords → 生成 → 复制）。

**第三步**：Agent 自动验证连接并拉取分类列表：

```bash
python3 -c "
import base64, json, urllib.request
email = '{EMAIL}'; url = '{URL}'; pwd = '{APP_PASSWORD}'
token = base64.b64encode(f'{email}:{pwd}'.encode()).decode()
headers = {'Authorization': f'Basic {token}'}

req = urllib.request.Request(f'{url}/wp-json/wp/v2/users/me', headers=headers)
me = json.loads(urllib.request.urlopen(req, timeout=10).read())
print('USER:' + me.get('name',''))

req2 = urllib.request.Request(f'{url}/wp-json/wp/v2/categories?per_page=100', headers=headers)
cats = json.loads(urllib.request.urlopen(req2, timeout=10).read())
for c in cats:
    print(f'CAT:{c[\"id\"]}:{c[\"name\"]}')
"
```

**第四步**：展示分类列表，确认英文/中文分类 ID。

**第五步**：写入配置：

```bash
python3 -c "
import json; from pathlib import Path
p = Path('~/.config/deepclick-blog/sites.json').expanduser()
cfg = json.loads(p.read_text()) if p.exists() else {}
cfg['{DOMAIN}'] = {
    'url': '{URL}', 'user': '{EMAIL}', 'app_password': '{APP_PASSWORD}',
    'en_category': {EN_CAT_ID}, 'zh_category': {ZH_CAT_ID}
}
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(cfg, indent=2))
print('saved')
"
```

---

## 调用方式

**交互模式**：正常工作流，生成文章后展示内容等用户确认，再发布。

**批量/定时任务模式**：消息含 `--batch` 时，全程自动发布无需确认。

```
发布 DeepClick 博客 [参数]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `--sites <域名列表>` | 指定发布站点，逗号分隔 | `--sites traffictalking.com` |
| `--count <N>` | 发布文章数（默认 1），每篇必须不同话题 | `--count 2` |
| `--topic <话题>` | 手动指定话题（跳过自动搜索） | `--topic "Meta Ads CVR 2026"` |
| `--batch` | 批量模式，直接发布不等确认 | `--batch` |

---

## 工作流程

### 步骤 1：选题（Agent 自主搜索热点）

**自动模式**（无用户指定话题时）：

Agent 自己通过 WebSearch 搜索最近 7 天的行业热点讨论，搜索范围：

1. **必搜关键词组**（至少搜 3 组，选最有料的）：
   - `"Meta ads" OR "Facebook ads" new update {current_month} {current_year}`
   - `"post-click" OR "landing page" conversion optimization {current_year}`
   - `"Meta ads" CPA OR CVR OR ROAS changes {current_year}`
   - `"Facebook ads" best practices OR strategy {current_month} {current_year}`

2. **补充搜索**（根据前面结果扩展）：
   - Twitter/X、Reddit r/PPC、r/FacebookAds 上的热帖
   - Search Engine Land、AdExchanger、Jon Loomer 等行业媒体近期文章

3. **选题规则**：
   - 每次选 **1 个话题**写 1 篇文章
   - 如果是批量发布（`--count 2` 或以上），每篇必须是**不同的话题**
   - 选择标准：有真实讨论热度、与 DeepClick 价值（CVR/CPA/post-click）能自然关联

**话题去重**（防止重复发文）：

去重依据：`~/.openclaw/logs/deepclick-blog/publish_log.jsonl`
- 读取最近 30 天的发布记录，提取已发布的 `article_title` 和 `primary_keyword`
- 新选题不能与已发布文章的关键词高度重叠
- 如果搜索到的热点已经写过，换一个角度或跳过

**表格导入补充（附加来源）：**
- 若有人工提供的 SEO 选题表（如 `SEO.xlsx`），已统一落库到：
  - `deepclick-digests/seo-topic-seed-active.json`
  - `deepclick-digests/seo-keyword-seed-2026-03-11.json`
- 选题时可优先从该“选题池”补充候选，再与雷达/搜索信号合并（或二选一）

**手动模式**：用户提供话题或内容，跳过搜索。

---

### 步骤 2：确定博客角度

选择一个清晰角度，每篇聚焦**一个核心问题**：

| 类型 | 示例标题 |
|------|---------|
| 新闻分析 | "How [Meta Change] Will Impact Your Ad CVR in 2026" |
| 操作指南 | "5 Post-Click Fixes That Lower Meta Ads CPA by 30%" |
| 数据洞察 | "Meta Ads CVR Benchmarks 2026: Where Do You Stand?" |
| 问题诊断 | "Why Your Facebook Ads Have High CTR But Low CVR" |

---

### 步骤 3：生成文章

> ⚠️ **年份**：标题和 Slug 使用当前年份（2026），不要硬编码。

**确定 SEO 元数据**：

```
PRIMARY_KEYWORD: [主关键词，英文]
SEO_TITLE_EN: [50-60字符，含主关键词]
META_DESC_EN: [150-160字符]
SLUG_EN: [关键词-年份，如 meta-ads-post-click-optimization-2026]

SEO_TITLE_ZH: [中文标题]
META_DESC_ZH: [中文 meta 描述]
SLUG_ZH: [SLUG_EN + "-zh"]
```

**文章结构（英文和中文都遵循）**：

> ⚠️ WordPress 页面中 `post title` 已作为 H1，**正文禁止再写 H1**。

```
[导言] 痛点共鸣（2-3句）→ 承诺价值 → 预告结构

[顶部 CTA - 文字形式，导言后第1-2段]

## H2: 核心问题/现状
### H3: 数据/细节

## H2: 为什么这影响你的转化表现

## H2: 解决方案（1-3个）
### H3: 方法一
### H3: 方法二

[中部 CTA - Callout 形式]

## H2: 进阶洞察或常见误区

## H2: 总结 + 可执行建议（3-5条）

[底部 CTA Block]
```

**CTA 规范**：

顶部（文字链接）：
```
*Struggling with high CTR but low CVR on Meta ads?
→ See how DeepClick diagnoses your post-click drop-offs — [Free Audit](https://deepclick.com/contact-sales?utm_source=seo-blog&utm_medium=organic-content&utm_campaign=seo&utm_content=contact-sales)*
```

中部（Callout Box）：
```
> **Industry Average CVR: 1.57% | Top performers: 3-5%**
> Is your Meta Ads CVR above or below average? DeepClick shows you exactly where
> you're losing clicks — and fixes it automatically.
> → [See Your Post-Click Score](https://deepclick.com/contact-sales?utm_source=seo-blog&utm_medium=organic-content&utm_campaign=seo&utm_content=contact-sales)
```

底部 CTA（英文）：
```
---
**Stop losing conversions after the click.**

DeepClick helps Meta advertisers fix post-click drop-offs and improve CVR by 30%+
through automated re-engagement and post-click link optimization.

→ [Book a Free Demo](https://deepclick.com/contact-sales?utm_source=seo-blog&utm_medium=organic-content&utm_campaign=seo&utm_content=contact-sales)
---
```

底部 CTA（中文）：
```
---
**广告有点击，但转化一直上不去？**

DeepClick 专注 Meta 广告点击后链路优化，通过回流、再曝光与落地页优化，
帮助出海广告团队平均提升 CVR 30%+，降低 CPA。

→ [预约免费诊断](https://deepclick.com/contact-sales?utm_source=seo-blog&utm_medium=organic-content&utm_campaign=seo&utm_content=contact-sales)
---
```

**字数要求（唯一质量门槛）**：
- 英文：≥ 800 词（操作指南类 ≥ 1200 词）
- 中文：≥ 600 字

字数不足时，扩展具体步骤、增加示例或数据分析，直到达标。

---

### 步骤 4：发布到 WordPress

**站点列表**（sites.json 中已配置即可）：

| 站点 | 定位 |
|------|------|
| traffictalking.com | DeepClick 营销博客（默认） |
| googlepwa.blog | PWA 技术站 |
| androidpwa.com | 安卓 PWA 出海站 |

**默认行为**：用户未指定 `--sites` 时，发布到全部三个站。

> ⚠️ **注意**：只有与站点定位匹配的内容才发布到该站。Meta Ads 相关内容三站都发；PWA/推送专题只发 googlepwa.blog 和 androidpwa.com。

**发布状态**：
- 交互模式：先展示内容给用户确认，确认后再发布
- 批量/cron 模式（含 `--batch`）：直接发布

**对每个目标站点，依次执行**：

发布英文版：
```bash
python3 ~/.openclaw/workspace-blogger-lumi/skills/seo-blog-skill/scripts/publish.py \
  --site {SITE_DOMAIN} \
  --lang en \
  --title "EN_TITLE" \
  --content "EN_CONTENT_HTML" \
  --excerpt "EN_EXCERPT" \
  --slug "SLUG_EN" \
  --status publish \
  --meta-title "SEO_TITLE_EN" \
  --meta-desc "META_DESC_EN" \
  --focus-kw "PRIMARY_KEYWORD"
```

发布中文版：
```bash
python3 ~/.openclaw/workspace-blogger-lumi/skills/seo-blog-skill/scripts/publish.py \
  --site {SITE_DOMAIN} \
  --lang zh \
  --title "ZH_TITLE" \
  --content "ZH_CONTENT_HTML" \
  --excerpt "ZH_EXCERPT" \
  --slug "SLUG_ZH" \
  --status publish \
  --meta-title "SEO_TITLE_ZH" \
  --meta-desc "META_DESC_ZH" \
  --focus-kw "ZH_FOCUS_KW"
```

返回 JSON 中提取 `url`（访问链接）和 `edit_url`（后台编辑链接）。

**记录发布日志**（每次发布写入）：`~/.openclaw/logs/deepclick-blog/publish_log.jsonl`

---

### 步骤 5：输出结果

发布完成后输出：

```
✅ 发布完成

英文版：{en_post_url}
中文版：{zh_post_url}

标题：{title}
关键词：{primary_keyword}
```

---

## 参考文件

- `references/seo-structure.md` — SEO 博客结构详细模板和关键词策略
- `references/deepclick-positioning.md` — DeepClick 产品定位和叙事基准
- `references/wordpress-publish.md` — WordPress REST API 技术文档
