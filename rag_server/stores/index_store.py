"""索引对照表：index.json 的读写管理。

存储 chunk_id → 全文 + metadata 的映射关系。
检索时通过 chunk_id 查询完整文本。

_save() 使用原子写入（写临时文件 → rename），避免崩溃导致文件损坏。
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


class IndexStore:
    """index.json 索引管理。"""

    def __init__(self, path: str = "./data/index.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[Dict[str, Dict]] = None

    def _load(self) -> Dict[str, Dict]:
        if self._cache is not None:
            return self._cache
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
                self._cache = data if isinstance(data, dict) else {}
        else:
            self._cache = {}
        return self._cache

    def _save(self):
        """原子写入：写临时文件 → rename 覆盖原文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self.path.parent, prefix=".index_tmp_",
            delete=False, encoding="utf-8",
        ) as f:
            tmp_path = f.name
            json.dump(self._cache or {}, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def add(self, chunk_id: str, text: str, doc_id: str = "",
            doc_path: str = "", chunk_index: int = 0,
            start_char: int = 0, end_char: int = 0,
            metadata: Optional[Dict] = None):
        """添加或更新一个 chunk 的索引。"""
        data = self._load()
        data[chunk_id] = {
            "text": text,
            "doc_id": doc_id,
            "doc_path": doc_path,
            "chunk_index": chunk_index,
            "start_char": start_char,
            "end_char": end_char,
            "metadata": metadata or {},
        }
        self._save()

    def add_batch(self, entries: List[Dict]):
        """批量添加 chunk 索引。"""
        data = self._load()
        for entry in entries:
            data[entry["chunk_id"]] = {
                "text": entry["text"],
                "doc_id": entry.get("doc_id", ""),
                "doc_path": entry.get("doc_path", ""),
                "chunk_index": entry.get("chunk_index", 0),
                "start_char": entry.get("start_char", 0),
                "end_char": entry.get("end_char", 0),
                "metadata": entry.get("metadata", {}),
            }
        self._save()

    def get(self, chunk_id: str) -> Optional[Dict]:
        """根据 chunk_id 获取全文和 metadata。"""
        data = self._load()
        return data.get(chunk_id)

    def get_texts(self, chunk_ids: List[str]) -> List[str]:
        """批量获取 chunk 文本（用于 BM25 重建）。"""
        data = self._load()
        texts = []
        for cid in chunk_ids:
            entry = data.get(cid)
            if entry:
                texts.append(entry["text"])
        return texts

    def get_all_texts(self) -> List[str]:
        """获取所有 chunk 的文本列表（用于 BM25 全量重建）。"""
        data = self._load()
        return [entry["text"] for entry in data.values()]

    def get_all_entries(self) -> List[Dict]:
        """获取所有 chunk 条目。"""
        data = self._load()
        return [
            {"chunk_id": cid, **entry}
            for cid, entry in data.items()
        ]

    def count_chunks(self) -> int:
        """统计总 chunk 数。"""
        data = self._load()
        return len(data)

    def count_unique_docs(self) -> int:
        """统计唯一文档数。"""
        data = self._load()
        return len(set(entry.get("doc_id", "") for entry in data.values() if entry.get("doc_id")))

    def clear(self):
        self._cache = {}
        self._save()