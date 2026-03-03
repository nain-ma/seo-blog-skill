---
name: deepclick-blog
description: >
  为 DeepClick（Meta/FB 广告 post-click 优化平台）生成 SEO 优化的中英双语博客文章并自动发布到 WordPress。
  从行业雷达 API 获取最新行业信号，转化为面向增长负责人和广告买手的高价值内容，
  通过内容营销持续产生 demo 预约线索。
  当用户提到"写博客"、"发一篇文章"、"内容营销"、"DeepClick 博客"、"生成博文"、
  "行业热点发文"、"blog post"、"content marketing for DeepClick"时，主动使用此 skill。
  支持两种模式：(1) 自动模式 — 拉取最新 8h digest 自动选题；(2) 手动模式 — 用户指定话题或提供原始内容。
---

# DeepClick 双语博客生成 Skill

## 配置检查（第一步）

发布前需要以下配置（从环境变量或用户提供）：

| 变量                        | 说明                      | 示例                            |
| --------------------------- | ------------------------- | ------------------------------- |
| `DEEPCLICK_WP_URL`          | WordPress 站点地址        | `https://traffictalking.com`    |
| `DEEPCLICK_WP_USER`         | WordPress 用户名          | `admin`                         |
| `DEEPCLICK_WP_APP_PASSWORD` | Application Password      | `xxxx xxxx xxxx xxxx xxxx xxxx` |
| `DEEPCLICK_WP_EN_CATEGORY`  | 英文博客分类 ID           | `132592`（Conversion Insights）  |
| `DEEPCLICK_WP_ZH_CATEGORY`  | 中文博客分类 ID           | `132594`（转化洞察）             |

如果用户没有提供配置，先询问，或提示他们将配置加入环境变量。

> **WordPress 前置要求**（只需配置一次）：
>
> 1. WordPress Application Password（Users → Profile → Application Passwords）
> 2. Rank Math SEO 已安装（字段默认开放，无需额外配置）
> 3. 在后台确认英文/中文分类 ID（wp-json/wp/v2/categories）

---

## 工作流程

### 步骤 1：获取行业信号

**自动模式**（无用户指定话题时）：

```
GET https://radar.qiliangjia.one/api/digests?type=8h&limit=3&offset=0
```

解析返回的 `content`（Markdown 格式），从 `## Signals` 区块提取各条信号。
选择 **2-3 个**与 DeepClick 定位最相关的信号（优先级见下方过滤规则）。

**手动模式**：用户直接提供话题、链接或原始信号内容，跳过 API 调用。

**信号相关性过滤规则**（按优先级排序）：

1. Meta/Facebook 广告政策、功能变化、算法更新
2. 转化率优化、post-click、落地页、CRO 相关讨论
3. 广告成本上涨、CPA 压力、ROI 下降
4. Re-engagement、re-targeting、PWA、推送相关
5. 竞品动态（AppsFlyer、Adjust、Kochava、分析工具）
6. 电商广告投放执行层问题（CVR、素材、归因）

不相关的信号（履约、库存、客服等）不纳入文章。

---

### 步骤 2：确定博客角度

基于筛选出的信号，选择一个清晰的文章角度。角度类型：

| 类型     | 适用场景            | 示例标题格式                                                  |
| -------- | ------------------- | ------------------------------------------------------------- |
| 新闻分析 | Meta 政策/功能变化  | "How [Meta Change] Will Impact Your Ad CVR in [CURRENT_YEAR]"   |
| 操作指南 | 具体优化问题        | "5 Post-Click Fixes That Lower Meta Ads CPA by 30%"             |
| 数据洞察 | Benchmark、趋势数据 | "Meta Ads CVR Benchmarks [CURRENT_YEAR]: Where Do You Stand?"   |
| 问题诊断 | 常见痛点            | "Why Your Facebook Ads Have High CTR But Low CVR"               |

每篇文章聚焦**一个核心角度**，不要把所有信号都塞进一篇文章。

---

### 步骤 3：生成 SEO 计划

在写正文之前，先确定：

> **⚠️ 年份**：标题和 Slug 中的年份请使用**当前年份**（从系统日期或 MEMORY 中获取）。不要硬编码 2025。

```
CURRENT_YEAR: [当前年份，如 2026]
PRIMARY_KEYWORD: [主关键词，英文，如 "meta ads post-click optimization"]
SEO_TITLE_EN: [50-60字符，含主关键词]
META_DESC_EN: [150-160字符，痛点+价值主张]
SLUG_EN: [url友好格式，如 "meta-ads-post-click-optimization-{CURRENT_YEAR}"]
FOCUS_KW_EN: [与 PRIMARY_KEYWORD 一致或略短]

SEO_TITLE_ZH: [中文标题，含核心关键词]
META_DESC_ZH: [中文 meta 描述]
SLUG_ZH: [英文 slug + "-zh" 后缀，如 "meta-ads-post-click-optimization-{CURRENT_YEAR}-zh"]
FOCUS_KW_ZH: [中文焦点关键词]
```

---

### 步骤 4：生成文章内容

参考 `references/seo-structure.md` 中的文章结构模板。

**英文版写作要点**：

- 面向全球 Meta Ads 从业者（广告买手、增长 PM、DTC 品牌营销）
- 语言：直接、数据驱动、实操性强；避免过度推销
- 字数：新闻分析 800-1200 词；操作指南 1500-2500 词
- 内嵌 3 个 CTA（见 CTA 规范）

**中文版写作要点**：

- 面向出海品牌广告团队、代理公司买手、增长负责人
- **不是机械翻译**：用中文市场惯用表达，可增加本地化案例或数据参照
- 核心论点和结构与英文版保持一致，但行文风格适配中文读者
- 同样嵌入 3 个 CTA

