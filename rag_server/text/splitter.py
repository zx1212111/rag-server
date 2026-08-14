"""文本分块组件。

策略：步距累加 + 上下文重叠。
按段落切分后，按 stride 累加段落长度，在段落边界上确定切断点。
超长段落（大于 stride）在段落内按 stride 切割。
每个 chunk 前后各带 overlap 字符的上下文重叠。
"""

import re
from typing import List, Tuple

from rag_server.registry import register
from rag_server.utils.timer import timeit
from .base import Splitter
from .chunk import Chunk


@register("splitter", "default")
class TextSplitter(Splitter):
    """文本分块器。"""

    def __init__(self, chunk_size: int = 1000, stride: int = 800, **kwargs):
        self.chunk_size = chunk_size
        self.stride = stride

    @timeit
    def split(self, md_text: str, doc_id: str) -> List[Chunk]:
        """将 MD 文本切分为 Chunk 列表。"""
        if not md_text.strip():
            return []

        overlap = (self.chunk_size - self.stride) // 2
        if overlap < 0:
            overlap = 0

        # 1. 获取每个段落在原文中的起止索引
        paragraph_ranges = self._get_paragraph_ranges(md_text)

        # 2. 预处理：任何段落 > stride，在段落内插入断点
        segments = []  # [(start, end), ...]
        for p_start, p_end in paragraph_ranges:
            length = p_end - p_start
            if length > self.stride:
                pos = p_start
                while pos + self.stride < p_end:
                    segments.append((pos, pos + self.stride))
                    pos += self.stride
                segments.append((pos, p_end))  # 剩余部分
            else:
                segments.append((p_start, p_end))

        # 3. 从第一段开始累加，和 stride 比较，确定切断点
        cuts = []
        accumulated = 0
        last_cut = 0

        for start, end in segments:
            seg_len = end - start
            if accumulated + seg_len <= self.stride:
                accumulated += seg_len
            else:
                cuts.append(last_cut)
                accumulated = seg_len
            last_cut = end

        if accumulated > 0:
            cuts.append(last_cut)  # 最后一个切断点即全文结尾

        # 4. 根据切断点构建 chunk，前后各加 overlap
        chunks: List[Chunk] = []
        prev_cut = 0

        for i, cut in enumerate(cuts):
            chunk_start = 0 if i == 0 else max(0, prev_cut - overlap)
            chunk_end = len(md_text) if i == len(cuts) - 1 else min(len(md_text), cut + overlap)
            content = md_text[chunk_start:chunk_end]
            chunks.append(
                self._make_chunk(content, doc_id, i, chunk_start, chunk_end)
            )
            prev_cut = cut

        return chunks

    def _get_paragraph_ranges(self, text: str) -> List[Tuple[int, int]]:
        """返回每个段落在原文中的 (start, end) 位置（不含空行分隔符）。"""
        ranges = []
        pos = 0
        for m in re.finditer(r"\n\s*\n", text):
            if m.start() > pos:
                ranges.append((pos, m.start()))
            pos = m.end()
        if pos < len(text):
            ranges.append((pos, len(text)))
        return ranges

    def _make_chunk(self, content: str, doc_id: str, index: int,
                    start: int, end: int) -> Chunk:
        return Chunk(
            id=Chunk.build_id(doc_id, index, content[:64]),
            doc_id=doc_id,
            chunk_index=index,
            content=content,
            start_char=start,
            end_char=end,
        )