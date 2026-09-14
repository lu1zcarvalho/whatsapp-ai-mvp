import asyncio


class InMemoryMessageStore:
    """Deduplicação local. Em produção, substituir por Redis ou banco de dados."""

    def __init__(self) -> None:
        self._processed_ids: set[str] = set()
        self._lock = asyncio.Lock()

    async def mark_if_new(self, message_id: str) -> bool:
        async with self._lock:
            if message_id in self._processed_ids:
                return False
            self._processed_ids.add(message_id)
            return True


message_store = InMemoryMessageStore()
