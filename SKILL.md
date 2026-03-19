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

## 安装后初始化（第一步，只需一次）

**发布方式**：直接调用 WordPress REST API（Basic Auth + Application Password），无需 wpcom-mcp 或任何 OAuth 服务。

### 检测是否需要初始化

每次 skill 被调用时，先检查配置文件和依赖是否存在且有效：

```bash
python3 -c "
import json; from pathlib import Path
p = Path('~/.config/deepclick-blog/sites.json').expanduser()
sites = 'ok' if p.exists() and json.loads(p.read_text()) else 'missing'
try:
    import feedparser; fp = 'ok'
except ImportError:
    fp = 'missing'
print(f'sites:{sites} feedparser:{fp}')
"
```

输出含 `sites:missing` 时，进入初始化流程（**不要让用户手动运行脚本**）。
输出含 `feedparser:missing` 时，先安装依赖：`python3 -m pip install feedparser -q`。

### 对话式初始化流程

通过对话收集信息，Agent 自己调用脚本完成配置：

**第一步**：询问用户 WordPress 账号邮箱（所有站共用）：
> "请提供你的 WordPress 账号邮箱地址"

**第二步**：询问要配置的站点及对应 Application Password：
> "请提供各站点的 Application Password。生成方式：进入站点后台 → Users → Profile → 最底部 Application Passwords → 输入名称 → 生成 → 复制。
> 请逐个提供：站点域名 + Application Password"

**第三步**：Agent 自动验证连接并拉取分类列表：

```bash
python3 -c "
import base64, json, urllib.request
email = '{EMAIL}'; url = '{URL}'; pwd = '{APP_PASSWORD}'
token = base64.b64encode(f'{email}:{pwd}'.encode()).decode()
headers = {'Authorization': f'Basic {token}'}

# 验证用户
req = urllib.request.Request(f'{url}/wp-json/wp/v2/users/me', headers=headers)
me = json.loads(urllib.request.urlopen(req, timeout=10).read())
print('USER:' + me.get('name',''))

# 拉分类
req2 = urllib.request.Request(f'{url}/wp-json/wp/v2/categories?per_page=100', headers=headers)
cats = json.loads(urllib.request.urlopen(req2, timeout=10).read())
for c in cats:
    print(f'CAT:{c[\"id\"]}:{c[\"name\"]}')
"
```

**第四步**：将分类列表展示给用户，对话式确认：

> "站点 {domain} 共有以下分类，请告诉我哪个用于**英文文章**，哪个用于**中文文章**（输入 ID 即可）：
> [ID] 分类名
> [ID] 分类名
> ..."

Agent 尝试按名称**自动匹配**（优先选含 en/english/中文/zh/chinese 的分类名），有把握时直接确认，否则列出候选请用户选择。

**第五步**：写入配置文件：

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

验证成功、分类已设置后，告知用户配置完成并直接继续发布流程。
失败的站点提示重新生成 Application Password。

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

### 步骤 1.5：选题扩展与评分

在获取信号后、确定角度前，汇聚多信号源并通过长尾词扩展和评分选出最佳话题。

**手动模式跳过此步骤**：用户直接指定话题时，直接进入步骤 2。

#### 1.5.1 多源候选汇聚

将以下来源的候选话题合并为统一列表，每条标注来源类型：

1. **radar API 信号**（步骤 1 的输出）— 标记为 `signal`
2. **竞品 RSS 新文章**：

```bash
python3 ~/.claude/skills/deepclick-blog/scripts/rss_monitor.py --days 7
```

从输出的 `new_articles` 中提取标题作为候选，标记为 `rss`。关注竞品写了但我们没有对应内容的话题（内容 gap）。

3. **常青选题池**：读取 `references/evergreen-topics.md`，过滤掉 `.used-signals.json` 中已使用的话题 ID（格式 `evergreen:{ID}`），标记为 `evergreen`。

某源无数据时继续用剩余来源，不中断。

#### 1.5.2 长尾词扩展验证

对每个候选话题提取 1-2 个种子关键词，调用 Autocomplete 扩展：

```bash
python3 ~/.claude/skills/deepclick-blog/scripts/keyword_expand.py --seeds "种子词1,种子词2"
```

记录每个候选话题的长尾词命中数（`total` 字段），用于评分。

> 为控制请求量，每次选题最多扩展 5 个候选话题的种子词。优先扩展来自 `signal` 和 `rss` 的话题。

#### 1.5.3 加权评分排序

