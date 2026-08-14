## Why

开发过程中需要了解各环节的耗时分布，定位性能瓶颈。当前代码没有任何计时埋点，无法区分"哪段代码慢"。

## What Changes

- 新增 `rag_server/utils/timer.py`：提供 `@timeit` 装饰器，在函数执行前后计时并输出日志
- 在关键路径的 async 方法上添加 `@timeit` 装饰器，覆盖 ingestion 和 query 全链路
- 日志格式：`[timing] <operation_name>: <duration_ms>ms [extra_info]`

## Capabilities

无。纯工具性变更，不涉及外部行为变更。

## Impact

- 新增 `rag_server/utils/` 目录，含 `__init__.py` 和 `timer.py`
- 修改 6-8 个文件（在 async 方法上加 `@timeit` 装饰器）
- 无外部接口变更（MCP 工具、CLI 命令、配置格式均不变）
- 日志会增加 `[timing]` 前缀的行，不影响其他日志