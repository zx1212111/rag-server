"""ChunkStitcher：连续 chunk 拼接器（可选，默认关闭）。

开启后，根据 start_char / end_char 区间去重拼接，返回连续的原始内容。
"""

from typing import Dict, List, Optional

from rag_server.utils.timer import timeit


class ChunkJoiner:
    """拼接连续 chunk，去除重叠部分。"""

    def __init__(self, enabled: bool = False, dedup: bool = True):
        self.enabled = enabled
        self.dedup = dedup

    @timeit
    def stitch(self, chunks: List[Dict]) -> str:
        """拼接 chunk 列表为连续文本。

        参数:
            chunks: 按检索顺序排列的 chunk 条目（含 text / start_char / end_char）

        返回:
            拼接后的完整文本
        """
        if not self.enabled or len(chunks) <= 1:
            return "\n\n".join(c.get("text", "") for c in chunks)

        if not self.dedup:
            return "\n\n".join(c.get("text", "") for c in chunks)

        # 去重：按 start_char 排序，去除重叠部分
        sorted_chunks = sorted(chunks, key=lambda c: c.get("start_char", 0))
        merged: List[str] = []
        last_end = 0

        for chunk in sorted_chunks:
            start = chunk.get("start_char", 0)
            end = chunk.get("end_char", 0)
            text = chunk.get("text", "")

            if start >= last_end:
                # 无重叠，直接追加
                merged.append(text)
            elif end > last_end:
                # 部分重叠，取不重叠的尾部
                overlap = last_end - start
                merged.append(text[overlap:])
            # else: 完全重叠，跳过

            last_end = max(last_end, end)

        return "\n".join(merged)