| 维度       | 分值  | 规则                                                          |
| ---------- | ----- | ------------------------------------------------------------- |
| 搜索需求   | 0-5   | Autocomplete 长尾变体数：0 个=0，1-5 个=2，6-15 个=3，16+=5  |
| 时效性     | 0-3   | radar 信号=3，RSS 7 天内=2，常青池=1                          |
| 内容 gap   | 0-2   | 竞品最近写了且我们无对应文章=+2                               |
| 多样性惩罚 | -2\~0 | 最近 7 天已发布相同角度类型=-2（查 `~/logs/deepclick-blog/`）  |

**交互模式**：展示得分最高的 3 个候选话题及评分明细，等用户选择。
**批量模式**（`--batch`）：自动选择得分最高的候选话题。

#### 1.5.4 记录已用话题

发布完成后，将选中话题的信号 URL 或常青话题 ID（`evergreen:{ID}`）追加到 `.used-signals.json`。

---

### 步骤 2：确定博客角度

基于步骤 1.5 选出的话题，参考 `references/content-types.md` 中的 **10 种角度模板**选择最匹配的文章角度。

角度选择依据：
- 话题来源类型（signal 偏向新闻分析，evergreen 偏向科普/指南）
- Autocomplete 扩展中出现的用户搜索意图（"how to" → 操作指南，"vs" → 对比评测，"what is" → 术语科普）
- 最近 7 天已发布的角度类型（避免重复）

每篇文章聚焦**一个核心角度**，不要把所有信号都塞进一篇文章。

---

### 步骤 2.5：行业参考 Blog 拆解（用户提供参考文章时必做）

当用户提供某行业参考 SEO Blog（如金融行业）并要求“提取关键要点/按该风格迭代模板”时：

1. 先读取并拆解原文结构、论点、证据、CTA 与合规表达。
2. 使用 `templates/industry-insight-extract.md` 填充提取结果。
3. 输出两层结论：
   - **可迁移框架**：可跨行业复用的写作结构与论证方式。
   - **行业特异约束**：仅该行业适用的术语、风险披露、指标口径。
4. 将提取结果映射到 DeepClick 叙事，重点回到 CVR/CPA/ROI 与 post-click 优化，不照搬行业术语。
5. 若原文缺少可验证证据，必须在最终写作计划中标记为“待补数据来源”，禁止强行下结论。

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

> ⚠️ WordPress 页面中，`post title` 已作为 H1。**正文禁止再写 H1**，避免双标题。

```
[Title/H1 由 WordPress 标题承担（≤60字/符）]

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

---

## 质量检查清单（发布前自查）

- [ ] 文章核心论点是否能回答"这对我的 CVR/CPA 有什么影响"
- [ ] WordPress 标题（页面 H1）是否包含主关键词，且≤60字符
- [ ] 正文首段前是否无额外 H1（防双标题）
- [ ] Meta description 是否在 150-160 字符范围内
- [ ] 是否有 3 个 CTA（顶/中/底）
- [ ] 底部 CTA 是否有明确的 Demo 链接
- [ ] 中文版是否自然流畅（非机器翻译语感）
- [ ] Slug 是否 URL 友好（全小写，连字符分隔）

---

## 2026-03 质量升级（强制执行）

> 目标：所有改造围绕 **DeepClick Radar → Blog Skill → 每日 SEO Cron** 闭环。

### 1) Radar 先出 Brief，不再直接发文

新增脚本：`scripts/radar_serp_brief.py`

```bash
python3 scripts/radar_serp_brief.py --from-api --limit 3 --out /tmp/serp-brief.json
```

规则：
- 先按 DeepClick 相关性打分（Meta/CVR/CPA/ROI/post-click 优先）
- 仅选择高分信号进入写作
- 每篇文章必须有 `SERP Brief`（主关键词、意图、SERP共性、内容缺口、证据清单）

### 2) 发布前质量拦截（采用 claude-blog 评分体系）

质量评估统一使用 `claude-blog` 的 `analyze_blog.py`（5 类 100 分体系），不再使用自定义评分脚本。

默认门槛：
- `<80` 分：强制 `draft`
- 存在 `high` 严重问题：强制 `draft`

`publish.py` 会在发布前自动调用：

```bash
python3 ~/.claude/skills/blog/scripts/analyze_blog.py /tmp/claude-quality-*.md
```

并把结果写入发布日志（score/rating/issues）。

### 3) 每日 SEO Cron = 发文 + D+14 复盘

新增脚本：`scripts/seo_daily_review.py`

```bash
python3 scripts/seo_daily_review.py \
  --publish-log ~/.openclaw/logs/deepclick-blog/publish_log.jsonl \
  --out ~/.openclaw/logs/deepclick-blog/daily-review.md
