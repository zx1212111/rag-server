## Context

当前 README.md 过于简略（48 行），不反映项目的实际能力和设计理念。见 proposal.md 了解动机。

## Goals / Non-Goals

**Goals:**
- README 清晰说明项目定位：LLM-first 的 MCP RAG Server
- 用流程图展示两条核心管线：Ingestion Pipeline (文件处理管线) 和 Query Pipeline (问答管线)
- 列出 MCP 工具的签名和用途
- 列出配置文件的全部字段及说明
- 列出支持的文件格式及其处理方式
- 快速开始能在三五行命令内完成

**Non-Goals:**
- 不包含架构深入解读（可放在单独文档）
- 不包含插件开发指南（可放在单独文档）
- 不改动代码逻辑或功能行为

## Decisions

### 1. README 语言风格与结构

英文为主，括号中文注释关键概念名。与用户确认的写法。

章节顺序：
1. 项目名 + 一句话定位
2. Ingestion Pipeline (文件处理管线) — 带 ASCII 流程图
3. Query Pipeline (问答管线) — 带 ASCII 流程图
4. Quick Start (快速开始)
5. Configuration (配置) — config.yaml 全字段表
6. Supported File Formats (支持的文件格式)
7. MCP Tools (MCP 工具参考)
8. Web Interface (Web 界面)

### 2. 流程图使用 ASCII 方框字符

用户要求用带方框的流程图，两个管线各自一张图：

**Ingestion Pipeline:**
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Input   │→ │  Loader  │→ │  Cleaner │→ │ Splitter │→ │  Index   │→ │  BM25   │
│  Files   │  │(per ext) │  │(default) │  │ (1000ch) │  │(Chroma)  │  │(rebuild)│
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Query Pipeline:**
```
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Query   │→ │Hybrid Retrieve│→ │  Rank   │→ │  Prompt  │→ │   LLM    │
│          │  │(Vector+BM25) │  │ (Fusion) │  │  Builder  │  │  Generate│
└──────────┘  └──────────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 3. 不改变 pyproject.toml 的 description

项目名已在 README 中明确定位为 "MCP RAG Server"，pyproject.toml 的 description 字段作为包元数据保留现有描述即可。

### 4. 执行方式

README 需要实际写入根目录的 README.md 文件。由 tasks.md 中的任务驱动，通过 Edit 或 Write 工具完成。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| ASCII 流程图在部分 Markdown 渲染器中可能对齐异常 | 使用等宽字符 + 简单方框图，避免复杂连接线 |
| 配置表过多可能让 README 显得冗长 | 表格放在靠后的章节（第 5 节），快速开始在前 |