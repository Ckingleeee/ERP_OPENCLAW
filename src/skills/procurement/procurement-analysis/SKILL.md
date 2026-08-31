---
name: benefit-operations-analysis
description: >
  信用卡权益与营销资源运营分析技能。串联需求拆解、数据收集、分析、图表和报告。
  当需要服务商对比、权益成本、资源配额或营销策略评估时加载。
---

# 信用卡权益与营销资源运营分析技能

## 适用场景
- 权益服务商成本与履约对比
- 权益资源成本、发放与核销趋势分析
- 服务商综合评分（成本、履约、稳定性、服务）
- 配额风险与营销资源补充建议
- 生成权益运营分析报告

## 分析流程（5 步）

### 第 1 步：理解需求
- 从任务描述中提取：【任务目标】、【用户偏好】、【分析需求正文】
- 明确分析维度：服务商对比？成本趋势？资源筛选？配额风险？

### 第 2 步：收集数据

**2a. ERP 内部数据（必须）**
- `provider_query(name="服务商名")` → 权益服务商列表
- `resource_query(name="权益名")` 或 `resource_search(name="权益名")` → 营销资源
- `resource_by_provider(provider_id=N)` → 按服务商查资源
- `replenishment_search_details(resourceName="xxx")` → 历史补充成本
- `quota_warning()` → 资源配额预警

**2b. 外部数据（不可跳过）**
1. 激活 `/skills/procurement/supplier-price-urls/`，读取 `data/url_mapping.yaml`
2. 按权益资源名 + 服务商名查找公开信息 URL
3. **找到 URL** → 使用 `web-scraper` 直接抓取：
   ```bash
   execute("python /skills/procurement/web-scraper/scrape_page.py --url '<报价URL>'")
   ```
   脚本将 HTML 转为 Markdown 保存到 `/analysis/temp/{filename}.md`，再 `read_file` 读取内容提取价格/型号/品牌/材质/单位。
4. **未找到 URL** → 使用 `web_search` 搜索公开市场价格、权益规则和服务商信息
5. 无论哪种路径，最终都要有外部参考数据用于对比

### 第 3 步：执行分析
1. 编写 Python 分析脚本，使用 `execute` 工具运行
2. 如需安装依赖：`pip install -i https://mirrors.aliyun.com/pypi/simple/ pandas matplotlib numpy`（已自动路由到 `/opt/skills-venv/bin/pip`）
3. 常见分析维度：
   - 成本对比：最低成本、均值、价差百分比
   - 服务商评估：服务评级 + 成本 + 履约稳定性加权
   - 权益质量：有效期、覆盖范围和使用门槛对比
   - 综合排名：多维度加权评分
4. 分析结果保留在上下文（`execute` 工具输出），无需写入文件

### 第 4 步：生成图表
1. **首次调用图表前**：`read_file("/skills/procurement/chart_params.md")` 获取 26 种图表参数速查（紧凑格式，仅 data 格式 + 特有参数，通用参数已提取到顶部表格，不逐图重复）
2. 根据分析维度选择 2-4 个最有洞察力的 chart_type
4. 循环调用 `generate_visualization(chart_type="xxx", chart_config={...})`，通用参数（width/height/title/theme/style）直接使用，无需每图查阅
5. 参考文件只读一次，后续多次调用不额外消耗上下文
6. 参数报错时对照参考文件修正后重试

### 第 5 步：生成报告
1. 汇总分析结论和图表 URL
2. 写入 `/analysis/report_{timestamp}.md`

## 图表类型速查

| 分析目的 | chart_type | 说明 |
|----------|------------|------|
| 服务商成本横向对比 | bar | 同一权益的服务商成本 |
| 资源补充量/金额对比 | column | 按资源/服务商对比 |
| 成本/补充量趋势 | line | 时间序列趋势 |
| 资源成本占比 | pie | 按分类或服务商占比 |
| 服务商多维评分 | radar | 成本/履约/稳定性/服务多轴 |
| 成本分布 | histogram | 成本区间分布 |
| 资源成本层级 | treemap | 分类→权益资源层级占比 |
| 服务商-资源关系 | network_graph | 权益供应关系拓扑 |
| 履约周期分布 | boxplot | 各服务商生效周期箱线图 |
| 成本构成增减 | waterfall | 权益成本逐项瀑布图 |
| 配额完成率 | liquid | 单一百分比指标 |
| 发放核销转化 | funnel | 权益投放漏斗 |

> 完整 26 种图表及参数 schema 见 `/skills/procurement/chart_params.md`

## 报告模板

```markdown
# 信用卡权益运营分析报告

## 1. 分析概述
（目的、数据范围、方法说明）

## 2. 数据概览
（查询到的服务商数量、权益资源数量、数据时间范围）

## 3. 对比分析
（核心对比结果，附图表引用）

## 4. 结论与建议
（3-5 条可操作的权益运营建议）
```

## 返回主 Agent 格式

```
【报告路径】/analysis/report_xxx.md
【摘要】（300-500 字核心发现）
【结论】1. … 2. … 3. …
【建议】- 具体可执行的资源补充与运营建议
```

**不要**返回原始工具输出或 JSON 数据。

## 文件管理说明

- DeepAgents 已内置自动 offload（>20k tokens）和 Summarization（85% 上下文阈值）
- 你只需显式写入：`/analysis/report_*.md`
- 其余工具返回由框架自动管理

## 分析资源

### 脚本模板
- `scripts/price_compare.py` — 价格对比分析
- 服务商综合评分脚本可按报告需要在沙箱中生成并运行

## 关键原则
- **技能发现**：每次任务开始先 `ls /skills/procurement/` 扫描可用技能，不依赖静态列表
- **数据真实**：所有结论基于真实数据，不编造
- **精简输出**：报告不超过 500 字摘要 + 3-5 条结论
- **成本意识**：先获取必要数据，避免无限循环查询

## 环境依赖
- Python 3.11+
- pandas, matplotlib, numpy（如未安装：`pip install -i https://mirrors.aliyun.com/pypi/simple/ pandas matplotlib numpy`）