```

复盘最低字段：
- 收录状态
- 平均排名
- CTR
- 页面停留
- Demo 点击率

并输出修订建议（改标题/改H2/补证据/调CTA），形成持续优化闭环。

### 4) 第二批：发布日志标准化 + 一键 cron 流水线 + 质量看板

#### 4.1 发布日志标准化（publish.py 内置）

`publish.py` 新增参数：
- `--article-title`
- `--primary-keyword`
- `--signal-source`
- `--topic-cluster`
- `--log-path`

每次执行（成功/失败/拦截）都会写入：
`~/.openclaw/logs/deepclick-blog/publish_log.jsonl`

#### 4.2 每日一键流水线

新增脚本：`scripts/seo_cron_pipeline.py`

```bash
python3 scripts/seo_cron_pipeline.py --limit 5
```

产物：
- `serp-brief-YYYY-MM-DD.json`
- `daily-review.md`
- `quality-dashboard.md`

#### 4.3 质量看板

新增脚本：`scripts/seo_quality_dashboard.py`

```bash
python3 scripts/seo_quality_dashboard.py --days 7
```

展示：发布成功率、拦截率、平均质量分、高频拦截原因、低分修订队列。

---

## 生产SOP（固定执行，cron 同步）

> 目标：稳定产出可发布 SEO Blog，杜绝占位符、重复段落、双标题、无 CTA 文。

### S1. 数据源检索（Radar）
- 仅用 DeepClick Radar 信号池。
- 过滤优先级：Meta/归因/CVR/CPA/ROI/post-click。
- 与 DeepClick 价值无关的信号直接丢弃。

### S2. 选题与关键词（必出 Brief）
- 必须先产出 `SERP Brief`（主关键词、意图、SERP 缺口、证据清单、商业角度）。
- 无 Brief 不进入写作。

### S3. 初稿生成（EN+ZH）
- 先生成首稿，再进入结构清洗。
- 文章必须包含 DeepClick CTA（顶部引导 + 中段提示 + 底部主 CTA）。
- 禁止机械附加“内部资源/来源”区块，除非老板明确要求。

### S4. AI 精修与结构清洗
- 发布前强制清洗：
  - 去正文首个 H1（WordPress 标题即页面 H1）
  - 列表/表格/blockquote HTML 合法化
  - 去重检测（重复段落比例超阈值直接拦截）
  - 去占位符/TODO

### S5. 质量门禁（本地 Gate）
- 使用：`publish.py` 内置 `local-seo-gate`。
- 语言门槛：EN `>=80`，ZH `>=72`。
- 硬拦截仅保留：
  - 缺少 DeepClick CTA
  - 内容重复率过高
- 软检查：结构层级与基础可读长度（提示优化，不做硬拦截）。
- 自动修复：门禁失败后自动优化 1 次再复检。

### S6. 发布策略（默认三站同发）
- 默认站点：`traffictalking.com`、`googlepwa.blog`、`androidpwa.com`
- 默认语言：EN + ZH
- 分类必填，标题唯一性必过。

### S7. 报告与复盘
- 每次发布写入 `publish_log.jsonl`。
- 每日输出：`quality-dashboard.md` + `daily-review.md`。
- D+14 复盘指标：收录、排名、CTR、停留、CTA 点击率。

### S8. 失败处理
- 任一步失败：停止 publish，输出可执行修复动作。
- 发现质量事故（重复段落、双标题等）：先下线为 draft，再修复流程。

---

## 参考文件

- `references/seo-structure.md` — SEO 博客结构详细模板和关键词策略
- `references/wordpress-publish.md` — WordPress REST API 完整技术文档（Polylang Pro + Yoast）
- `references/deepclick-positioning.md` — DeepClick 产品定位、种子关键词矩阵
- `references/content-types.md` — 10 种文章角度模板库
- `references/evergreen-topics.md` — 常青选题池（30-50 个话题）
- `templates/industry-finance-template.md` — 金融行业参考文章提炼模板（可迁移框架 + 行业特异约束）
- `scripts/keyword_expand.py` — Google Autocomplete 长尾词扩展脚本
- `scripts/rss_monitor.py` — 竞品 RSS 监控脚本
