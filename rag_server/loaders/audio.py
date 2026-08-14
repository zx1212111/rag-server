"""音频文件加载器。

支持 .mp3/.wav/.m4a 格式，直接调用 ASR 将语音转为文字。
"""

import os
from typing import Dict, List

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import BaseLoader, LoaderOutput


@register("loader", "audio")
class AudioLoader(BaseLoader):
    """音频文件加载器，支持 .mp3/.wav/.m4a，通过 ASR 转文字。"""

    extensions = [".mp3", ".wav", ".m4a"]

    def __init__(self, asr_provider: str = "dashscope"):
        self.asr_provider = asr_provider

    @timeit
    async def load(self, file_path: str) -> LoaderOutput:
        from rag_server.registry import Factory
        import rag_server.models.asr.dashscope  # 触发 @register

        asr = Factory.create("asr", self.asr_provider)
        text = await asr.transcribe(file_path)

        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        return LoaderOutput(
            md_text=f"# {doc_name}\n\n{text}",
            assets=[],
            metadata={"source": file_path, "type": "audio"},
        )