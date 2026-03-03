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

**发布方式**：直接调用 WordPress REST API（Basic Auth + Application Password），不依赖 wpcom-mcp。

### Credentials 配置文件

路径：`~/.config/deepclick-blog/sites.json`

```json
{
  "traffictalking.com": {
    "url": "https://traffictalking.com",
    "user": "your_username",
    "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
    "en_category": 132592,
    "zh_category": 132594
  },
  "googlepwa.blog": {
    "url": "https://googlepwa.blog",
    "user": "your_username",
    "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
    "en_category": null,
    "zh_category": null
  },
  "androidpwa.com": {
    "url": "https://androidpwa.com",
    "user": "your_username",
    "app_password": "xxxx xxxx xxxx xxxx xxxx xxxx",
    "en_category": null,
    "zh_category": null
  }
}
```

配置文件不存在时，引导用户创建：
1. WordPress Admin → Users → Edit Profile → Application Passwords → 输入名称 → 生成 → **立即复制**
2. 创建 `~/.config/deepclick-blog/` 目录，按上方格式填写 sites.json
3. Rank Math SEO 已安装即可，无需额外配置

**验证配置**：
```bash
python3 ~/.claude/skills/deepclick-blog/scripts/publish.py --help
```

---

## 调用方式与参数

**交互模式**（用户直接对话）：正常工作流，草稿发布后等用户确认再 publish。

**批量/定时任务模式**（openclaw cron 调用）：识别以下 message 格式，自动执行全流程无需确认。

消息格式：

```
发布 DeepClick 博客 [参数]
```

| 参数                 | 说明                                | 示例                                        |
| -------------------- | ----------------------------------- | ------------------------------------------- |
| `--sites <域名列表>` | 指定发布站点，逗号分隔              | `--sites traffictalking.com,googlepwa.blog` |
| `--count <N>`        | 每个站点发布文章数（默认 1）        | `--count 2`                                 |
| `--topic <话题>`     | 手动指定话题（跳过信号 API）        | `--topic "Meta Ads CVR 2026"`               |
| `--batch`            | 批量模式标记，直接 publish 不等确认 | `--batch`                                   |

openclaw cron 推荐配置示例：

```
openclaw agent --message "发布 DeepClick 博客 --batch --sites traffictalking.com" --json
```

**识别批量模式的规则**：message 中含 `--batch`，或来源为 cron job（无交互上下文），则全程自动 publish，不等用户确认。

---

## 工作流程

### 步骤 1：获取行业信号

**自动模式**（无用户指定话题时）：

```
GET https://radar.qiliangjia.one/api/digests?type=daily&limit=3&offset=0
```

解析返回的 `content`（Markdown 格式），从 `## Signals` 区块提取各条信号。
选择 **2-3 个**与 DeepClick 定位最相关的信号（优先级见下方过滤规则）。

**信号去重**（定时任务模式下防止重复发文）：

去重状态文件路径：`~/logs/deepclick-blog/.used-signals.json`
格式：`{"urls": ["https://...", ...], "updated_at": "2026-03-03T14:00:00Z"}`

- 拉取信号后，过滤掉 `.used-signals.json` 中已存在的 URL
- 发布完成后，将本次使用的信号 URL 追加到该文件
- 文件不存在时自动创建；文件中超过 200 条时，清除 30 天前的条目

**手动模式**：用户直接提供话题、链接或原始信号内容，跳过 API 调用，跳过去重检查。

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
| 新闻分析 | Meta 政策/功能变化  | "How [Meta Change] Will Impact Your Ad CVR in [CURRENT_YEAR]" |
| 操作指南 | 具体优化问题        | "5 Post-Click Fixes That Lower Meta Ads CPA by 30%"           |
| 数据洞察 | Benchmark、趋势数据 | "Meta Ads CVR Benchmarks [CURRENT_YEAR]: Where Do You Stand?" |
| 问题诊断 | 常见痛点            | "Why Your Facebook Ads Have High CTR But Low CVR"             |

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

