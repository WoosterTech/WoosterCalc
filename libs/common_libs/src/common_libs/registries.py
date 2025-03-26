from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A generic registry class that allows storing and retrieving objects by name.

    Supports type-safe registration and retrieval of objects.

    Example usage:
    >>> int_registry = Registry[int]()
    >>> int_registry.register('answer', 42)

    >>> str_registry = Registry[str]()
    >>> str_registry.register('greeting', 'Hello, World!')
    """

    _items: dict[str, T]

    def __init__(self):
        """Initialize an empty registry."""
        self._items = {}

    def register(self, name: str, item: T) -> None:
        """Register an item in the registry with a given name.

        Args:
            name: A unique identifier for the item
            item: The item to be stored in the registry

        Raises:
            KeyError: If an item with the same name already exists
        """
        if name in self._items:
            msg = f"An item with the name '{name}' already exists in the registry."
            raise KeyError(msg)

        self._items[name] = item

    def get(self, name: str) -> T:
        """Retrieve an item from the registry by its name.

        Args:
            name: The name of the item to retrieve

        Returns:
            The item associated with the given name

        Raises:
            KeyError: If no item with the given name exists in the registry
        """
        return self._items[name]

    def pop(self, name: str) -> T:
        """Remove and return an item from the registry.

        Args:
            name: The name of the item to remove

        Returns:
            The removed item

        Raises:
            KeyError: If no item with the given name exists in the registry
        """
        return self._items.pop(name)

    def unregister(self, name: str) -> T:
        """Remove and return an item from the registry.

        Args:
            name: The name of the item to remove

        Returns:
            The removed item

        Raises:
            KeyError: If no item with the given name exists in the registry
        """
        return self._items.pop(name)

    def __contains__(self, name: str) -> bool:
        """Check if an item with the given name exists in the registry.

        Returns:
            bool: True if the name exists, False otherwise
        """
        return name in self._items

    def __len__(self) -> int:
        """Return the number of items in the registry.

        Returns:
            int: The number of items in the registry
        """
        return len(self._items)
