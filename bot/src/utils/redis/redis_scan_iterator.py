from redis.asyncio import Redis


# TODO: annotate iterator.
class RedisScanIterAsyncIterator:
    """
    E.g.
    ```python
    redis = Redis(host="redis", port=6379, db=0, decode_responses=True)
    bot_chat_messages_cache_keys_iterator = RedisScanIterAsyncIterator(redis, "redisKeysGeneralPart*", 10)
    async for redis_keys in bot_chat_messages_cache_keys_iterator:
        print(f'{redis_keys = }\n\n')
    ```
    """

    def __init__(self, redis: Redis, match: str):
        """:param count: deprecated."""
        self.redis = redis
        self.match = match
        self._cursor = None

    def __aiter__(self):
        return self

    async def __anext__(self) -> list[str]:
        # Only when cursor == 0 means that we have iterated over all keys.
        if self._cursor == 0:
            raise StopAsyncIteration

        self._cursor = 0 if self._cursor is None else self._cursor
        new_cursor, keys = await self.redis.scan(match=self.match, cursor=self._cursor)
        self._cursor = new_cursor
        if keys == []:
            return await self.__anext__()
        return keys


async def get_first_n_keys(
        match_pattern: str,
        first_n: int,
        redis_engine: Redis,
) -> list[str]:
    """It loads first n keys from redis that matches match_pattern (it may use several queries to Redis).
    It may load less obviously. If it loads more it slice for the exact number.
    """
    chat_keys_loaded = []
    keys_iterator = RedisScanIterAsyncIterator(redis=redis_engine, match=match_pattern)
    async for chat_keys in keys_iterator:
        chat_keys_loaded += chat_keys
        if len(chat_keys_loaded) >= first_n:
            return chat_keys_loaded[:first_n]
    return chat_keys_loaded