**直接调用 WP REST API**，通过 `scripts/publish.py` 执行，无需 wpcom-mcp。

**支持站点**（sites.json 中已配置即可）：

| 站点               | 定位               | 英文分类 ID                     | 中文分类 ID          |
| ------------------ | ------------------ | ------------------------------- | -------------------- |
| traffictalking.com | DeepClick 营销博客 | `132592`（Conversion Insights） | `132594`（转化洞察） |
| googlepwa.blog     | PWA 技术站         | 待配置                          | 待配置               |
| androidpwa.com     | 安卓 PWA 出海站    | 待配置                          | 待配置               |

用户未指定站点时，默认发布到 **traffictalking.com**。

**发布状态策略**：
- **交互模式**：先发 `draft`，输出预览链接，等用户确认后再改为 `publish`
- **批量/cron 模式**（含 `--batch`）：直接发 `publish`

**步骤 5.1 - 发布英文版**：

```bash
python3 ~/.claude/skills/deepclick-blog/scripts/publish.py \
  --site traffictalking.com \
  --lang en \
  --title "EN_TITLE" \
  --content "EN_CONTENT_HTML" \
  --excerpt "EN_EXCERPT" \
  --slug "SLUG_EN" \
  --status publish \
  --meta-title "SEO_TITLE_EN" \
  --meta-desc "META_DESC_EN" \
  --focus-kw "FOCUS_KW_EN"
```

返回 JSON，从中提取 `url`（访问链接）和 `edit_url`（后台编辑链接）。

**步骤 5.2 - 发布中文版**：

```bash
python3 ~/.claude/skills/deepclick-blog/scripts/publish.py \
  --site traffictalking.com \
  --lang zh \
  --title "ZH_TITLE" \
  --content "ZH_CONTENT_HTML" \
  --excerpt "ZH_EXCERPT" \
  --slug "SLUG_ZH" \
  --status publish \
  --meta-title "SEO_TITLE_ZH" \
  --meta-desc "META_DESC_ZH" \
  --focus-kw "FOCUS_KW_ZH"
```

**步骤 5.3 - 仅交互模式 draft 确认**：

```bash
# 将 draft 改为 publish（获取 post_id 后用 curl 更新）
curl -s -X POST "https://traffictalking.com/wp-json/wp/v2/posts/{post_id}" \
  -u "username:app_password" \
  -H "Content-Type: application/json" \
  -d '{"status": "publish"}'
```

**错误处理**：脚本返回含 `error` 字段时，记录到 PUBLISH_LOG（status: failed），继续处理下一篇，不中断整体流程。

发布每篇文章后，将以下数据记录下来，用于步骤 6 生成报告：

```
PUBLISH_LOG 条目：
- article_title: {标题}
- primary_keyword: {主关键词}
- signal_source: {来源信号摘要}
- site_name: {站点域名}
- blog_id: {blog_id}
- en_post_url: {英文版访问链接}
- en_edit_url: {英文版后台编辑链接}
- zh_post_url: {中文版访问链接}
- zh_edit_url: {中文版后台编辑链接}
- en_focus_kw: {英文焦点关键词}
- zh_focus_kw: {中文焦点关键词}
- status: success / failed
```

---

### 步骤 6：生成执行报告

所有文章发布完毕后，生成执行报告。

**报告模板**：读取 `templates/report.md`，按实际数据填充所有 `{占位符}`，每篇文章重复"发布详情"区块。

报告完成后：
1. **保存到文件**：`~/logs/deepclick-blog/YYYY-MM-DD-HHmm.md`（定时任务存档）
2. **输出到对话**（供用户查看）

```bash
mkdir -p ~/logs/deepclick-blog
# 将填充好的报告内容写入：~/logs/deepclick-blog/$(date +%Y-%m-%d-%H%M).md
```

如果保存文件失败（权限等问题），只输出到对话，不中断流程。

**频道通知版**（openclaw `--deliver` 到 Telegram/Discord 时额外输出，放在完整报告之前）：

读取 `templates/channel-notify.md`，按实际数据填充占位符后输出。

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
