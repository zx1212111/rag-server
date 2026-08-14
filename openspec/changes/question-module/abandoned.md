# 废案说明

## 变更：question-module

**废弃原因：** question 模块（文件提问）的定位被重新审视。它的本质不是 RAG 操作（检索知识库），而是 Agent 问答工具（直接分析用户提供的文件）。作为 RAG 管线的一部分设计是不合理的。

**处理方式：**
- `rag_server/question/` 目录移至 `_archived/question-module/` 备用（后续 Agent 设计可能用到）
- `QueryPipeline.query_with_files()` 方法删除
- `config.py / config.yaml` 中 `question_provider` 配置项删除
- MCP 工具 `ask_with_file` 删除
- CLI `ask` 命令删除
- Web 界面文件上传功能删除

**备用的模块代码位置：** `_archived/question-module/`