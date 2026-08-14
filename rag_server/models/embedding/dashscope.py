"""DashScope（阿里云通义）嵌入服务。

使用 dashscope SDK 调用文本嵌入 API。
注意：单次最多 20 条文本，超出需分批。
"""

import asyncio
from typing import List, Optional
from http import HTTPStatus

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import Embedding


@register("embedding", "dashscope")
class DashScopeEmbedding(Embedding):
    """基于 DashScope SDK 的嵌入实现。"""

    MAX_BATCH_SIZE = 20

    def __init__(self, api_key: str = "", model: str = "text-embedding-v3", **kwargs):
        import dashscope
        dashscope.api_key = api_key
        self.model = model

    @timeit
    async def embed(self, texts: List[str]) -> List[List[float]]:
        import dashscope
        loop = asyncio.get_event_loop()

        all_embeddings = []
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i:i + self.MAX_BATCH_SIZE]
            resp = await loop.run_in_executor(
                None,
                lambda: dashscope.TextEmbedding.call(
                    model=self.model,
                    input=batch,
                ),
            )
            if resp.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"DashScope embedding failed: {resp.status_code} {resp.message}"
                )
            all_embeddings.extend(
                item["embedding"] for item in resp.output["embeddings"]
            )
        return all_embeddings