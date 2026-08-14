"""Prompt 组装抽象。管线只调 build()，不关心模板和裁剪策略。"""

from abc import ABC, abstractmethod
from typing import List, Optional

from rag_server.registry import register


class PromptBuilder(ABC):
    """Prompt 组装抽象。管线只调 build()，不关心模板内容。"""

    @abstractmethod
    async def build(self, context: str, query: str) -> List[dict]:
        """返回 messages 列表 [{"role": "system", "content": ...}]"""
        ...


@register("prompt_builder", "default")
class DefaultPromptBuilder(PromptBuilder):
    """默认 Prompt 组装器。使用固定 SYSTEM_PROMPT 模板 + 上下文裁剪。"""

    SYSTEM_PROMPT = """你是一个知识库助手。请基于以下文档内容回答问题。
如果文档中没有相关信息，直接说"未找到相关信息"，不要编造。

文档内容：

{context}

---

用户问题：{query}"""

    def __init__(self, max_chars: int = 30000):
        self.max_chars = max_chars

    def _truncate_context(self, context: str) -> Optional[str]:
        """裁剪上下文到 max_chars，优先在句子边界截断。"""
        if not context.strip():
            return None

        if len(context) <= self.max_chars:
            return context

        truncated = context[:self.max_chars]
        last_period = max(
            truncated.rfind("。"),
            truncated.rfind("."),
            truncated.rfind("\n"),
        )
        if last_period > self.max_chars // 2:
            truncated = truncated[:last_period + 1]
        return truncated

    async def build(self, context: str, query: str) -> List[dict]:
        context = self._truncate_context(context)
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT.format(
                context=context, query=query
            )},
        ]