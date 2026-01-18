"""Test script for 3-node cluster."""

import sys
import os
import time
import requests

# Add parent directory to path so we can import python_kv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_kv import KVStore, NotLeaderError

def find_leader():
    """Find which node is the leader."""
    for port, server_id in [(8080, 0), (8081, 1), (8082, 2)]:
        try:
            response = requests.get(f"http://localhost:{port}/is_leader", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("is_leader"):
                    return port, server_id
        except:
            continue
    return None, None

def main():
    print("=" * 60)
    print("Python Raft KV Store - 3-Node Cluster Test")
    print("=" * 60)
    print()
    
    # Find the leader
    print("Finding leader node...")
    leader_port, leader_id = find_leader()
    
    if leader_port is None:
        print("❌ No leader found. Make sure the cluster is running.")
        print("   Run: .\\start-3node-cluster.ps1")
        sys.exit(1)
    
    print(f"✓ Found leader: Node {leader_id} on port {leader_port}")
    print()
    
    # Create KV store connected to the leader
    kv = KVStore(f"http://localhost:{leader_port}", server_id=leader_id)
    
    print("Testing KV operations...")
    print()
    
    try:
        # Test PUT
        print("1. Testing PUT operation...")
        prev_value, was_found = kv.put("test_key", "test_value_1")
        print(f"   ✓ PUT successful")
        print(f"     Previous value: {prev_value}, Was found: {was_found}")
        print()
        
        # Test GET
        print("2. Testing GET operation...")
        value, found = kv.get("test_key")
        if found and value == "test_value_1":
            print(f"   ✓ GET successful")
            print(f"     Value: {value}, Found: {found}")
        else:
            print(f"   ✗ GET failed")
            print(f"     Value: {value}, Found: {found}")
            sys.exit(1)
        print()
        
        # Test PUT (update)
        print("3. Testing PUT (update) operation...")
        prev_value, was_found = kv.put("test_key", "test_value_2")
        print(f"   ✓ PUT successful")
        print(f"     Previous value: {prev_value}, Was found: {was_found}")
        print()
        
        # Verify update
        print("4. Verifying update...")
        value, found = kv.get("test_key")
        if value == "test_value_2":
            print(f"   ✓ Update verified")
            print(f"     Value: {value}")
        else:
            print(f"   ✗ Update verification failed")
            print(f"     Expected: test_value_2, Got: {value}")
            sys.exit(1)
        print()
        
        # Test CAS
        print("5. Testing CAS operation...")
        old_value, was_found = kv.cas("test_key", "test_value_2", "test_value_3")
        print(f"   ✓ CAS successful")
        print(f"     Old value: {old_value}, Was found: {was_found}")
        print()
        
        # Verify CAS
        print("6. Verifying CAS result...")
        value, found = kv.get("test_key")
        if value == "test_value_3":
            print(f"   ✓ CAS verified")
            print(f"     Value: {value}")
        else:
            print(f"   ✗ CAS verification failed")
            print(f"     Expected: test_value_3, Got: {value}")
            sys.exit(1)
        print()
        
        # Test multiple keys
        print("7. Testing multiple keys...")
        kv.put("key1", "value1")
        kv.put("key2", "value2")
        kv.put("key3", "value3")
        
        v1, f1 = kv.get("key1")
        v2, f2 = kv.get("key2")
        v3, f3 = kv.get("key3")
        
        if f1 and f2 and f3 and v1 == "value1" and v2 == "value2" and v3 == "value3":
            print(f"   ✓ Multiple keys test successful")
        else:
            print(f"   ✗ Multiple keys test failed")
            sys.exit(1)
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print(f"The cluster is working correctly with Node {leader_id} as leader.")
        print(f"You can use: KVStore('http://localhost:{leader_port}', server_id={leader_id})")
        
    except NotLeaderError as e:
        print(f"❌ Not leader error: {e}")
        print("   The leader may have changed. Try running the test again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