**文章结构（两种语言均遵循）**：

```
[H1] 核心关键词 + 用户利益（≤60字/符）

[导言] 痛点共鸣（2-3句）→ 承诺价值 → 预告结构

[轻量 CTA - 文章顶部，文字形式]
"Struggling with high CTR but low CVR on Meta? → See how DeepClick diagnoses post-click drop-offs →"

## H2: 核心问题/现状（行业信号引入）
### H3: 数据/具体细节

## H2: 为什么这会影响你的转化表现
### H3: 具体机制分析

## H2: [解决方案/操作建议]（1-3个）
### H3: 方法一（具体步骤）
### H3: 方法二（具体步骤）

[中部 CTA - Callout Box 形式]
数据对比 + 工具价值 → "Run Free Post-Click Audit →"

## H2: 进阶洞察或常见误区

## H2: 总结 + 行动清单（3-5条可执行建议）

[底部 CTA Block]
```

**CTA 规范**：

| 位置                      | 形式           | 文案方向                        |
| ------------------------- | -------------- | ------------------------------- |
| 顶部（文章开始后 1-2 段） | 纯文字超链接   | 引发共鸣 + 指向痛点解决方案     |
| 中部（关键洞察后）        | Callout/Banner | 数据对比 + 免费审计/资源        |
| 底部（文章结尾）          | 完整 CTA Block | 价值主张 + "Book a Demo" 主行动 |

底部 CTA 模板（英文）：

```
---
**Stop losing conversions after the click.**

DeepClick helps Meta advertisers fix post-click drop-offs and improve CVR by 30%+
through automated re-engagement and post-click link optimization.

→ [Book a Free Demo](https://deepclick.com?utm_source=blog&utm_medium=content&utm_campaign=seo)
---
```

底部 CTA 模板（中文）：

```
---
**广告有点击，但转化一直上不去？**

DeepClick 专注 Meta 广告点击后链路优化，通过回流、再曝光与落地页优化，
帮助出海广告团队平均提升 CVR 30%+，降低 CPA。

→ [预约免费诊断](https://deepclick.com?utm_source=blog&utm_medium=content&utm_campaign=seo)
---
```

---

### 步骤 5：发布到 WordPress

**使用 wpcom-mcp content-authoring 工具发布**（已内置认证，无需 Application Password）。

站点 ID：`247107897`（traffictalking.com）
英文分类 ID：`132592`（Conversion Insights）
中文分类 ID：`132594`（转化洞察）

**⚠️ wpcom-mcp 已知限制（截至 2026-03）**：

| 参数 | 问题 | 解决方案 |
| --- | --- | --- |
| `categories` | 传数组 `[132592]` 报错；改传**单个整数** `132592`，WP 会自动处理 | `"categories": 132592`（无方括号） |
| `meta`（SEO 字段） | 传对象时报错，无法通过 MCP 设置 | 发布后在 WP 后台 Rank Math 手动设置 |
| `title` / `content` / `excerpt` | **必须直接传字符串**，不要用 `{"raw": "..."}` 对象格式 | 正确示例：`"title": "My Title"` |

**步骤 5.1 - 发布英文版（先发 draft，确认后改 publish）**：

```
operation: posts.create
wpcom_site: 247107897
params:
  title: "EN_TITLE（字符串，非对象）"
  content: "EN_CONTENT_HTML"
  excerpt: "EN_EXCERPT"
  status: "draft"
  slug: SLUG_EN
```

**步骤 5.2 - 发布中文版**：

```
operation: posts.create
wpcom_site: 247107897
params:
  title: "ZH_TITLE"
  content: "ZH_CONTENT_HTML"
  excerpt: "ZH_EXCERPT"
  status: "draft"
  slug: SLUG_ZH
```

**步骤 5.3 - 确认内容后改为 publish**：

```
operation: posts.update
wpcom_site: 247107897
params:
  id: POST_ID
  status: "publish"
```

**发布成功后，向用户报告**：

```
✅ 博客已发布
- 英文版：{en_post_url}（Edit: {en_edit_url}）
- 中文版：{zh_post_url}（Edit: {zh_edit_url}）
- 主关键词：{primary_keyword}
- 信号来源：{signal_source}
```

**步骤 5.4 - 提醒用户在 WP 后台手动完成**（因 MCP 限制）：

```
📌 还需手动操作：
- 英文版分类：Posts → Edit → Category → "Conversion Insights"（ID: 132592）
- 中文版分类：Posts → Edit → Category → "转化洞察"（ID: 132594）
- Rank Math 焦点关键词：Rank Math 面板 → Focus Keyword → {FOCUS_KW_EN/ZH}
  编辑链接：https://traffictalking.com/wp-admin/post.php?post={post_id}&action=edit
```

---

## 质量检查清单（发布前自查）

- [ ] 文章核心论点是否能回答"这对我的 CVR/CPA 有什么影响"
- [ ] H1 是否包含主关键词，且≤60字符
- [ ] Meta description 是否在 150-160 字符范围内
- [ ] 是否有 3 个 CTA（顶/中/底）
- [ ] 底部 CTA 是否有明确的 Demo 链接
- [ ] 中文版是否自然流畅（非机器翻译语感）
- [ ] Slug 是否 URL 友好（全小写，连字符分隔）

---

## 参考文件

- `references/seo-structure.md` — SEO 博客结构详细模板和关键词策略
- `references/wordpress-publish.md` — WordPress REST API 完整技术文档（Polylang Pro + Yoast）
- `references/deepclick-positioning.md` — DeepClick 产品定位和叙事基准
