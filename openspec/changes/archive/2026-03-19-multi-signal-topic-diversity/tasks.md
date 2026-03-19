## 1. 脚本开发

- [x] 1.1 创建 `scripts/keyword_expand.py`：实现 Google Autocomplete 字母扩展，支持 `--seeds`、`--lang`、`--country` 参数，输出 JSON 格式
- [x] 1.2 创建 `scripts/rss_monitor.py`：实现 6 源 RSS 抓取、feedparser 解析、`rss-seen.json` 去重、`--days` 和 `--mark-seen` 参数，输出 JSON 格式
- [x] 1.3 验证两个脚本可独立运行并输出正确 JSON

## 2. 参考文件

- [x] 2.1 创建 `references/content-types.md`：定义 10 种角度模板（新闻分析、操作指南、数据洞察、问题诊断、对比评测、客户案例、术语科普、工具清单、季节性话题、行业年度报告），每种含适用场景 + 示例标题
- [x] 2.2 创建 `references/evergreen-topics.md`：填充 30-50 个常青话题，每条含标题、建议角度、种子关键词、唯一 ID，覆盖至少 6 种角度类型
- [x] 2.3 修改 `references/deepclick-positioning.md`：将关键词矩阵标记为"种子关键词"，注明用于 Autocomplete 扩展输入

## 3. 主流程改造（SKILL.md）

- [x] 3.1 在步骤 1 和步骤 2 之间插入"步骤 1.5：选题扩展与评分"，包含：多源汇聚、长尾词扩展、加权评分、交互/批量模式分支
- [x] 3.2 重写步骤 2 角度选择逻辑，改为引用 `references/content-types.md` 的 10 种模板
- [x] 3.3 在初始化检测中加入 feedparser 安装检查（`pip install feedparser`）
- [x] 3.4 在步骤 6 报告模板中加入常青池剩余数量提示

## 4. 验证

- [x] 4.1 手动模式端到端测试：指定话题 → 验证 Autocomplete 扩展 → 角度选择 → 生成文章
- [x] 4.2 自动模式端到端测试：不指定话题 → 验证 radar + RSS + 常青池汇聚 → 评分排序 → 生成文章
