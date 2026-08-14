"""BM25 关键词检索模块。

基于 rank_bm25 库，中文预处理使用 jieba 分词。
从 index.json 全量重建索引。
"""

import json
import os
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

from rag_server.utils.timer import timeit


class BM25Index:
    """BM25 稀疏索引。"""

    def __init__(self, sparse_dir: str = "./data/sparse"):
        self.sparse_dir = Path(sparse_dir)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        self._bm25 = None
        self._corpus: List[str] = []

    def rebuild_from_texts(self, texts: List[str]):
        """从文本列表重建 BM25。"""
        import jieba
        from rank_bm25 import BM25Okapi

        self._corpus = texts
        tokenized = [list(jieba.cut(t)) for t in texts]
        self._bm25 = BM25Okapi(tokenized)
        self._save()

    def rebuild_from_index(self, index_store):
        """从 IndexStore 全量重建 BM25。"""
        texts = index_store.get_all_texts()
        self.rebuild_from_texts(texts)

    @timeit
    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """关键词检索，返回 [(chunk_id, score), ...]。

        注意：当前实现仅返回索引位置和分数。
        外部调用方需配合 IndexStore 获取完整文本。
        """
        if self._bm25 is None:
            self._load()
            if self._bm25 is None:
                return []

        import jieba
        tokenized_query = list(jieba.cut(query))
        scores = self._bm25.get_scores(tokenized_query)

        # 取 Top-K
        indexed = [(i, scores[i]) for i in range(len(scores))]
        indexed.sort(key=lambda x: -x[1])
        top = indexed[:top_k]

        # 归一化分数到 [0, 1]
        if top and top[0][1] > 0:
            max_score = top[0][1]
            return [(str(i), s / max_score) for i, s in top]
        return [(str(i), 0.0) for i, s in top]

    def _save(self):
        """持久化 BM25 对象。"""
        import jieba
        from rank_bm25 import BM25Okapi

        # 保存 corpus 文本
        corpus_path = self.sparse_dir / "corpus.json"
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(self._corpus, f, ensure_ascii=False)

        # 保存 tokenized corpus 和 BM25 参数
        tokenized = [list(jieba.cut(t)) for t in self._corpus]
        data = {
            "corpus": self._corpus,
            "tokenized": tokenized,
        }
        with open(self.sparse_dir / "bm25.pkl", "wb") as f:
            pickle.dump(data, f)

    def _load(self):
        """从磁盘加载 BM25。"""
        from rank_bm25 import BM25Okapi

        corpus_path = self.sparse_dir / "corpus.json"
        if not corpus_path.exists():
            return

        with open(corpus_path, encoding="utf-8") as f:
            self._corpus = json.load(f)

        import jieba
        tokenized = [list(jieba.cut(t)) for t in self._corpus]
        self._bm25 = BM25Okapi(tokenized)