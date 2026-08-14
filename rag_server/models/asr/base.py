"""ASR 语音识别抽象接口。"""

from abc import ABC, abstractmethod


class ASR(ABC):
    """语音识别能力提供者抽象接口。"""

    @abstractmethod
    async def transcribe(self, audio_path: str) -> str:
        """将音频文件转为文字，返回完整文本。"""
        ...