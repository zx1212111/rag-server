"""默认文件提问处理器。"""

import logging
import os
from typing import List, Optional

from rag_server.loaders.base import BaseLoader, LoaderOutput
from rag_server.registry import Factory, auto_register, register, _registry
from rag_server.utils.timer import timeit
from .base import Question

auto_register("rag_server.loaders")

logger = logging.getLogger(__name__)


@timeit
def _resolve_loader(file_path: str) -> Optional[BaseLoader]:
    """根据文件扩展名选择加载器。"""
    ext = os.path.splitext(file_path)[1].lower()
    for name, cls in _registry.get("loader", {}).items():
        if ext in getattr(cls, "extensions", []):
            return Factory.create("loader", name)
    return None


@register("question", "default")
class DefaultQuestionHandler(Question):
    """默认文件提问处理器。复用已有 Loader 将文件转为 MD 文本。"""

    async def ask(self, file_paths: List[str], question: str) -> str:
        """遍历文件，用 Loader 处理，合并为查询文本。"""
        parts = []
        for fp in file_paths:
            try:
                loader = _resolve_loader(fp)
                if loader is None:
                    logger.warning("不支持的格式，跳过: %s", fp)
                    continue
                output: LoaderOutput = await loader.load(fp)
                if output.md_text.strip():
                    parts.append(output.md_text)
            except Exception as e:
                logger.warning("文件处理失败，跳过 %s: %s", fp, e)
                continue

        if parts:
            combined = "\n\n".join(parts) + f"\n\n{question}"
        else:
            combined = question

        return combined