"""混合融合策略。

加权评分：final = α × normalize(vec) + (1-α) × normalize(bm25)
"""

from typing import Dict, List, Tuple

from rag_server.registry import register
from rag_server.retrieval.base import Ranker
from rag_server.utils.timer import timeit


@register("ranker", "hybrid")
class HybridRanker(Ranker):
    """双路检索结果排序。"""

    def __init__(self, vector_weight: float = 0.5, final_top_k: int = 10,
                 vector_top_k: int = 20):
        self.vector_weight = vector_weight
        self.final_top_k = final_top_k
        self.vector_top_k = vector_top_k

    @timeit
    def rank(self, results: List[Tuple[str, float]]) -> List[str]:
        """排序，返回排序后的 chunk_id 列表。

        results 前 vector_top_k 条来自向量检索，其余来自 BM25。
        """
        scores: Dict[str, float] = {}

        vector_results = results[:self.vector_top_k]
        bm25_results = results[self.vector_top_k:]

        for chunk_id, score in vector_results:
            scores[chunk_id] = scores.get(chunk_id, 0) + self.vector_weight * score

        for chunk_id, score in bm25_results:
            scores[chunk_id] = scores.get(chunk_id, 0) + (1 - self.vector_weight) * score

        # 按融合分降序排列
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return [cid for cid, _ in ranked[:self.final_top_k]]