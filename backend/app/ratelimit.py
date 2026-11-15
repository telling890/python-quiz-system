# -*- coding: utf-8 -*-
"""限流：进程内滑动窗口，够单机用；多实例部署时换成 Redis 实现即可。"""

import threading
import time
from collections import deque

from .config import get_settings

_buckets = {}
_guard = threading.Lock()


class SlidingWindow:
    def __init__(self, limit, window=60.0):
        self.limit = limit
        self.window = window
        self.hits = deque()
        self.lock = threading.Lock()

    def allow(self, cost=1):
        now = time.monotonic()
        cutoff = now - self.window
        with self.lock:
            while self.hits and self.hits[0] < cutoff:
                self.hits.popleft()
            if len(self.hits) + cost > self.limit:
                return False
            self.hits.extend([now] * cost)
            return True


def _bucket(name, limit):
    with _guard:
        bucket = _buckets.get(name)
        if bucket is None or bucket.limit != limit:
            bucket = SlidingWindow(limit)
            _buckets[name] = bucket
        return bucket


def check(name, key):
    """返回 (是否允许, 建议的 Retry-After 秒数)。"""
    settings = get_settings()
    limit = settings.rate_limit_auth_per_minute if name == "auth" else settings.rate_limit_per_minute
    bucket = _bucket(name, limit)
    if bucket.allow():
        return True, 0
    return False, 60


def reset():
    """测试用：清空所有计数。"""
    with _guard:
        _buckets.clear()
