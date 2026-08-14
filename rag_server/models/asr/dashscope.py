"""DashScope（阿里云通义）语音识别实现。

使用 REST API 将音频转为文字。
"""

import base64
import json
import os
from typing import Optional

import httpx

from rag_server.registry import register
from .base import ASR


@register("asr", "dashscope")
class DashScopeASR(ASR):
    """基于 DashScope 语音识别 API 的实现。"""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        **kwargs,
    ):
        self.base_url = base_url or os.getenv("ASR_BASE_URL", "")
        self.api_key = api_key or os.getenv("ASR_API_KEY", "")
        self.model = model or os.getenv("ASR_MODEL", "qwen-audio-3.0-asr-flash")

    async def transcribe(self, audio_path: str) -> str:
        """将音频文件转为文字。"""
        # 1. 读取音频文件并 Base64 编码
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        data_uri = f"data:audio/wav;base64,{audio_b64}"

        # 2. 构造请求体
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": data_uri,
                                },
                            }
                        ],
                    }
                ]
            },
            "parameters": {
                "format": "wav",
                "sample_rate": 16000,
            },
        }

        # 3. 发送请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                content=json.dumps(payload),
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope ASR failed: {response.status_code} {response.text}"
            )

        # 4. 解析响应
        result = response.json()
        text = self._extract_text(result)
        if not text:
            raise RuntimeError(f"DashScope ASR: 未能从响应中提取文字: {response.text}")
        return text

    def _extract_text(self, result: dict) -> Optional[str]:
        """从 DashScope 响应中提取识别文字。"""
        try:
            choices = result.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                # content 可能是字符串或列表
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = [item.get("text", "") for item in content if "text" in item]
                    return "".join(texts)
            # 兼容旧格式: output.text
            return result.get("output", {}).get("text", "")
        except (KeyError, IndexError, TypeError):
            return None