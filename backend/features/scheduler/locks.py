import uuid
from django.core.cache import cache


class RedisLock:
    def __init__(self, key: str, timeout: int = 55):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.token = None

    def acquire(self) -> bool:
        self.token = uuid.uuid4().hex
        return cache.add(self.key, self.token, self.timeout)

    def release(self):
        if self.token is None:
            return
        current = cache.get(self.key)
        if current == self.token:
            cache.delete(self.key)
        self.token = None
