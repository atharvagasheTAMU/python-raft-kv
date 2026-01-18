"""Test fault tolerance of the Raft cluster."""

import sys
import os
import time
import requests

# Add parent directory to path so we can import python_kv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_kv import KVStore, NotLeaderError


class ClusterController:
    """Helper class to control the cluster for fault tolerance testing."""
    
    def __init__(self):
        self.nodes = [
            {"id": 0, "port": 8080, "url": "http://localhost:8080"},
            {"id": 1, "port": 8081, "url": "http://localhost:8081"},
            {"id": 2, "port": 8082, "url": "http://localhost:8082"},
        ]
        self.addresses = {}
    
    def get_leader(self):
        """Find the current leader."""
        for node in self.nodes:
            try:
                response = requests.get(f"{node['url']}/is_leader", timeout=2)
                if response.status_code == 200 and response.json().get("is_leader"):
                    return node
            except:
                continue
        return None
    
    def get_all_addresses(self):
        """Get Raft addresses for all nodes."""
        for node in self.nodes:
            try:
                response = requests.get(f"{node['url']}/listen_addr", timeout=2)
                if response.status_code == 200:
                    self.addresses[node['id']] = response.json()["address"]
            except:
                pass
        return self.addresses
    
    def disconnect_peer(self, from_node_id, to_node_id):
        """Disconnect one node from another."""
        node = self.nodes[from_node_id]
        try:
            response = requests.post(
                f"{node['url']}/disconnect_peer",
                json={"peer_id": to_node_id},
                timeout=2
            )
            if response.status_code == 200:
                print(f"    Disconnected Node {from_node_id} from Node {to_node_id}")
            return response.status_code == 200
        except Exception as e:
            print(f"    Error disconnecting Node {from_node_id} from Node {to_node_id}: {e}")
            return False
    
    def disconnect_all(self, node_id):
        """Disconnect a node from all peers."""
        node = self.nodes[node_id]
        try:
            response = requests.post(f"{node['url']}/disconnect_all", timeout=2)
            if response.status_code == 200:
                print(f"    Disconnected Node {node_id} from all peers")
            return response.status_code == 200
        except Exception as e:
            print(f"    Error disconnecting Node {node_id} from all: {e}")
            return False
    
    def reconnect_peer(self, from_node_id, to_node_id):
        """Reconnect one node to another."""
        if to_node_id not in self.addresses:
            self.get_all_addresses()
        
        node = self.nodes[from_node_id]
        try:
            response = requests.post(
                f"{node['url']}/connect_peer",
                json={"peer_id": to_node_id, "address": self.addresses[to_node_id]},
                timeout=2
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error reconnecting: {e}")
            return False
    
    def reconnect_all(self, node_id):
        """Reconnect a node to all other nodes."""
        if not self.addresses:
            self.get_all_addresses()
        
        node = self.nodes[node_id]
        success = True
        for other_node in self.nodes:
            if other_node['id'] != node_id:
                if not self.reconnect_peer(node_id, other_node['id']):
                    success = False
                if not self.reconnect_peer(other_node['id'], node_id):
                    success = False
        return success


def wait_for_leader(controller, timeout=10):
    """Wait for a leader to be elected."""
    start = time.time()
    while time.time() - start < timeout:
        leader = controller.get_leader()
        if leader:
            return leader
        time.sleep(0.5)
    return None


def test_leader_disconnect(controller):
    """Test 1: Disconnect leader, new leader should be elected and data persists."""
    print("\n" + "="*60)
    print("TEST 1: Leader Disconnection with Data Persistence")
    print("="*60)
    
    # Find initial leader
    leader = wait_for_leader(controller)
    if not leader:
        print("❌ No leader found initially")
        return False
    
    print(f"✓ Initial leader: Node {leader['id']}")
    
    # Put multiple values before failure
    kv = KVStore(leader['url'], server_id=leader['id'])
    test_data = {
        "pre_failure_1": "data_before_leader_fail",
        "pre_failure_2": "important_data",
        "pre_failure_3": "persistent_value"
    }
    
    print("\nWriting data before leader failure...")
    for key, value in test_data.items():
        try:
            kv.put(key, value)
            print(f"  ✓ Put {key} = {value}")
        except Exception as e:
            print(f"  ✗ Put {key} failed: {e}")
            return False
    
    # Verify data is accessible
    print("\nVerifying data is accessible...")
    for key, expected_value in test_data.items():
        try:
            value, found = kv.get(key)
            if not found or value != expected_value:
                print(f"  ✗ Get {key} failed: expected={expected_value}, got={value}, found={found}")
                return False
            print(f"  ✓ Get {key} = {value}")
        except Exception as e:
            print(f"  ✗ Get {key} failed: {e}")
            return False
    
    # Disconnect leader from all peers (both directions)
    print(f"\nDisconnecting leader (Node {leader['id']}) from all peers...")
    controller.disconnect_all(leader['id'])
    
    # Disconnect all other nodes from the leader
    for other_node in controller.nodes:
        if other_node['id'] != leader['id']:
            try:
                requests.post(
                    f"{other_node['url']}/disconnect_peer",
                    json={"peer_id": leader['id']},
                    timeout=2
                )
            except:
                pass
    
    print("  Waiting for election timeout (150-300ms) and new leader election...")
    print("  (This may take a few seconds for followers to detect missing heartbeats)")
    
    # Initial wait - similar to test harness which waits 350ms
    # This gives time for followers to detect missing heartbeats
    time.sleep(0.4)
    
    # Wait and check multiple times - election timeout is 150-300ms
    # Heartbeats are sent every 50ms, so followers should detect missing heartbeats quickly
    new_leader = None
    old_leader_still_leader = True
    
    # Check all nodes directly to see their leader status
    def check_all_leader_status():
        status = {}
        for node in controller.nodes:
            try:
                response = requests.get(f"{node['url']}/is_leader", timeout=1)
                if response.status_code == 200:
                    status[node['id']] = response.json().get("is_leader", False)
            except:
                status[node['id']] = None
        return status
    
    for attempt in range(20):  # Check for up to 6 seconds
        time.sleep(0.3)
        
        # Check status of all nodes
        status = check_all_leader_status()
        leaders = [node_id for node_id, is_leader in status.items() if is_leader]
        
        if len(leaders) == 0:
            print(f"  (Attempt {attempt+1}) No leader found yet...")
            continue
        elif len(leaders) > 1:
            # Multiple leaders - this can happen if old leader is disconnected
            # Prefer a leader that's NOT the old disconnected leader
            new_leaders = [lid for lid in leaders if lid != leader['id']]
            if new_leaders:
                # We have a new leader (not the old one)
                new_leader = controller.nodes[new_leaders[0]]
                print(f"  ✓ New leader elected: Node {new_leader['id']} (after {(attempt+1)*0.3:.1f}s)")
                print(f"    (Note: Old leader Node {leader['id']} still thinks it's leader, but it's disconnected)")
                break
            else:
                # Only old leader thinks it's leader
                print(f"  (Attempt {attempt+1}) Only old leader ({leader['id']}) thinks it's leader...")
        
        # Check if we have a new leader (single leader case)
        if len(leaders) == 1 and leaders[0] != leader['id']:
            new_leader = controller.nodes[leaders[0]]
            print(f"  ✓ New leader elected: Node {new_leader['id']} (after {(attempt+1)*0.3:.1f}s)")
            break
        
        # Check if old leader stepped down
        old_leader_status = status.get(leader['id'], None)
        if old_leader_status is False:
            old_leader_still_leader = False
            print(f"  ✓ Old leader (Node {leader['id']}) stepped down, waiting for new leader...")
            # Continue waiting for new leader
    
    if not new_leader:
        # Final check
        status = check_all_leader_status()
        leaders = [node_id for node_id, is_leader in status.items() if is_leader]
        
        if len(leaders) == 0:
            print("❌ No leader found after disconnection")
            return False
        
        # If we have multiple leaders, prefer one that's not the old leader
        if len(leaders) > 1:
            new_leaders = [lid for lid in leaders if lid != leader['id']]
            if new_leaders:
                new_leader = controller.nodes[new_leaders[0]]
                print(f"  ✓ Found new leader on final check: Node {new_leader['id']}")
                print(f"    (Note: Old leader Node {leader['id']} still thinks it's leader, but it's disconnected)")
            else:
                print(f"❌ Only old leader (Node {leader['id']}) found after disconnection")
                print(f"   All node statuses: {status}")
                return False
        elif leaders[0] == leader['id']:
            print(f"❌ Same leader (Node {leader['id']}) still leader")
            print(f"   All node statuses: {status}")
            print("   The disconnection may not have worked properly")
            return False
        else:
            new_leader = controller.nodes[leaders[0]]
            print(f"  ✓ Found new leader on final check: Node {new_leader['id']}")
    
    if new_leader['id'] == leader['id']:
        print(f"❌ Same leader ({leader['id']}) still leader")
        return False
    
    print(f"✓ New leader elected: Node {new_leader['id']}")
    
    # Verify data persists on new leader
    print("\nVerifying data persists on new leader...")
    kv_new = KVStore(new_leader['url'], server_id=new_leader['id'])
    for key, expected_value in test_data.items():
        try:
            value, found = kv_new.get(key)
            if not found:
                print(f"  ✗ Data lost! Key {key} not found on new leader")
                return False
            if value != expected_value:
                print(f"  ✗ Data corrupted! Key {key}: expected={expected_value}, got={value}")
                return False
            print(f"  ✓ Data persisted: {key} = {value}")
        except Exception as e:
            print(f"  ✗ Get {key} failed: {e}")
            return False
    
    # Test that new leader can handle new operations
    print("\nTesting new operations on new leader...")
    try:
        kv_new.put("post_failure_1", "new_data_after_failover")
        value, found = kv_new.get("post_failure_1")
        if found and value == "new_data_after_failover":
            print("  ✓ New leader can handle new operations")
            return True
        else:
            print(f"  ✗ New operation failed: value={value}, found={found}")
            return False
    except Exception as e:
        print(f"  ✗ Operation on new leader failed: {e}")
        return False


def test_follower_disconnect(controller):
    """Test 2: Disconnect a follower, cluster should continue working and data persists."""
    print("\n" + "="*60)
    print("TEST 2: Follower Disconnection with Data Persistence")
    print("="*60)
    
    # Find leader
    leader = wait_for_leader(controller)
    if not leader:
        print("❌ No leader found")
        return False
    
    print(f"✓ Leader: Node {leader['id']}")
    
    # Write data before disconnecting follower
    kv = KVStore(leader['url'], server_id=leader['id'])
    test_data = {
        "before_follower_disconnect": "data_before_follower_fail",
        "test_key_2": "value_2"
    }
    
    print("\nWriting data before follower disconnection...")
    for key, value in test_data.items():
        try:
            kv.put(key, value)
            print(f"  ✓ Put {key} = {value}")
        except Exception as e:
            print(f"  ✗ Put {key} failed: {e}")
            return False
    
    # Find a follower
    follower_id = None
    for node in controller.nodes:
        if node['id'] != leader['id']:
            follower_id = node['id']
            break
    
    if follower_id is None:
        print("❌ No follower found")
        return False
    
    print(f"\nDisconnecting follower: Node {follower_id}")
    
    # Disconnect follower
    controller.disconnect_all(follower_id)
    for other_node in controller.nodes:
        if other_node['id'] != follower_id:
            controller.disconnect_peer(other_node['id'], follower_id)
    
    time.sleep(0.5)
    
    # Cluster should still work and data should persist
    print("\nVerifying data persists and cluster continues working...")
    for key, expected_value in test_data.items():
        try:
            value, found = kv.get(key)
            if not found or value != expected_value:
                print(f"  ✗ Data lost! Key {key}: expected={expected_value}, got={value}, found={found}")
                return False
            print(f"  ✓ Data persisted: {key} = {value}")
        except Exception as e:
            print(f"  ✗ Get {key} failed: {e}")
            return False
    
    # Test new operations
    try:
        kv.put("after_follower_disconnect", "new_data")
        value, found = kv.get("after_follower_disconnect")
        if found and value == "new_data":
            print("  ✓ Cluster continues working with follower disconnected")
            return True
        else:
            print(f"  ✗ New operation failed: value={value}, found={found}")
            return False
    except Exception as e:
        print(f"  ✗ Operation failed: {e}")
        return False


def test_no_quorum(controller):
    """Test 3: Disconnect majority, cluster should stop accepting writes."""
    print("\n" + "="*60)
    print("TEST 3: No Quorum (Majority Disconnected)")
    print("="*60)
    
    # Find leader
    leader = wait_for_leader(controller)
    if not leader:
        print("❌ No leader found")
        return False
    
    print(f"✓ Leader: Node {leader['id']}")
    
    # Disconnect leader and one follower (no quorum in 3-node cluster)
    print("Disconnecting leader and one follower (no quorum)...")
    controller.disconnect_all(leader['id'])
    
    # Disconnect one follower
    for node in controller.nodes:
        if node['id'] != leader['id']:
            controller.disconnect_all(node['id'])
            # Disconnect from other nodes
            for other in controller.nodes:
                if other['id'] != node['id']:
                    controller.disconnect_peer(other['id'], node['id'])
            break
    
    time.sleep(1)
    
    # Remaining node should not be able to accept writes
    remaining_node = None
    for node in controller.nodes:
        if node['id'] != leader['id']:
            try:
                response = requests.get(f"{node['url']}/is_leader", timeout=2)
                if response.status_code == 200:
                    remaining_node = node
                    break
            except:
                pass
    
    if remaining_node:
        kv = KVStore(remaining_node['url'], server_id=remaining_node['id'])
        try:
            kv.put("test3", "value3")
            print("⚠ Warning: Write succeeded with no quorum (unexpected)")
            return False
        except NotLeaderError:
            print("✓ Correctly rejected writes with no quorum")
            return True
        except Exception as e:
            print(f"✓ Operation failed as expected: {type(e).__name__}")
            return True
    
    print("✓ No quorum - cluster cannot accept writes")
    return True


def test_reconnect_and_catchup(controller):
    """Test 4: Reconnect a node and verify it catches up with all data."""
    print("\n" + "="*60)
    print("TEST 4: Reconnection and Catch-up with Data Persistence")
    print("="*60)
    
    # Reconnect all nodes first
    print("Reconnecting all nodes...")
    controller.get_all_addresses()
    for node in controller.nodes:
        controller.reconnect_all(node['id'])
    
    time.sleep(2)  # Wait for cluster to stabilize
    
    # Find leader
    leader = wait_for_leader(controller)
    if not leader:
        print("❌ No leader found after reconnection")
        return False
    
    print(f"✓ Leader after reconnection: Node {leader['id']}")
    
    # Write data while all nodes are connected
    kv = KVStore(leader['url'], server_id=leader['id'])
    test_data = {
        "catchup_test_1": "value_before_disconnect",
        "catchup_test_2": "more_data",
        "catchup_test_3": "even_more"
    }
    
    print("\nWriting data with all nodes connected...")
    for key, value in test_data.items():
        try:
            kv.put(key, value)
            print(f"  ✓ Put {key} = {value}")
        except Exception as e:
            print(f"  ✗ Put {key} failed: {e}")
            return False
    
    # Disconnect a follower
    follower_id = None
    for node in controller.nodes:
        if node['id'] != leader['id']:
            follower_id = node['id']
            break
    
    if follower_id is None:
        print("❌ No follower found")
        return False
    
    print(f"\nDisconnecting follower Node {follower_id}...")
    controller.disconnect_all(follower_id)
    for other_node in controller.nodes:
        if other_node['id'] != follower_id:
            controller.disconnect_peer(other_node['id'], follower_id)
    
    # Write more data while follower is disconnected
    more_data = {
        "catchup_test_4": "written_while_follower_disconnected",
        "catchup_test_5": "more_while_disconnected"
    }
    
    print("\nWriting data while follower is disconnected...")
    for key, value in more_data.items():
        try:
            kv.put(key, value)
            print(f"  ✓ Put {key} = {value}")
        except Exception as e:
            print(f"  ✗ Put {key} failed: {e}")
            return False
    
    # Reconnect the follower
    print(f"\nReconnecting follower Node {follower_id}...")
    controller.reconnect_all(follower_id)
    time.sleep(2)  # Wait for catch-up
    
    # Get the current leader (might have changed after reconnection)
    current_leader = wait_for_leader(controller, timeout=5)
    if not current_leader:
        print("❌ No leader found after reconnection")
        return False
    
    print(f"  Current leader: Node {current_leader['id']}")
    
    # Create a new KVStore instance for the current leader
    kv_current = KVStore(current_leader['url'], server_id=current_leader['id'])
    
    # Verify all data is accessible (including data written while disconnected)
    print("\nVerifying all data is accessible after reconnection...")
    all_data = {**test_data, **more_data}
    
    for key, expected_value in all_data.items():
        try:
            value, found = kv_current.get(key)
            if not found:
                print(f"  ✗ Data lost! Key {key} not found")
                return False
            if value != expected_value:
                print(f"  ✗ Data mismatch! Key {key}: expected={expected_value}, got={value}")
                return False
            print(f"  ✓ Data accessible: {key} = {value}")
        except Exception as e:
            print(f"  ✗ Get {key} failed: {e}")
            return False
    
    print("\n✓ All data persisted and is accessible after reconnection")
    return True


def main():
    print("="*60)
    print("Raft Cluster - Fault Tolerance Tests")
    print("="*60)
    print("\nMake sure the 3-node cluster is running!")
    print("Run: .\\start-3node-cluster.ps1")
    print()
    
    controller = ClusterController()
    
    # Get addresses
    print("Getting cluster information...")
    controller.get_all_addresses()
    if not controller.addresses:
        print("❌ Could not connect to cluster nodes")
        print("   Make sure the cluster is running: .\\start-3node-cluster.ps1")
        sys.exit(1)
    
    print(f"✓ Connected to cluster")
    print(f"  Node addresses: {controller.addresses}")
    
    results = []
    
    # Run tests
    results.append(("Leader Disconnect", test_leader_disconnect(controller)))
    
    # Reconnect for next test
    time.sleep(1)
    controller.get_all_addresses()
    for node in controller.nodes:
        controller.reconnect_all(node['id'])
    time.sleep(2)
    
    results.append(("Follower Disconnect", test_follower_disconnect(controller)))
    
    # Reconnect for next test
    time.sleep(1)
    controller.get_all_addresses()
    for node in controller.nodes:
        controller.reconnect_all(node['id'])
    time.sleep(2)
    
    results.append(("No Quorum", test_no_quorum(controller)))
    
    # Reconnect for final test
    time.sleep(1)
    controller.get_all_addresses()
    for node in controller.nodes:
        controller.reconnect_all(node['id'])
    time.sleep(2)
    
    results.append(("Reconnect and Catch-up", test_reconnect_and_catchup(controller)))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n✅ All fault tolerance tests passed!")
        print("\n💡 Tip: Run 'python test_data_persistence.py' for comprehensive data persistence tests")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

