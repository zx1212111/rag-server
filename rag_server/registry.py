"""Registry 注册表 + 工厂方法。

用法：
    @register("llm", "openai")
    class OpenAICompatibleLLM(LLM):
        ...

    # 创建实例
    llm = Factory.create("llm", "openai", api_key="...")
"""

from typing import Any, Callable, Dict, List, Optional, Type


_registry: Dict[str, Dict[str, type]] = {}


def register(group: str, name: str) -> Callable[[type], type]:
    """装饰器：将实现类注册到指定分组和名称下。"""
    def decorator(cls: type) -> type:
        if group not in _registry:
            _registry[group] = {}
        _registry[group][name] = cls
        return cls
    return decorator


def get_supported_extensions() -> List[str]:
    """收集所有已注册 Loader 声明的文件扩展名。"""
    exts: List[str] = []
    for name, cls in _registry.get("loader", {}).items():
        exts.extend(getattr(cls, "extensions", []))
    return sorted(set(exts))


def auto_register(package_name: str) -> None:
    """自动导入指定包下的所有模块，触发 @register 装饰器。

    跳过 __init__ 和 base（抽象接口），只导入具体实现模块。
    """
    import importlib
    import pkgutil

    pkg = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
        if module_name not in ("__init__", "base"):
            importlib.import_module(f"{package_name}.{module_name}")


class Factory:
    """工厂方法：根据分组和名称创建实例。"""

    @staticmethod
    def create(group: str, name: str, **kwargs: Any) -> Any:
        if group not in _registry:
            raise ValueError(f"未注册的分组: {group}，可用: {list(_registry.keys())}")
        if name not in _registry[group]:
            raise ValueError(f"未注册的名称: {name}，可用: {list(_registry[group].keys())}")
        cls = _registry[group][name]
        return cls(**kwargs)

    @staticmethod
    def list(group: Optional[str] = None):
        """列出已注册的组件。

        参数:
            group: 分组名，为 None 时返回全部分组
        """
        if group:
            return {group: list(_registry.get(group, {}).keys())}
        return {g: list(names.keys()) for g, names in _registry.items()}

    @staticmethod
    def has(group: str, name: str) -> bool:
        return group in _registry and name in _registry[group]