## Why

当前博客选题机制存在三重锁死：信号源仅有一个 radar API（8h digest）、关键词矩阵是 18 个静态硬编码词、角度模板只有 4 种。结果是每篇文章都在"Meta 又改了什么 → 对 CVR 有什么影响"的模式里打转，选题高度同质化，无法覆盖有搜索需求的长尾流量。

## What Changes

- **新增 Google Autocomplete 长尾词扩展**：在信号获取和角度选择之间插入关键词扩展步骤，从种子词通过字母扩展生成 200+ 长尾候选词
- **新增竞品 RSS 监控**：订阅 6 条已验证活跃的行业博客 RSS（Jon Loomer、VWO、SEJ Paid Media、Unbounce、WordStream、CRO Weekly），发现内容 gap
- **新增选题评分机制**：信号 × 搜索需求交叉匹配，优先选择既有时效性又有搜索量的话题
- **扩展角度模板**：从 4 种（新闻分析/操作指南/数据洞察/问题诊断）扩展到 10 种，增加对比文章、案例故事、术语科普、工具清单、季节性话题、行业报告
- **新增常青选题池**：维护一个不依赖实时信号的静态话题库，cron 任务可交替从信号选题和常青选题中取
- **改造选题流程**：从单步"拉信号→选角度"改为多源汇聚→扩展→评分→选择的管线

## Capabilities

### New Capabilities
- `keyword-expansion`: Google Autocomplete 字母扩展脚本，输入种子词输出长尾关键词列表
- `rss-monitoring`: 竞品 RSS 抓取、去重、内容 gap 分析
- `topic-scoring`: 多信号源汇聚后的选题评分与排序机制
- `content-diversity`: 扩展后的角度模板库 + 常青选题池

### Modified Capabilities

（无已有 specs）

## Impact

- **SKILL.md**：主工作流步骤 1-2 之间插入新流程，步骤 2 角度选择逻辑重写
- **references/deepclick-positioning.md**：关键词矩阵从纯静态改为静态种子词 + 动态扩展
- **新增脚本**：`scripts/keyword_expand.py`、`scripts/rss_monitor.py`
- **新增参考文件**：`references/evergreen-topics.md`、`references/content-types.md`
- **依赖**：Python 标准库（urllib、json、xml）+ feedparser（RSS 解析，pip install）
- **外部 API**：Google Autocomplete（免费、无 auth）、竞品 RSS（公开）
- **后续扩展点**：Phase 2 可接入 Keywords Everywhere API（$1.75/月）和 Reddit API 做搜索量验证
