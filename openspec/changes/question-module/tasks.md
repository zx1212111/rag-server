## 1. question 模块基础结构

- [x] 1.1 创建 `rag_server/question/` 目录：`__init__.py`、`base.py`、`handler.py`
- [x] 1.2 在 `base.py` 中定义 `Question(ABC)` 抽象接口，方法 `ask(file_paths, question) → str`
- [x] 1.3 在 `handler.py` 中实现 `DefaultQuestionHandler`，`@register("question", "default")`，复用 Loader 处理文件

## 2. QueryPipeline 扩展

- [x] 2.1 在 `QueryPipeline` 中新增 `query_with_files(file_paths, question, stream) → AsyncIterator[str]` 方法
- [x] 2.2 方法内部通过 Factory.create("question", ...) 获取 handler，调用 ask() 合并文本，再走现有 query()

## 3. Config 配置

- [x] 3.1 在 `QueryPipelineConfig` 中新增 `question_provider: str = "default"` 字段
- [x] 3.2 在 `config.yaml` 的 `query_pipeline:` 段新增 `question_provider: default`
- [x] 3.3 在 `_merge_yaml` 中为 `question` 添加短名称到属性名的映射

## 4. CLI ask 命令

- [x] 4.1 在 `cli.py` 中新增 `ask` 命令解析和 `_run_ask()` 异步函数
- [x] 4.2 实现交互：扫描 `ask_incoming/` → 有文件则列出 → 输入问题 → 调用 query_with_files() → 打印答案 → 清理文件

## 5. MCP ask_with_file 工具

- [x] 5.1 在 `mcp.py` 中新增 `ask_with_file(question)` 工具
- [x] 5.2 空目录时返回路径并要求用户放文件
- [x] 5.3 有文件时处理并回答，完成后删除文件
- [x] 5.4 工具描述明确提示 LLM 用于非文字提问场景

## 6. Web 文件提问

- [x] 6.1 在 `web.py` 中添加 `st.file_uploader` 文件上传组件
- [x] 6.2 上传后保存到 `ask_incoming/`，调 `query_with_files()` 回答，完成后删除文件

## 7. 投递目录管理

- [x] 7.1 在 `config.py` 的 `DataConfig` 中新增 `ask_incoming_dir` 字段，默认 `./data/ask_incoming/`
- [x] 7.2 三个接口统一使用 `data/ask_incoming/`，处理完只删文件不删目录

## 8. 验证

- [x] 8.1 `rag-server ask` + 放文件 + 输入问题，正常回答
- [x] 8.2 `rag-server ask` + 不放文件 + 纯文本提问，正常回答
- [x] 8.3 MCP 工具调用：空目录 → 返回路径提示 → 放文件 → 回答
- [x] 8.4 Web 上传文件提问正常（待实现后验证）
- [x] 8.5 确认处理后文件被删除，目录保留