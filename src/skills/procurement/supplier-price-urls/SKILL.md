---
name: provider-resource-urls
description: >
  权益服务商公开资源页面映射表。根据系统查到的权益资源名和服务商名，
  查找公开信息页面，供后续抓取成本、有效期、适用范围和履约规则。
---

# 权益服务商公开资源页面映射

## 用途

提供「权益资源名称 + 服务商名称 → 公开信息 URL」的映射查询，
是外部数据采集的第一步。

## 数据文件

映射数据在 `data/url_mapping.yaml`。

```yaml
mappings:
  - resource_name: "权益或营销资源名称"
    provider: "权益服务商名称"
    url: "报价页面URL"
```

> URL 页面可包含公开价格、有效期、覆盖范围、使用门槛和服务说明。
> 爬虫技能可一次性提取全部数据，无需多次请求。

## 使用流程

1. 用 `read_file` 读取 `data/url_mapping.yaml`
2. 按 MCP 工具返回的权益资源名 + 服务商名查找匹配条目
3. 匹配逻辑：
   - `resource_name` 使用包含匹配
   - `provider` 使用包含匹配
   - 两个字段同时匹配才算命中
4. 将找到的 URL 列表传给爬虫技能（如 `web-scraper`）获取最新报价和产品详情

## 示例

```
系统返回: resource_name="视频会员月卡", provider="星享数字权益"
→ 查 url_mapping.yaml
→ 命中 resource_name + provider
→ 传给 web-scraper 获取公开价格、有效期和使用规则
```

## 注意事项

- 映射表由运维人员维护，Agent 只读不写
- 如未找到匹配条目 → 改用 `web_search` 搜索市场价格
- 权益资源可能存在别名，匹配时用包含关系而非精确匹配
- 同类权益可能有多个服务商条目，应全部收集后对比
