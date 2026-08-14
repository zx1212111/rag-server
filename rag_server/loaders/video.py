"""视频文件加载器。

两步处理：ffmpeg 提取音频 → ASR 语音转文字 → 输出 MD 文本。
支持 .mp4/.avi/.mov/.mkv 格式。
"""

import os
import subprocess
import tempfile
from typing import Dict, List

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import BaseLoader, LoaderOutput


@register("loader", "video")
class VideoLoader(BaseLoader):
    """视频文件加载器。

    Step 1: ffmpeg 提取音频为 16kHz 单声道 WAV
    Step 2: ASR 将音频转为文字
    """

    extensions = [".mp4", ".avi", ".mov", ".mkv"]

    def __init__(self, asr_provider: str = "dashscope"):
        self.asr_provider = asr_provider

    def _extract_audio(self, video_path: str) -> str:
        """用 ffmpeg 提取音频到系统临时目录，返回临时 WAV 路径。"""
        fd, audio_path = tempfile.mkstemp(suffix="_audio.wav")
        os.close(fd)
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1",
             "-y", audio_path],
            capture_output=True,
            check=True,
        )
        return audio_path

    @timeit
    async def load(self, file_path: str) -> LoaderOutput:
        # Step 1: 提取音频
        audio_path = self._extract_audio(file_path)

        # Step 2: ASR 转文字
        from rag_server.registry import Factory
        import rag_server.models.asr.dashscope  # 触发 @register

        asr = Factory.create("asr", self.asr_provider)
        text = await asr.transcribe(audio_path)

        # 清理临时音频文件
        if os.path.exists(audio_path):
            os.remove(audio_path)

        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        return LoaderOutput(
            md_text=f"# {doc_name}\n\n{text}",
            assets=[],
            metadata={"source": file_path, "type": "video"},
        )