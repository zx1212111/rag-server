## Why

当前 `rag-server` 只支持纯文本问答（`rag-server query "..."`），无法处理带图片、视频、音频等附件的提问。用户需要将文件先手动导入知识库，再提问——流程割裂。需要一个直接"带着文件提问"的模式。

## What Changes

- **新增** `rag_server/question/` 模块：`Question(ABC)` 抽象接口 + `DefaultQuestionHandler` 实现
- **新增** `rag-server ask` CLI 交互命令：创建临时目录 → 用户放文件 → 输入问题 → 回答
- **修改** `QueryPipeline`：新增 `query_with_files(files, question)` 方法，接收文件列表+问题文本
- **修改** `config.yaml` / `config.py`：`query_pipeline` 新增 `question_provider` 配置项
- **新增** 临时文件目录管理：处理完成后自动清理

## Capabilities

### New Capabilities

- `question`: 文件提问能力——接收图片/视频/音频/PDF/Word/Markdown 等文件 + 文本问题，自动转写为统一查询文本后执行 RAG 问答

### Modified Capabilities

无。`QueryPipeline` 的改动为新增方法，不影响现有 `query()` 接口。

## Impact

- **新增 1 个目录**：`rag_server/question/`（base.py + handler.py）
- **修改 2 个文件**：`pipeline/query.py`（新增 query_with_files）、`cli.py`（新增 ask 命令）
- **修改 config**：`query_pipeline.question_provider` 配置项
- **外部不感知**：现有 MCP 工具、`query` CLI 命令不变
- **依赖不变**：`pyproject.toml` 不变