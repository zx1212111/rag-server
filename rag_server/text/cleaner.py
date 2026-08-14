"""文本清洗组件。

可插拔设计：注册多种清洗策略，通过配置选择。
"""

import re
from abc import ABC, abstractmethod

from rag_server.registry import register
from rag_server.utils.timer import timeit


class BaseCleaner(ABC):
    @abstractmethod
    def clean(self, text: str) -> str:
        ...


@register("cleaner", "default")
class DefaultCleaner(BaseCleaner):
    """标准清洗：去多余空格、合行、规格化换行、修标点。"""

    @timeit
    def clean(self, text: str) -> str:
        # 去除多余空格
        text = re.sub(r" +", " ", text)
        # 断行合并（段落内换行合并为空格）
        lines = text.split("\n")
        merged = []
        for line in lines:
            stripped = line.strip()
            if stripped == "":
                merged.append("")
            elif stripped.startswith("#"):
                merged.append(stripped)
            elif stripped.startswith(("- ", "* ", "1. ", ">")):
                merged.append(stripped)
            else:
                if merged and merged[-1] != "" and not merged[-1].endswith((".", "!", "?", "。", "！", "？")):
                    merged[-1] += " " + stripped
                else:
                    merged.append(stripped)
        text = "\n".join(merged)
        # 去除连续空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


@register("cleaner", "minimal")
class MinimalCleaner(BaseCleaner):
    """仅去多余空格和连续空行。"""

    @timeit
    def clean(self, text: str) -> str:
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


@register("cleaner", "verbose")
class VerboseCleaner(BaseCleaner):
    """仅去首尾空格，保留原始排版。"""

    @timeit
    def clean(self, text: str) -> str:
        return text.strip()