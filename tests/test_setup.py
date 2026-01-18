"""Test script to verify the setup is working."""

import sys
import os
import requests
import time

# Add parent directory to path so we can import python_kv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_bridge_connection(bridge_url="http://localhost:8080"):
    """Test if the bridge is running and responding."""
    print("Testing bridge connection...")
    
    try:
        # Test is_leader endpoint
        response = requests.get(f"{bridge_url}/is_leader", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Bridge is running!")
            print(f"  Is leader: {data.get('is_leader', False)}")
            return True
        else:
            print(f"✗ Bridge returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to bridge. Is it running?")
        print(f"  Expected URL: {bridge_url}")
        print("\n  To start the bridge, run in a separate terminal:")
        print("  cd python-raft-kv/raft-bridge")
        print("  .\\raft-bridge.exe 0 8080")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_kv_operations(bridge_url="http://localhost:8080"):
    """Test basic KV operations."""
    print("\nTesting KV operations...")
    
    try:
        # python_kv is already in path from the sys.path.insert above
        from python_kv import KVStore, NotLeaderError
        
        kv = KVStore(bridge_url, server_id=0)
        
        # Check if leader
        if not kv.is_leader():
            print("⚠ Warning: Not the leader. Some operations may fail.")
            print("  (This is normal for a single-node cluster - it should become leader)")
            return False
        
        # Test PUT
        print("  Testing PUT...")
        prev_value, was_found = kv.put("test_key", "test_value")
        print(f"    ✓ PUT successful (prev: {prev_value}, found: {was_found})")
        
        # Test GET
        print("  Testing GET...")
        value, found = kv.get("test_key")
        if found and value == "test_value":
            print(f"    ✓ GET successful (value: {value})")
        else:
            print(f"    ✗ GET failed (value: {value}, found: {found})")
            return False
        
        # Test CAS
        print("  Testing CAS...")
        old_value, was_found = kv.cas("test_key", "test_value", "new_value")
        if was_found:
            print(f"    ✓ CAS successful (old: {old_value})")
        else:
            print(f"    ✗ CAS failed")
            return False
        
        # Verify CAS worked
        value, found = kv.get("test_key")
        if value == "new_value":
            print(f"    ✓ CAS verification successful")
        else:
            print(f"    ✗ CAS verification failed (got: {value})")
            return False
        
        print("\n✓ All tests passed!")
        return True
        
    except NotLeaderError as e:
        print(f"✗ Not leader error: {e}")
        print("  Wait a moment for leader election, then try again.")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Python Raft KV Store - Setup Test")
    print("=" * 50)
    print()
    
    # Test bridge connection
    if not test_bridge_connection():
        print("\n❌ Setup incomplete. Please start the bridge first.")
        sys.exit(1)
    
    # Test KV operations
    if test_kv_operations():
        print("\n✅ All tests passed! Your setup is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)


