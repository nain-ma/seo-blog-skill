## ADDED Requirements

### Requirement: 竞品 RSS 抓取
系统 SHALL 提供 `scripts/rss_monitor.py` 脚本，从预配置的 RSS 源列表抓取最新文章，返回结构化的文章列表。

#### Scenario: 抓取所有配置源
- **WHEN** 执行 `python3 scripts/rss_monitor.py`
- **THEN** 脚本从内置的 6 个 RSS 源抓取最近 7 天的文章，输出 JSON 格式的文章列表

#### Scenario: 指定时间范围
- **WHEN** 执行 `python3 scripts/rss_monitor.py --days 14`
- **THEN** 脚本抓取最近 14 天的文章

#### Scenario: 单源失败不中断
- **WHEN** 某个 RSS 源请求失败（超时、404、解析错误）
- **THEN** 脚本 SHALL 记录错误并继续处理其余源，输出中包含 `failed_sources` 字段

### Requirement: 文章去重
脚本 SHALL 通过本地状态文件对已读文章去重，避免重复推荐。

#### Scenario: 首次运行
- **WHEN** `~/.config/deepclick-blog/rss-seen.json` 不存在
- **THEN** 脚本 SHALL 自动创建该文件，所有抓取的文章均标记为新文章

#### Scenario: 过滤已读文章
- **WHEN** 某篇文章的 URL 已存在于 `rss-seen.json` 中
- **THEN** 该文章 SHALL 不出现在输出的 `new_articles` 列表中

#### Scenario: 标记已读
- **WHEN** 执行 `python3 scripts/rss_monitor.py --mark-seen`
- **THEN** 本次抓取的所有新文章 URL SHALL 写入 `rss-seen.json`

### Requirement: 输出格式
脚本输出 SHALL 为 JSON，包含文章标题、URL、发布日期、来源名称。

#### Scenario: 正常输出
- **WHEN** 抓取成功
- **THEN** 输出格式为 `{"new_articles": [{"title": "...", "url": "...", "published": "...", "source": "..."}], "total_new": N, "failed_sources": []}`

### Requirement: 内置 RSS 源列表
脚本 SHALL 内置以下 6 个已验证活跃的 RSS 源，无需外部配置。

#### Scenario: 默认源列表
- **WHEN** 脚本运行且未指定自定义源
- **THEN** SHALL 抓取以下源：`jonloomer.com/feed/`、`vwo.com/blog/feed/`、`searchenginejournal.com/category/paid-media/feed/`、`unbounce.com/feed/`、`wordstream.com/feed`、`tomvandenberg.substack.com/feed`
