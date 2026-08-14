"""OpenAI 兼容协议的 LLM 实现。

支持 OpenAI、Ollama、vLLM 等兼容 OpenAI API 格式的后端。
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import LLM


@register("llm", "openai")
class OpenAILLM(LLM):
    """基于 OpenAI 兼容协议（/v1/chat/completions）的 LLM 实现。"""

    def __init__(self, base_url: str = "https://api.openai.com/v1", api_key: str = "", model: str = "gpt-4o-mini"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    @timeit
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            if stream:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                choices = chunk.get("choices", [])
                                if not choices:
                                    continue
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            else:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                yield content