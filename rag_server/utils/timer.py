"""操作计时工具。

提供 @timeit 装饰器和 Timer 上下文管理器，
用于记录关键路径的操作耗时，输出 [timing] 日志。
"""

import functools
import inspect
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def timeit(fn):
    """函数计时装饰器，同时支持同步和异步函数。

    用法:
        @timeit
        async def search(self, query): ...

        @timeit
        def clean(self, text): ...
    """
    qualname = f"{fn.__module__}.{fn.__qualname__}"

    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(f"[timing] {qualname}: {elapsed_ms:.1f}ms")
        return async_wrapper
    else:
        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(f"[timing] {qualname}: {elapsed_ms:.1f}ms")
        return sync_wrapper


class Timer:
    """异步代码块计时上下文管理器。

    用法:
        async with Timer("chroma.search") as t:
            result = await chroma.search(query)

        # 获取耗时
        print(t.elapsed_ms)
    """

    def __init__(self, name: str):
        self.name = name
        self.start: float = 0.0
        self._elapsed_ms: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed_ms

    async def __aenter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    async def __aexit__(self, *exc) -> Optional[bool]:
        self._elapsed_ms = (time.perf_counter() - self.start) * 1000
        logger.info(f"[timing] {self.name}: {self._elapsed_ms:.1f}ms")
        return None