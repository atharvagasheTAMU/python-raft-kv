#!/usr/bin/env python3
"""
Simple startup script for the Raft KV store cluster.
One command to start everything!
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def check_go_bridge_exists():
    """Check if the Go bridge executable exists."""
    if sys.platform == "win32":
        bridge_path = Path("raft-bridge/raft-bridge.exe")
    else:
        bridge_path = Path("raft-bridge/raft-bridge")
    return bridge_path.exists()

def build_go_bridge():
    """Build the Go bridge executable."""
    print("Building Go bridge...")
    os.chdir("raft-bridge")
    
    if sys.platform == "win32":
        cmd = ["go", "build", "-o", "raft-bridge.exe", "main.go", "command.go"]
    else:
        cmd = ["go", "build", "-o", "raft-bridge", "main.go", "command.go"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.chdir("..")
    
    if result.returncode != 0:
        print(f"Error building bridge: {result.stderr}")
        return False
    
    print("✓ Go bridge built successfully")
    return True

def kill_existing_processes():
    """Kill any existing bridge processes."""
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "raft-bridge.exe"], 
                         capture_output=True, stderr=subprocess.DEVNULL)
        except:
            pass
    else:
        try:
            subprocess.run(["pkill", "-f", "raft-bridge"], 
                         capture_output=True, stderr=subprocess.DEVNULL)
        except:
            pass

def start_node(node_id, port, peer_ids, bridge_path):
    """Start a single bridge node."""
    peer_str = ",".join(map(str, peer_ids))
    
    if sys.platform == "win32":
        # Windows: start in new window
        cmd = ["start", "cmd", "/k", f"title Node {node_id} && {bridge_path}", 
               str(node_id), str(port), peer_str]
        subprocess.Popen(cmd, shell=True, cwd=os.getcwd())
    else:
        # Linux/Mac: start in background
        cmd = [bridge_path, str(node_id), str(port), peer_str]
        subprocess.Popen(cmd, cwd=os.getcwd(), 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    
    time.sleep(1)

def get_listen_addr(port):
    """Get the Raft listen address for a node."""
    for _ in range(10):
        try:
            response = requests.get(f"http://localhost:{port}/listen_addr", timeout=1)
            if response.status_code == 200:
                return response.json()["address"]
        except:
            time.sleep(0.5)
    return None

def connect_peers():
    """Connect all peers together."""
    print("Connecting nodes...")
    
    # Get addresses
    addrs = {}
    for node_id, port in [(0, 8080), (1, 8081), (2, 8082)]:
        addr = get_listen_addr(port)
        if addr:
            addrs[node_id] = addr
            print(f"  Node {node_id}: {addr}")
        else:
            print(f"  ⚠ Could not get address for node {node_id}")
    
    # Connect all pairs
    for node_id, port in [(0, 8080), (1, 8081), (2, 8082)]:
        for peer_id, peer_port in [(0, 8080), (1, 8081), (2, 8082)]:
            if node_id != peer_id and node_id in addrs and peer_id in addrs:
                try:
                    requests.post(
                        f"http://localhost:{port}/connect_peer",
                        json={"peer_id": peer_id, "address": addrs[peer_id]},
                        timeout=2
                    )
                except:
                    pass
    
    # Signal ready
    for port in [8080, 8081, 8082]:
        try:
            requests.post(f"http://localhost:{port}/ready", timeout=1)
        except:
            pass

def find_leader():
    """Find which node is the leader."""
    for port, node_id in [(8080, 0), (8081, 1), (8082, 2)]:
        try:
            response = requests.get(f"http://localhost:{port}/is_leader", timeout=1)
            if response.status_code == 200 and response.json().get("is_leader"):
                return port, node_id
        except:
            continue
    return None, None

def main():
    print("=" * 60)
    print("Raft KV Store - Simple Startup")
    print("=" * 60)
    print()
    
    # Check if bridge exists, build if needed
    if not check_go_bridge_exists():
        print("Go bridge not found. Building...")
        if not build_go_bridge():
            print("Failed to build Go bridge. Make sure Go is installed.")
            sys.exit(1)
    else:
        print("✓ Go bridge found")
    
    # Kill existing processes
    print("Cleaning up existing processes...")
    kill_existing_processes()
    time.sleep(1)
    
    # Get bridge path
    if sys.platform == "win32":
        bridge_path = Path("raft-bridge/raft-bridge.exe").absolute()
    else:
        bridge_path = Path("raft-bridge/raft-bridge").absolute()
    
    print()
    print("Starting 3-node cluster...")
    
    # Start all nodes
    start_node(0, 8080, [1, 2], str(bridge_path))
    start_node(1, 8081, [0, 2], str(bridge_path))
    start_node(2, 8082, [0, 1], str(bridge_path))
    
    print("✓ All nodes started")
    time.sleep(2)
    
    # Connect peers
    connect_peers()
    print("✓ Nodes connected")
    
    # Wait for leader
    print()
    print("Waiting for leader election...")
    for i in range(30):
        time.sleep(0.5)
        leader_port, leader_id = find_leader()
        if leader_port:
            print()
            print("=" * 60)
            print("✓ Cluster is running!")
            print("=" * 60)
            print(f"Leader: Node {leader_id} on port {leader_port}")
            print()
            print("You can now use the Python KV store:")
            print(f"  from python_kv import KVStore")
            print(f"  kv = KVStore('http://localhost:{leader_port}', server_id={leader_id})")
            print()
            print("To stop: Close the node windows or press Ctrl+C")
            return
    
    print()
    print("⚠ Cluster started but no leader found yet.")
    print("Check the node windows for details.")

if __name__ == "__main__":
    try:
        main()
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        kill_existing_processes()
        sys.exit(0)
