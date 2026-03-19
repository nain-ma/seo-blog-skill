## ADDED Requirements

### Requirement: 扩展角度模板库
系统 SHALL 在 `references/content-types.md` 中定义 10 种文章角度类型，替代当前 SKILL.md 中的 4 种。

#### Scenario: 完整角度类型
- **WHEN** agent 在步骤 2 选择文章角度
- **THEN** SHALL 从以下 10 种类型中选择：新闻分析、操作指南、数据洞察、问题诊断、对比评测、客户案例、术语科普、工具清单、季节性话题、行业年度报告

#### Scenario: 角度匹配建议
- **WHEN** 候选话题确定后
- **THEN** `content-types.md` SHALL 为每种角度提供适用场景和示例标题格式，供 agent 匹配

### Requirement: 常青选题池
系统 SHALL 在 `references/evergreen-topics.md` 中维护 30-50 个不依赖实时信号的常青话题。

#### Scenario: 常青话题结构
- **WHEN** agent 读取常青选题池
- **THEN** 每个话题 SHALL 包含：话题标题、建议角度类型、种子关键词（1-3个）、唯一标识符（用于去重）

#### Scenario: 分类覆盖
- **WHEN** 审视常青选题池全集
- **THEN** SHALL 覆盖至少 6 种不同角度类型，不集中于单一类型

#### Scenario: 池剩余提醒
- **WHEN** 常青池中未使用的话题少于 10 个
- **THEN** agent SHALL 在执行报告中提示"常青选题池剩余 N 个，建议补充"

### Requirement: SKILL.md 步骤 2 角度选择重写
SKILL.md 的步骤 2 SHALL 引用 `references/content-types.md` 中的角度模板，而非内联定义 4 种固定类型。

#### Scenario: 引用外部模板
- **WHEN** agent 执行步骤 2
- **THEN** SHALL 读取 `references/content-types.md` 获取可用角度列表和匹配规则

### Requirement: 关键词矩阵改为种子词 + 动态扩展
`references/deepclick-positioning.md` 中的关键词矩阵 SHALL 改为"种子关键词"定位，明确标注这些词用于 Autocomplete 扩展的输入，而非文章的唯一关键词选项。

#### Scenario: 种子词标注
- **WHEN** agent 读取关键词矩阵
- **THEN** 矩阵 SHALL 将现有关键词标记为"种子词"，并注明"实际文章关键词通过 keyword_expand.py 动态扩展获得"
