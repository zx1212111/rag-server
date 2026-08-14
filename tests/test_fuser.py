"""融合器单元测试。"""

import pytest

from rag_server.retrieval.fusion import HybridRanker


class TestHybridRanker:
    """测试 HybridRanker 融合排序功能。"""

    def setup_method(self):
        self.fusion = HybridRanker(vector_weight=0.5, final_top_k=5)

    def test_fuse_empty(self):
        """空结果应返回空列表。"""
        assert self.fusion.rank([]) == []

    def test_fuse_vector_only(self):
        """仅向量结果应正常排序。"""
        results = [("a", 0.9), ("b", 0.8)]
        fused = self.fusion.rank(results)
        assert len(fused) > 0
        assert fused[0] == "a"

    def test_fuse_bm25_only(self):
        """仅 BM25 结果应正常处理。"""
        # 所有结果视作向量结果，BM25 部分为空
        results = [("a", 0.9)]
        assert "a" in self.fusion.rank(results)

    def test_fuse_mixed_hybrid(self):
        """向量+BM25 混合结果应正确融合。"""
        results = [("a", 0.9), ("b", 0.8), ("c", 0.7), ("d", 0.6)]
        fused = self.fusion.rank(results)
        assert len(fused) >= 1

    def test_fuse_top_k_limit(self):
        """结果数应不超过 final_top_k。"""
        fusion = HybridRanker(vector_weight=0.5, final_top_k=3)
        results = [("a", 0.9), ("b", 0.8), ("c", 0.7), ("d", 0.6), ("e", 0.5)]
        fused = fusion.rank(results)
        assert len(fused) <= 3

    def test_fuse_weight_extreme(self):
        """极端权重（1.0 或 0.0）应正常工作。"""
        results = [("a", 0.9), ("b", 0.8), ("c", 0.7)]

        fusion_vec = HybridRanker(vector_weight=1.0, final_top_k=5, vector_top_k=2)
        assert len(fusion_vec.rank(results)) > 0

        fusion_bm25 = HybridRanker(vector_weight=0.0, final_top_k=5, vector_top_k=2)
        assert len(fusion_bm25.rank(results)) > 0