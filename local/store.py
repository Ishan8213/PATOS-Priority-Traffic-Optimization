"""In-memory stand-ins for the two DynamoDB tables, used only by the local server."""
import threading


class MemoryTable:
    def __init__(self, key: str, max_items: int | None = None):
        self._key, self._max = key, max_items
        self._items: dict = {}
        self._lock = threading.Lock()

    def put_item(self, Item):
        with self._lock:
            self._items.pop(Item[self._key], None)
            self._items[Item[self._key]] = Item
            while self._max and len(self._items) > self._max:
                self._items.pop(next(iter(self._items)))

    def scan(self, **_):
        with self._lock:
            return {"Items": list(self._items.values())}

    def recent(self, n: int) -> list:
        with self._lock:
            return list(self._items.values())[-n:][::-1]


class MirroredTable(MemoryTable):
    """MemoryTable that also hands every stored item to a callback (used for best-effort AWS sync).
    A failing callback never affects the local app."""

    def __init__(self, key: str, max_items: int | None = None, on_put=None):
        super().__init__(key, max_items)
        self._on_put = on_put

    def put_item(self, Item):
        super().put_item(Item)
        if self._on_put:
            try:
                self._on_put(Item)
            except Exception:
                pass
