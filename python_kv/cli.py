#!/usr/bin/env python3
"""
Command-line interface for starting the Raft KV store cluster.
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path


def check_go_bridge_exists():
    """Check if the Go bridge executable exists."""
    # Try to find bridge in package directory or current directory
    package_dir = Path(__file__).parent.parent
    if sys.platform == "win32":
        bridge_path = package_dir / "raft-bridge" / "raft-bridge.exe"
    else:
        bridge_path = package_dir / "raft-bridge" / "raft-bridge"
    
    if bridge_path.exists():
        return bridge_path
    
    # Also check current directory
    if sys.platform == "win32":
        bridge_path = Path("raft-bridge/raft-bridge.exe")
    else:
        bridge_path = Path("raft-bridge/raft-bridge")
    
    return bridge_path if bridge_path.exists() else None


def build_go_bridge():
    """Build the Go bridge executable."""
    package_dir = Path(__file__).parent.parent
    bridge_dir = package_dir / "raft-bridge"
    
    if not bridge_dir.exists():
        print("Error: raft-bridge directory not found!")
        return False
    
    print("Building Go bridge...")
    original_dir = os.getcwd()
    os.chdir(bridge_dir)
    
    try:
        if sys.platform == "win32":
            cmd = ["go", "build", "-o", "raft-bridge.exe", "main.go", "command.go"]
        else:
            cmd = ["go", "build", "-o", "raft-bridge", "main.go", "command.go"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error building bridge: {result.stderr}")
            return False
        
        print("✓ Go bridge built successfully")
        return True
    finally:
        os.chdir(original_dir)


def kill_existing_processes():
    """Kill any existing bridge processes."""
    try:
        import psutil
        print("Checking for existing bridge processes...")
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if 'raft-bridge' in proc.name().lower():
                print(f"  Stopping existing raft-bridge process: {proc.pid}")
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                    killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                        killed += 1
                    except:
                        pass
        if killed > 0:
            print(f"✓ Stopped {killed} existing process(es)")
            time.sleep(1)
    except ImportError:
        # psutil not available, try basic approach
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "raft-bridge.exe"], 
                         capture_output=True, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["pkill", "-f", "raft-bridge"], 
                         capture_output=True, stderr=subprocess.DEVNULL)


def start_node(node_id, port, peer_ids, bridge_path):
    """Start a single Raft node."""
    print(f"Starting node {node_id} on port {port}...")
    
    peers_str = ",".join(map(str, peer_ids))
    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    
    process = subprocess.Popen(
        [str(bridge_path), str(node_id), str(port), peers_str],
        cwd=os.getcwd(),
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(0.5)
    return process


def connect_peers():
    """Connect all peers together."""
    # Get listen addresses first
    addresses = {}
    for port, node_id in [(8080, 0), (8081, 1), (8082, 2)]:
        for _ in range(10):
            try:
                response = requests.get(f"http://localhost:{port}/listen_addr", timeout=1)
                if response.status_code == 200:
                    addr = response.json()["address"]
                    addresses[node_id] = addr
                    break
            except:
                time.sleep(0.2)
    
    # Connect peers
    for port, node_id in [(8080, 0), (8081, 1), (8082, 2)]:
        for peer_id, peer_addr in addresses.items():
            if peer_id != node_id:
                try:
                    requests.post(
                        f"http://localhost:{port}/connect_peer",
                        json={"peer_id": peer_id, "address": peer_addr},
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
    """Main entry point for the CLI."""
    print("=" * 60)
    print("Raft KV Store - Simple Startup")
    print("=" * 60)
    print()
    
    # Check if bridge exists, build if needed
    bridge_path = check_go_bridge_exists()
    if not bridge_path:
        print("Go bridge not found. Building...")
        if not build_go_bridge():
            print("Failed to build Go bridge. Make sure Go is installed.")
            sys.exit(1)
        bridge_path = check_go_bridge_exists()
        if not bridge_path:
            print("Error: Bridge still not found after build!")
            sys.exit(1)
    else:
        print(f"✓ Go bridge found: {bridge_path}")
    
    # Kill existing processes
    print("Cleaning up existing processes...")
    kill_existing_processes()
    time.sleep(1)
    
    print()
    print("Starting 3-node cluster...")
    
    # Start all nodes
    start_node(0, 8080, [1, 2], bridge_path)
    start_node(1, 8081, [0, 2], bridge_path)
    start_node(2, 8082, [0, 1], bridge_path)
    
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
    main()

