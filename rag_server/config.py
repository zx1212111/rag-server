"""配置加载模块。

优先级：环境变量 > config.yaml > 默认值
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    provider: str = "openai"          # openai | anthropic
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_chars: int = 30000
    stream: bool = True


@dataclass
class EmbeddingConfig:
    provider: str = "openai"       # openai | dashscope
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "text-embedding-3-small"


@dataclass
class QueryPipelineConfig:
    retriever_provider: str = "hybrid"     # hybrid | vector_only | bm25_only
    ranker_provider: str = "hybrid"        # hybrid | rrf | ...
    prompt_builder_provider: str = "default"  # default | ...
    vector_weight: float = 0.5
    vector_top_k: int = 20
    bm25_top_k: int = 20
    final_top_k: int = 10


@dataclass
class JoinerConfig:
    enabled: bool = False
    dedup: bool = True


@dataclass
class ASRConfig:
    provider: str = "dashscope"
    base_url: str = ""
    api_key: str = ""
    model: str = "qwen-audio-3.0-asr-flash"


@dataclass
class IngestionPipelineConfig:
    """Ingestion 管线各步骤的 provider 配置。"""
    cleaner_provider: str = "default"
    splitter_provider: str = "default"
    chunk_size: int = 1000
    stride: int = 800
    storage_provider: str = "file"
    indexer_provider: str = "chroma"


@dataclass
class DataConfig:
    root: str = "./data"
    input_dir: str = ""        # 运行时自动拼接
    processed_dir: str = ""
    docs_dir: str = ""
    assets_dir: str = ""
    vector_dir: str = ""
    sparse_dir: str = ""
    index_path: str = ""

    def __post_init__(self):
        root = Path(self.root)
        self.input_dir = str(root / "input")
        self.processed_dir = str(root / "processed")
        self.docs_dir = str(root / "docs")
        self.assets_dir = str(root / "assets")
        self.vector_dir = str(root / "vector")
        self.sparse_dir = str(root / "sparse")
        self.ask_incoming_dir = str(root / "ask_incoming")
        self.index_path = str(root / "index.json")


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    ingestion_pipeline: IngestionPipelineConfig = field(default_factory=IngestionPipelineConfig)
    query_pipeline: QueryPipelineConfig = field(default_factory=QueryPipelineConfig)
    stitcher: JoinerConfig = field(default_factory=JoinerConfig)
    data: DataConfig = field(default_factory=DataConfig)


def load_config(path: Optional[str] = None) -> Config:
    """加载配置，优先级：环境变量 > YAML > 默认值"""
    load_dotenv()  # 加载 .env 文件
    config = Config()  # 默认值

    # 加载 YAML
    yaml_path = path or os.getenv("CONFIG_PATH", "./config.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        _merge_yaml(config, raw)

    # 环境变量覆盖
    _apply_env_overrides(config)

    return config


def _merge_yaml(config: Config, raw: dict):
    if "llm" in raw:
        for k, v in raw["llm"].items():
            if hasattr(config.llm, k):
                setattr(config.llm, k, v)
    if "embedding" in raw:
        for k, v in raw["embedding"].items():
            if hasattr(config.embedding, k):
                setattr(config.embedding, k, v)
    if "query_pipeline" in raw:
        for k, v in raw["query_pipeline"].items():
            mapped_r = {"retriever": "retriever_provider", "ranker": "ranker_provider",
                        "prompt_builder": "prompt_builder_provider"}
            attr = mapped_r.get(k, k)
            if hasattr(config.query_pipeline, attr):
                setattr(config.query_pipeline, attr, v)
    if "stitcher" in raw:
        for k, v in raw["stitcher"].items():
            if hasattr(config.stitcher, k):
                setattr(config.stitcher, k, v)
    if "asr" in raw:
        for k, v in raw["asr"].items():
            if hasattr(config.asr, k):
                setattr(config.asr, k, v)
    if "ingestion_pipeline" in raw:
        for k, v in raw["ingestion_pipeline"].items():
            mapped = {"cleaner": "cleaner_provider", "splitter": "splitter_provider",
                       "storage": "storage_provider", "indexer": "indexer_provider"}
            attr = mapped.get(k, k)
            if hasattr(config.ingestion_pipeline, attr):
                setattr(config.ingestion_pipeline, attr, v)
    if "data" in raw:
        if "root" in raw["data"]:
            config.data.root = raw["data"]["root"]
            config.data.__post_init__()


def _apply_env_overrides(config: Config):
    config.llm.api_key = os.getenv("LLM_API_KEY", config.llm.api_key)
    config.llm.base_url = os.getenv("LLM_BASE_URL", config.llm.base_url)
    config.llm.model = os.getenv("LLM_MODEL", config.llm.model)
    config.llm.provider = os.getenv("LLM_PROVIDER", config.llm.provider)

    config.embedding.api_key = os.getenv("EMBEDDING_API_KEY", config.embedding.api_key)
    config.embedding.base_url = os.getenv("EMBEDDING_BASE_URL", config.embedding.base_url)
    config.embedding.model = os.getenv("EMBEDDING_MODEL", config.embedding.model)
    config.embedding.provider = os.getenv("EMBEDDING_PROVIDER", config.embedding.provider)

    config.asr.api_key = os.getenv("ASR_API_KEY", config.asr.api_key)
    config.asr.base_url = os.getenv("ASR_BASE_URL", config.asr.base_url)
    config.asr.model = os.getenv("ASR_MODEL", config.asr.model)
    config.asr.provider = os.getenv("ASR_PROVIDER", config.asr.provider)

    if os.getenv("DATA_ROOT"):
        config.data.root = os.getenv("DATA_ROOT")
        config.data.__post_init__()


# 全局单例
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config