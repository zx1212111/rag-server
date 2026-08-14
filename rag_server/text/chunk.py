"""Chunk 数据结构定义。"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Chunk:
    """文档分块后的基本单元。"""
    id: str                    # md5("{doc_id}_{index}_{content[:64]}")[:16]
    doc_id: str                # md5(源文件路径)[:12]
    chunk_index: int           # 文件内第几块（从0开始）
    content: str               # 切分文本
    start_char: int            # 在源文件中的起始位置
    end_char: int              # 结束位置
    metadata: Dict = field(default_factory=dict)  # 来源路径、图片引用等

    @staticmethod
    def build_id(doc_id: str, index: int, content: str) -> str:
        raw = f"{doc_id}_{index}_{content[:64]}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]