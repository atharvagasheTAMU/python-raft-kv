"""Client for interacting with the KV store over HTTP."""

import requests
from typing import Optional, Tuple


class KVClient:
    """Client for making requests to a KV store server."""
    
    def __init__(self, server_url: str):
        """
        Initialize the client.
        
        Args:
            server_url: Base URL of the KV store server (e.g., "http://localhost:9000")
        """
        self.server_url = server_url.rstrip('/')
    
    def get(self, key: str) -> Tuple[Optional[str], bool]:
        """Get a value by key."""
        url = f"{self.server_url}/get"
        response = requests.post(url, json={"key": key})
        response.raise_for_status()
        data = response.json()
        
        if data["resp_status"] != 0:  # StatusOK = 0
            raise Exception(f"Get failed with status: {data['resp_status']}")
        
        return data.get("value"), data.get("key_found", False)
    
    def put(self, key: str, value: str) -> Tuple[Optional[str], bool]:
        """Put a key-value pair."""
        url = f"{self.server_url}/put"
        response = requests.post(url, json={"key": key, "value": value})
        response.raise_for_status()
        data = response.json()
        
        if data["resp_status"] != 0:  # StatusOK = 0
            raise Exception(f"Put failed with status: {data['resp_status']}")
        
        return data.get("prev_value"), data.get("key_found", False)
    
    def cas(self, key: str, compare_value: str, new_value: str) -> Tuple[Optional[str], bool]:
        """Compare-and-swap operation."""
        url = f"{self.server_url}/cas"
        response = requests.post(url, json={
            "key": key,
            "compare_value": compare_value,
            "value": new_value
        })
        response.raise_for_status()
        data = response.json()
        
        if data["resp_status"] != 0:  # StatusOK = 0
            raise Exception(f"CAS failed with status: {data['resp_status']}")
        
        return data.get("prev_value"), data.get("key_found", False)


