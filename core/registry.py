"""Generic instance-based registry for flyweight templates.

Registries map string IDs to immutable template objects loaded from JSON.
Each content domain subclasses Registry and exposes a module-level default
instance; injectable for tests that need isolated content.
"""

from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Maps string IDs to template flyweights."""

    def __init__(self):
        self._items: dict[str, T] = {}

    def register(self, item: T) -> None:
        """Add a template; its ``id`` attribute is the key."""
        self._items[item.id] = item

    def get(self, item_id: str) -> Optional[T]:
        """Retrieve a template by ID. Returns None if not found."""
        return self._items.get(item_id)

    def clear(self) -> None:
        """Remove all registered templates."""
        self._items.clear()

    def all_ids(self) -> list[str]:
        """Return all registered IDs."""
        return list(self._items.keys())

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item_id: str) -> bool:
        return item_id in self._items
