## ADDED Requirements

### Requirement: 多源候选汇聚
SKILL.md 的步骤 1.5 SHALL 汇聚以下来源的候选话题进入统一评分：
1. radar API 信号（现有步骤 1）
2. 竞品 RSS 最新文章标题（内容 gap 信号）
3. 常青选题池中未使用的话题

#### Scenario: 三源汇聚
- **WHEN** agent 执行步骤 1.5
- **THEN** agent SHALL 将 radar 信号、RSS 新文章、常青池话题合并为统一的候选列表，每条标注来源类型

#### Scenario: 某源无数据
- **WHEN** radar API 返回空或 RSS 全部失败
- **THEN** agent SHALL 继续用剩余来源的候选话题，不中断流程

### Requirement: 长尾词扩展验证
agent SHALL 对每个候选话题提取 1-2 个种子关键词，调用 keyword_expand.py 做 Autocomplete 扩展，用命中数作为搜索需求评估。

#### Scenario: 扩展验证
- **WHEN** 候选话题为 "Meta Advantage+ 落地页变化"
- **THEN** agent SHALL 提取种子词如 "meta advantage+ landing page"，执行扩展，记录返回的长尾词数量

### Requirement: 加权评分排序
agent SHALL 对每个候选话题按以下维度打分，取总分最高者：

| 维度 | 分值 | 规则 |
|------|------|------|
| 搜索需求 | 0-5 | Autocomplete 长尾变体数：0个=0分，1-5个=2分，6-15个=3分，16+=5分 |
| 时效性 | 0-3 | radar 信号=3，RSS 7天内=2，常青池=1 |
| 内容 gap | 0-2 | 竞品最近写了且我们无对应文章=+2 |
| 多样性惩罚 | -2~0 | 最近 7 天已发布相同角度类型=-2 |

#### Scenario: 评分计算
- **WHEN** 候选话题"Meta Ads Benchmark 2026"的 Autocomplete 返回 12 条长尾、来源为 radar 信号、竞品 VWO 刚发了类似话题、最近 7 天未发过"数据洞察"类
- **THEN** 得分 SHALL 为 3（搜索）+ 3（时效）+ 2（gap）+ 0（无惩罚）= 8 分

#### Scenario: 交互模式展示 Top 3
- **WHEN** 处于交互模式（非 --batch）
- **THEN** agent SHALL 展示得分最高的 3 个候选话题及评分明细，等用户选择

#### Scenario: 批量模式自动选择
- **WHEN** 处于 --batch 模式
- **THEN** agent SHALL 自动选择得分最高的候选话题

### Requirement: 已用话题去重
步骤 1.5 SHALL 复用现有的 `~/logs/deepclick-blog/.used-signals.json` 去重机制，过滤掉已用过的信号和常青话题。

#### Scenario: 过滤已用信号
- **WHEN** 某个 radar 信号 URL 已在 `.used-signals.json` 中
- **THEN** 该信号 SHALL 不进入候选列表

#### Scenario: 常青话题去重
- **WHEN** 常青池中某话题的标识符已在 `.used-signals.json` 中
- **THEN** 该话题 SHALL 不进入候选列表
