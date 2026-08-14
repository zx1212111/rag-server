"""OpenAI 兼容协议的 Embedding 实现。

支持 OpenAI、Ollama 等兼容 OpenAI API 格式的嵌入服务。
"""

from typing import List

import httpx

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import Embedding


@register("embedding", "openai")
class OpenAIEmbedding(Embedding):
    """基于 OpenAI 兼容协议（/v1/embeddings）的嵌入实现。"""

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = "", model: str = "text-embedding-3-small"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    @timeit
    async def embed(self, texts: List[str]) -> List[List[float]]:
        payload = {
            "model": self.model,
            "input": texts,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
            return [item["embedding"] for item in result["data"]]