---
name: asp-siem-zh
description: '通过 schema 探索、关键词搜索和自适应字段查询来调查 ASP SIEM 数据。适用于查找正确索引、检查可用字段、按 IOC 搜索日志，或用精确过滤和聚合运行结构化 hunt。'
argument-hint: 'explore schema [index] | search <keyword> from <UTC start> to <UTC end> | adaptive query <index_name> <time range> [filters] [aggregations]'
compatibility: connect to asp mcp server
metadata:
  author: Funnywolf
  version: 0.3.0
  mcp-server: asp
  category: cyber security
  tags: [ SIEM, search, SOC, hunting, investigation ]
  documentation: https://asp.viperrtp.com/
---

# ASP SIEM

当用户要在 ASP 中进行 SIEM 调查时，使用这个 skill。这个 skill 应该指导搜索策略和证据收集。

## 适用场景

- 用户想在搜索前先发现有哪些索引或字段。
- 用户想按 IP、用户、主机、hash、域名、进程、邮箱或任意关键词搜索日志。
- 用户想从 alert、artifact 或 case pivot 到 SIEM 证据。
- 用户想要精确匹配过滤和 top-N 统计，而不是自由文本搜索。
- 用户想收窄噪音搜索或扩展空结果。
- 用户想要完整原始证据，而不只是高层计数。

## 运行规则

- 如果用户请求已经隐含 SIEM 搜索，不要反问用户要选哪种操作。
- 只收集所选路径缺失的必要输入。
- 把它视为调查工作流，而不是一次性查询助手。
- 当用户不知道正确索引或字段时，使用 `siem_explore_schema`。
- 当用户有一个或多个强关键词且需要匹配事件时，使用 `siem_keyword_search`。
- 当用户已经知道目标索引且想要精确字段过滤或统计时，使用 `siem_adaptive_query`。
- 如果用户给出相对时间窗口，先调用 `get_current_time`，从返回的本地时间加时区推导出可用的 UTC 范围。
- 优化目标是有用证据，而不是最大原始输出。

## 决策流程

1. 如果用户问该用哪个索引、有哪些字段，或 SIEM 源如何组织，使用 `siem_explore_schema`。
2. 如果用户已经提供关键词和时间范围，立即使用 `siem_keyword_search`。
3. 如果用户给出相对时间窗口，调用 `get_current_time`，从返回的本地时间加时区推导出可用 UTC 范围，再继续。
4. 如果用户只给了 IOC 或关键词，询问最窄可用的 UTC 时间范围。
5. 如果用户想要精确字段过滤、分组统计或受控聚合，使用 `siem_adaptive_query`。
6. 如果用户知道数据源，传 `index_name`；否则先广泛搜索或先探索 schema。
7. 如果数据源可能使用非默认时间字段，询问它；否则使用 `@timestamp`。
8. 每次搜索后，决定是停止、收窄、扩展，还是把有用结果写回为 enrichment。

## SOP

### 探索 Schema

1. 如果用户不知道目标源，先调用 `siem_explore_schema()`。
2. 如果用户已经知道索引且想要字段结构，调用 `siem_explore_schema(target_index=<index>)`。
3. 解析返回的 JSON。
4. 总结与调查目标最相关的索引、时间字段候选和高信号字段。
5. 推荐下一步查询路径：关键词搜索或自适应查询。

### 开始搜索

1. 先提取已知最强关键词。
2. 只有当用户真正要求所有条件都匹配时，才把多个关键词规范化为 AND 集合。
3. 要求 UTC 时间戳以 `Z` 结尾。
4. 调用 `siem_keyword_search`。
5. 解析每条返回的 JSON 字符串。

### 运行结构化 Hunt

1. 要求 `index_name`、UTC 时间范围，以及至少一个精确过滤条件或明确聚合目标。
2. 把过滤条件规范化为精确字段/值对。
3. 只有当用户想要流行度、top-N 统计或分组范围时，才添加 `aggregation_fields`。
4. 调用 `siem_adaptive_query`。
5. 用分析师语言总结过滤范围和任何聚合输出。

### 优化搜索

首选优化动作：

1. 在添加很多新关键词前，先收窄时间范围。
2. 添加一两个高信号关键词，而不是很多弱关键词。
3. 如果查询为空，移除一个限制性关键词。
4. 当广泛搜索返回太多无关数据时，添加 `index_name`。
5. 当用户已经学到足够字段结构可以停止使用关键词搜索时，切换到 `siem_adaptive_query`。
6. 持续迭代直到结果质量匹配用户目标。

### 调查模式

在有帮助时使用这些模式：

- `IOC pivot`：从一个 IOC 开始，然后从返回记录中添加主机、用户、进程或动作。
- `Alert follow-up`：用告警 artifact 加告警时间窗口搜索，然后围绕首次和最后出现时间收紧。
- `User activity check`：从用户名加窄时间范围开始，然后 pivot 到源 IP、主机和动作。
- `Infrastructure pivot`：从 IP 或主机名开始，然后 pivot 到相关用户、进程和目标。

### 停止条件

满足以下任一条件时停止优化：

- 用户只要求范围、趋势或流行度。
- 进一步优化可能会移除相关证据。
- 重复优化仍然没有返回有用数据。
- 用户已经有正确索引和精确字段约束，这种情况下下一步是自适应查询而不是另一次关键词搜索。

## 回复策略

始终解释搜索的含义，而不只是它返回了什么。

首选回复结构：

### 搜索概览

- 搜索模式：schema 探索、关键词搜索或自适应查询
- 关键词集或精确过滤条件
- 时间范围
- 搜索的索引或 `all`
- 如果使用了聚合字段
- 结果组数量
- 用一两句话给出整体解释

### 结果组

| Backend | Status | Total Hits | Index Distribution | Meaning |
|---------|--------|------------|--------------------|---------|

### 证据要点

- 对调查重要的关键字段统计。
- 只有在增加价值时才给出代表性记录。
- 重要 pivot：用户、主机、IP、进程、事件、动作、目标或其他相关字段。
- 对于 schema 探索，只强调对 hunt 重要的索引和字段。

### 下一步最佳动作

- 收窄时间范围
- 添加一个更强关键词
- 移除一个限制性关键词
- 搜索特定索引
- 用精确过滤切换到自适应查询
- 把有用 SIEM 结果保存为相关 case、alert 或 artifact 上的 enrichment
- 停止，因为证据已经足够

## 澄清规则

- 如果缺少时间范围，询问时间范围。
- 只有当用户没有提供 UTC 且意图时区不清楚时，才询问时区。
- 只有当广泛搜索可能浪费、用户已经暗示已知源，或自适应查询是正确工具时，才询问 `index_name`。
- 只有当用户想要自适应查询且 schema 仍不清楚时，才询问精确字段名。
- 如果用户说"看看这个事件周围"，从可用 IOC 和时间框架推导出合理的首次搜索，而不是让他们设计查询。

## 输出规则

- 保持简洁。
- 默认不要倾倒每条返回记录。
- 优先展示最相关的记录和统计。
- 当返回多个组时，按 backend 和 index 分组结果。
- 对于 schema 探索，呈现候选列表而不是原始字段清单。
- 如果没有找到数据，直接说明并建议最可能有用的调整。

## 失败处理

- 无效时间格式：要求 UTC ISO8601 带尾部 `Z`。
- 空结果：扩展时间范围或移除一个关键词。
- 太多命中：先收窄时间范围，再添加信号。
- 未知索引或字段选择：在猜测前使用 `siem_explore_schema`。
- Backend 或源问题：如果结果指示了，说明哪个 backend 或索引失败。
