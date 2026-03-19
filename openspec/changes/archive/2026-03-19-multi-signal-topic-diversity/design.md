## Context

当前 deepclick-blog skill 的选题管线是线性单源的：radar API → 固定过滤规则 → 4 种角度模板。关键词矩阵硬编码在 `references/deepclick-positioning.md` 中，共约 18 个词。这导致每篇博客都围绕同一批关键词和同一种"新闻分析"模式，无法覆盖长尾搜索流量。

skill 运行环境是 Claude Code agent，通过 Python 脚本执行外部操作。当前已有 `scripts/publish.py` 和 `scripts/setup.py`。

## Goals / Non-Goals

**Goals:**
- 选题来源从单一 radar API 扩展为多信号源汇聚
- 每次选题时动态发现有搜索需求的长尾关键词
- 支持更多内容类型，降低文章同质化
- 保持零成本（Phase 1 不引入付费 API）
- 对现有发布流程（步骤 3-6）零侵入

**Non-Goals:**
- 不改动 WordPress 发布逻辑（publish.py 不动）
- 不实现 Phase 2/3 的付费 API 集成（Keywords Everywhere、Reddit、GSC）
- 不做自动化 A/B 标题测试
- 不改动 CTA 模板和文章结构模板

## Decisions

### 1. 长尾词扩展用 Google Autocomplete 而非 pytrends

**选择**：Google Autocomplete（`suggestqueries.google.com/complete/search`）

**理由**：
- 零 auth、极稳定（多年未变）、无明确限流
- 字母扩展法（seed + a-z）单次可获 200+ 候选词
- pytrends 主库已 archived（2025.4），替代 fork 成熟度不够
- Autocomplete 直接反映用户真实搜索行为

**替代方案**：pytrends `related_queries(rising=True)` — 保留为 Phase 2 的补充信号，不作为 Phase 1 核心依赖。

### 2. RSS 监控用 feedparser + 本地 JSON 去重

**选择**：`feedparser` 库解析 RSS，已读条目存储在 `~/.config/deepclick-blog/rss-seen.json`

**理由**：
- feedparser 是 Python RSS 解析的事实标准，处理各种格式兼容性好
- 本地 JSON 文件去重，与现有 `.used-signals.json` 模式一致
- 不需要数据库或外部服务

**RSS 源选择**（已验证活跃）：
| 源 | URL | 频率 |
|----|-----|------|
| Jon Loomer | `jonloomer.com/feed/` | 3-4/周 |
| VWO | `vwo.com/blog/feed/` | 2-3/周 |
| SEJ Paid Media | `searchenginejournal.com/category/paid-media/feed/` | 3-5/周 |
| Unbounce | `unbounce.com/feed/` | 2-4/月 |
| WordStream | `wordstream.com/feed` | 2-3/周 |
| CRO Weekly | `tomvandenberg.substack.com/feed` | 1/周 |

### 3. 选题评分采用简单加权打分而非 ML 排序

**选择**：基于规则的加权评分（autocomplete 命中数 × 信号新鲜度 × 角度多样性惩罚）

**理由**：
- 候选池小（通常 10-20 个），不需要 ML
- 规则透明，agent 可在对话中解释选择理由
- 评分逻辑写在 SKILL.md 的 prompt 中，不需要额外脚本

**评分维度**：
- **搜索需求分**（0-5）：种子词在 Autocomplete 中命中的长尾变体数量
- **时效性分**（0-3）：来自 radar 信号 +3，来自 RSS +2，来自常青池 +1
- **多样性惩罚**（-2）：最近 7 天已发布过相同角度类型的话题扣分
- **内容 gap 加分**（+2）：竞品最近写了但我们没有对应文章

### 4. 常青选题池作为静态参考文件维护

**选择**：`references/evergreen-topics.md` 中维护约 30-50 个常青话题

**理由**：
- Agent 读文件比调 API 快，且零外部依赖
- 话题由人工 curate + agent 建议更新，质量可控
- cron 任务随机从池中取未使用的话题，通过 `.used-signals.json` 同样的去重机制避免重复

### 5. 新步骤插入位置：步骤 1 之后、步骤 2 之前

**选择**：新增"步骤 1.5：选题扩展与评分"

**理由**：
- 步骤 1（获取信号）不变，仍然是信号源之一
- 步骤 2（确定角度）改为从评分后的候选列表中选择，而非直接从信号中选
- 步骤 3-6（SEO 计划、写作、发布、报告）完全不动

```
原流程:  [1.信号] → [2.角度] → [3.SEO] → [4.写] → [5.发] → [6.报告]
新流程:  [1.信号] → [1.5.扩展+评分] → [2.角度] → [3.SEO] → [4.写] → [5.发] → [6.报告]
                       ↑
            Autocomplete + RSS + 常青池 + 评分
```

## Risks / Trade-offs

**Google Autocomplete 被限流** → 缓解：加 0.5s 间隔；每次只扩展 2-3 个种子词（约 80 请求）；失败时 fallback 到纯信号模式

**feedparser 依赖需要 pip install** → 缓解：在 SKILL.md 初始化检查中加入 feedparser 安装检测，首次运行自动 `pip install feedparser`

**RSS 源失效（站点下线/改 URL）** → 缓解：rss_monitor.py 对每个源做 try/except，单源失败不影响整体；定期检查时在报告中标注失败源

**选题评分过于机械** → 缓解：评分只做排序建议，交互模式下 agent 仍会展示 top 3 给用户选择；批量模式取 top 1

**常青选题池耗尽** → 缓解：池中保持 30-50 个话题；agent 在报告中提示"常青池剩余 N 个话题"；低于 10 个时建议用户补充
