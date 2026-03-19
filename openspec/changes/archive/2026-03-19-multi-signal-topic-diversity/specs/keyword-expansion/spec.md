## ADDED Requirements

### Requirement: Autocomplete 字母扩展
系统 SHALL 提供 `scripts/keyword_expand.py` 脚本，接受一个或多个种子关键词，通过 Google Autocomplete API 的字母扩展法（seed + a-z 共 27 次请求/种子词）返回去重后的长尾关键词列表。

#### Scenario: 单种子词扩展
- **WHEN** 执行 `python3 scripts/keyword_expand.py --seeds "meta ads post-click optimization"`
- **THEN** 脚本向 `suggestqueries.google.com/complete/search` 发送 27 次请求（空字符 + a-z），输出 JSON 格式的去重关键词列表，每条含 `keyword` 字段

#### Scenario: 多种子词扩展
- **WHEN** 执行 `python3 scripts/keyword_expand.py --seeds "meta ads CVR,facebook ads landing page"`
- **THEN** 脚本对每个种子词分别扩展，输出合并去重后的关键词列表

#### Scenario: 请求间隔控制
- **WHEN** 脚本执行 Autocomplete 请求
- **THEN** 每次请求之间 SHALL 等待至少 0.3 秒，避免触发限流

#### Scenario: API 请求失败
- **WHEN** 某次 Autocomplete 请求返回非 200 状态或超时
- **THEN** 脚本 SHALL 跳过该请求并继续处理剩余字母，最终输出中包含 `errors` 字段记录失败数

### Requirement: 输出格式标准化
脚本输出 SHALL 为 JSON 格式，可被 agent 直接解析用于后续选题评分。

#### Scenario: 正常输出格式
- **WHEN** 扩展成功完成
- **THEN** 输出格式为 `{"keywords": ["kw1", "kw2", ...], "seed_count": N, "total": M, "errors": 0}`

### Requirement: 语言和地区参数
脚本 SHALL 支持 `--lang` 和 `--country` 参数控制 Autocomplete 结果的语言和地区。

#### Scenario: 英文美国市场
- **WHEN** 执行 `python3 scripts/keyword_expand.py --seeds "meta ads" --lang en --country US`
- **THEN** 请求参数中 `hl=en`、`gl=US`

#### Scenario: 默认参数
- **WHEN** 未指定 `--lang` 和 `--country`
- **THEN** 默认使用 `hl=en`、`gl=US`
