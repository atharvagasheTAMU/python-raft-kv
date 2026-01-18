#!/usr/bin/env python3
"""
Async benchmark script to measure operations per second with concurrent requests.
This can achieve much higher throughput than sequential operations.
"""

import sys
import os
import time
import requests
import concurrent.futures
from statistics import mean

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_kv import KVStore

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

def submit_operation(kv, op_type, key, value=None):
    """Submit a single operation."""
    try:
        if op_type == "put":
            kv.put(key, value)
            return True
        elif op_type == "get":
            kv.get(key)
            return True
        return False
    except Exception as e:
        return False

def benchmark_concurrent(kv, num_ops=100, num_threads=10):
    """Benchmark with concurrent operations."""
    print(f"Benchmarking {num_ops} operations with {num_threads} concurrent threads...")
    
    def worker(i):
        key = f"concurrent_key_{i}"
        value = f"value_{i}"
        return submit_operation(kv, "put", key, value)
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_ops)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    elapsed = end_time - start_time
    successful = sum(results)
    ops_per_sec = successful / elapsed if elapsed > 0 else 0
    
    return successful, elapsed, ops_per_sec

def run_benchmark(num_ops=100, num_threads=10):
    """Run concurrent benchmark."""
    print("=" * 60)
    print("Raft KV Store - Concurrent Performance Benchmark")
    print("=" * 60)
    print()
    
    # Find leader
    print("Finding leader...")
    leader_port, leader_id = find_leader()
    if not leader_port:
        print("❌ No leader found! Make sure the cluster is running.")
        print("   Start it with: python start.py")
        sys.exit(1)
    
    print(f"✓ Leader found: Node {leader_id} on port {leader_port}")
    print()
    
    # Connect to leader
    kv = KVStore(f"http://localhost:{leader_port}", server_id=leader_id)
    
    # Warmup
    print("Warming up...")
    for i in range(10):
        try:
            kv.put(f"warmup_{i}", f"warmup_value_{i}")
        except:
            pass
    time.sleep(0.5)
    print("✓ Warmup complete")
    print()
    
    # Run concurrent benchmark
    successful, elapsed, ops_per_sec = benchmark_concurrent(kv, num_ops, num_threads)
    
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Operations: {successful}/{num_ops} successful")
    print(f"Time: {elapsed:.2f} seconds")
    print(f"Throughput: {ops_per_sec:.2f} ops/sec")
    print(f"Concurrency: {num_threads} threads")
    print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Concurrent benchmark for Raft KV Store')
    parser.add_argument('-n', '--num-ops', type=int, default=100,
                       help='Number of operations (default: 100)')
    parser.add_argument('-t', '--threads', type=int, default=10,
                       help='Number of concurrent threads (default: 10)')
    
    args = parser.parse_args()
    
    run_benchmark(num_ops=args.num_ops, num_threads=args.threads)

if __name__ == "__main__":
    main()

