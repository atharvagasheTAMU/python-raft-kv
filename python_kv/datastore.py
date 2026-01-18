"""In-memory data store for key-value operations."""

from typing import Optional, Tuple


class DataStore:
    """Simple in-memory key-value data store."""
    
    def __init__(self):
        self._store: dict[str, str] = {}
    
    def get(self, key: str) -> Tuple[Optional[str], bool]:
        """
        Get a value by key.
        
        Returns:
            Tuple of (value, found) where found is True if key exists.
        """
        value = self._store.get(key)
        found = key in self._store
        return value, found
    
    def put(self, key: str, value: str) -> Tuple[Optional[str], bool]:
        """
        Put a key-value pair.
        
        Returns:
            Tuple of (previous_value, was_found) where was_found indicates
            if the key existed before.
        """
        prev_value = self._store.get(key)
        was_found = key in self._store
        self._store[key] = value
        return prev_value, was_found
    
    def cas(self, key: str, compare_value: str, new_value: str) -> Tuple[Optional[str], bool]:
        """
        Compare-and-swap operation.
        
        If store[key] == compare_value, sets store[key] = new_value.
        Otherwise, does nothing.
        
        Returns:
            Tuple of (old_value, was_found) where was_found indicates
            if the key existed before the operation.
        """
        old_value = self._store.get(key)
        was_found = key in self._store
        
        if was_found and old_value == compare_value:
            self._store[key] = new_value
        
        return old_value, was_found


