"""Anthropic Claude API 的 LLM 实现。

支持 Claude API（/v1/messages 端点）。
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import LLM


@register("llm", "anthropic")
class AnthropicLLM(LLM):
    """基于 Anthropic Messages API 的 LLM 实现。"""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514"):
        self.base_url = "https://api.anthropic.com/v1"
        self.api_key = api_key
        self.model = model
        self._headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

    @timeit
    async def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        # 转换消息格式：OpenAI 格式 → Anthropic 格式
        system = ""
        converted: List[Dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                converted.append({"role": msg["role"], "content": msg["content"]})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": converted,
            "stream": stream,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120) as client:
            if stream:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
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
                                if chunk.get("type") == "content_block_delta":
                                    delta = chunk.get("delta", {})
                                    content = delta.get("text", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
            else:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                content_blocks = result.get("content", [])
                for block in content_blocks:
                    if block.get("type") == "text":
                        yield block.get("text", "")