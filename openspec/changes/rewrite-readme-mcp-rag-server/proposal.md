## Why

当前 README.md 仅 48 行，与项目实际能力严重不匹配。项目支持六类文件加载（PDF/MD/Word/图片/音频/视频）、双路混合检索、多供应商 AI 模型、MCP 协议与 Web 界面双接口，但 README 没有体现这些能力，也没有说明项目的核心设计理念——LLM-first、MCP-native。需要一份完整的 README 让使用者（人和 LLM 客户端配置者）能快速理解项目定位和用法。

## What Changes

- 重写 `README.md`：从 48 行扩写为完整的项目文档
- 修改 `pyproject.toml` 中的项目描述（可选，如果描述需要更新）
- 纯文档变更，无功能代码修改，无行为变更

## Capabilities

### New Capabilities

无（纯文档变更）。

### Modified Capabilities

无（纯文档变更）。

## Impact

- `README.md`：完全重写
- `pyproject.toml`：可能更新 description 字段
- 无代码、API、依赖变更