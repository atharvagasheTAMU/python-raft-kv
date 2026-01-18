"""Key-value store using Raft consensus via HTTP bridge."""

import json
import time
from typing import Optional, Tuple
import requests

from .datastore import DataStore


class KVStore:
    """Distributed key-value store using Raft consensus."""
    
    def __init__(self, raft_bridge_url: str, server_id: int, timeout_ms: int = 30000):
        """
        Initialize the KV store.
        
        Args:
            raft_bridge_url: Base URL of the Raft bridge service (e.g., "http://localhost:8080")
            server_id: ID of this server in the Raft cluster
            timeout_ms: Timeout for waiting for commits in milliseconds
        """
        self.bridge_url = raft_bridge_url.rstrip('/')
        self.server_id = server_id
        self.timeout_ms = timeout_ms
        self.datastore = DataStore()
        self.last_applied_index = -1  # Track the last commit index we've applied
    
    def _submit_command(self, kind: str, key: str, value: str = "", compare_value: str = "") -> int:
        """Submit a command to Raft and return log index."""
        url = f"{self.bridge_url}/submit"
        payload = {
            "kind": kind,
            "key": key,
            "value": value,
            "compare_value": compare_value,
            "id": self.server_id
        }
        
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("is_leader"):
            raise NotLeaderError("This server is not the Raft leader")
        
        return data["log_index"]
    
    def _wait_for_commit(self, log_index: int) -> dict:
        """Wait for a command to be committed at the given log index."""
        url = f"{self.bridge_url}/wait_commit"
        payload = {
            "log_index": log_index,
            "timeout_ms": self.timeout_ms
        }
        
        # Add extra buffer to timeout to account for network delays
        timeout_seconds = (self.timeout_ms / 1000) + 10
        try:
            response = requests.post(url, json=payload, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            # If timeout, check if we're still the leader
            try:
                if not self.is_leader():
                    raise NotLeaderError("Lost leadership while waiting for commit")
            except:
                pass
            raise
    
    def _apply_command(self, command: dict) -> Tuple[Optional[str], bool]:
        """Apply a committed command to the local data store."""
        kind = command["kind"]
        key = command["key"]
        
        if kind == "get":
            return self.datastore.get(key)
        elif kind == "put":
            value = command.get("value", "")
            return self.datastore.put(key, value)
        elif kind == "cas":
            compare_value = command.get("compare_value", "")
            new_value = command.get("value", "")
            return self.datastore.cas(key, compare_value, new_value)
        else:
            raise ValueError(f"Unknown command kind: {kind}")
    
    def _sync_commits(self):
        """Sync all commits since last_applied_index to ensure consistency."""
        try:
            url = f"{self.bridge_url}/get_commits_since"
            params = {"since_index": self.last_applied_index}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            commits = data.get("commits", [])
            # Sort commits by index to ensure we apply them in order
            commits.sort(key=lambda c: c["index"])
            
            for commit in commits:
                # Apply the command
                self._apply_command(commit["command"])
                # Update last applied index
                self.last_applied_index = max(self.last_applied_index, commit["index"])
        except requests.exceptions.HTTPError as e:
            # If 404, it means no commits found (which is OK if last_applied_index is up to date)
            if e.response.status_code == 404:
                pass
            else:
                # Other HTTP errors - log but continue
                pass
        except Exception as e:
            # If sync fails, continue - we'll try again on next operation
            pass
    
    def get(self, key: str) -> Tuple[Optional[str], bool]:
        """
        Get a value by key.
        
        Returns:
            Tuple of (value, found) where found is True if key exists.
            
        Raises:
            NotLeaderError: If this server is not the leader
            requests.RequestException: On network errors
        """
        # Sync any missing commits first
        self._sync_commits()
        
        log_index = self._submit_command("get", key)
        commit_data = self._wait_for_commit(log_index)
        
        # Update last applied index
        self.last_applied_index = max(self.last_applied_index, commit_data["index"])
        
        # Apply to local store
        value, found = self._apply_command(commit_data["command"])
        return value, found
    
    def put(self, key: str, value: str) -> Tuple[Optional[str], bool]:
        """
        Put a key-value pair.
        
        Returns:
            Tuple of (previous_value, was_found) where was_found indicates
            if the key existed before.
            
        Raises:
            NotLeaderError: If this server is not the leader
            requests.RequestException: On network errors
        """
        # Sync any missing commits first
        self._sync_commits()
        
        log_index = self._submit_command("put", key, value)
        commit_data = self._wait_for_commit(log_index)
        
        # Update last applied index
        self.last_applied_index = max(self.last_applied_index, commit_data["index"])
        
        # Apply to local store
        prev_value, was_found = self._apply_command(commit_data["command"])
        return prev_value, was_found
    
    def cas(self, key: str, compare_value: str, new_value: str) -> Tuple[Optional[str], bool]:
        """
        Compare-and-swap operation.
        
        If store[key] == compare_value, sets store[key] = new_value.
        Otherwise, does nothing.
        
        Returns:
            Tuple of (old_value, was_found) where was_found indicates
            if the key existed before the operation.
            
        Raises:
            NotLeaderError: If this server is not the leader
            requests.RequestException: On network errors
        """
        log_index = self._submit_command("cas", key, new_value, compare_value)
        commit_data = self._wait_for_commit(log_index)
        
        # Verify this is our command
        if commit_data["command"]["id"] != self.server_id:
            raise CommitFailedError("Command was committed but not ours (lost leadership)")
        
        # Apply to local store
        old_value, was_found = self._apply_command(commit_data["command"])
        return old_value, was_found
    
    def is_leader(self) -> bool:
        """Check if this server is the Raft leader."""
        url = f"{self.bridge_url}/is_leader"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()["is_leader"]


class NotLeaderError(Exception):
    """Raised when an operation is attempted on a non-leader server."""
    pass


class CommitFailedError(Exception):
    """Raised when a commit fails (e.g., lost leadership during commit)."""
    pass


