#!/usr/bin/env python3
"""
Benchmark script to measure operations per second (ops/sec) of the Raft KV store.
"""

import sys
import os
import time
import requests
from statistics import mean, median

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

def benchmark_put(kv, num_ops=100):
    """Benchmark PUT operations."""
    print(f"Benchmarking {num_ops} PUT operations...")
    
    start_time = time.time()
    successful = 0
    
    for i in range(num_ops):
        try:
            kv.put(f"bench_key_{i}", f"value_{i}")
            successful += 1
        except Exception as e:
            print(f"  Error on operation {i}: {e}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    ops_per_sec = successful / elapsed if elapsed > 0 else 0
    
    return successful, elapsed, ops_per_sec

def benchmark_get(kv, num_ops=100):
    """Benchmark GET operations."""
    print(f"Benchmarking {num_ops} GET operations...")
    
    # First, make sure keys exist
    for i in range(num_ops):
        try:
            kv.put(f"bench_key_{i}", f"value_{i}")
        except:
            pass
    
    time.sleep(0.5)  # Let commits settle
    
    start_time = time.time()
    successful = 0
    
    for i in range(num_ops):
        try:
            value, found = kv.get(f"bench_key_{i}")
            if found:
                successful += 1
        except Exception as e:
            print(f"  Error on operation {i}: {e}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    ops_per_sec = successful / elapsed if elapsed > 0 else 0
    
    return successful, elapsed, ops_per_sec

def benchmark_mixed(kv, num_ops=100):
    """Benchmark mixed PUT and GET operations."""
    print(f"Benchmarking {num_ops} mixed PUT/GET operations...")
    
    start_time = time.time()
    successful = 0
    
    for i in range(num_ops):
        try:
            if i % 2 == 0:
                # PUT
                kv.put(f"mixed_key_{i}", f"value_{i}")
            else:
                # GET
                kv.get(f"mixed_key_{i-1}")
            successful += 1
        except Exception as e:
            print(f"  Error on operation {i}: {e}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    ops_per_sec = successful / elapsed if elapsed > 0 else 0
    
    return successful, elapsed, ops_per_sec

def run_benchmark(num_ops=100, warmup_ops=10):
    """Run complete benchmark suite."""
    print("=" * 60)
    print("Raft KV Store - Performance Benchmark")
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
    if warmup_ops > 0:
        print(f"Warming up with {warmup_ops} operations...")
        for i in range(warmup_ops):
            try:
                kv.put(f"warmup_{i}", f"warmup_value_{i}")
            except:
                pass
        time.sleep(0.5)
        print("✓ Warmup complete")
        print()
    
    results = {}
    
    # Benchmark PUT
    successful, elapsed, ops_per_sec = benchmark_put(kv, num_ops)
    results['PUT'] = {
        'successful': successful,
        'elapsed': elapsed,
        'ops_per_sec': ops_per_sec
    }
    print(f"  ✓ {successful}/{num_ops} successful in {elapsed:.2f}s")
    print(f"  📊 {ops_per_sec:.2f} ops/sec")
    print()
    
    # Benchmark GET
    successful, elapsed, ops_per_sec = benchmark_get(kv, num_ops)
    results['GET'] = {
        'successful': successful,
        'elapsed': elapsed,
        'ops_per_sec': ops_per_sec
    }
    print(f"  ✓ {successful}/{num_ops} successful in {elapsed:.2f}s")
    print(f"  📊 {ops_per_sec:.2f} ops/sec")
    print()
    
    # Benchmark Mixed
    successful, elapsed, ops_per_sec = benchmark_mixed(kv, num_ops)
    results['MIXED'] = {
        'successful': successful,
        'elapsed': elapsed,
        'ops_per_sec': ops_per_sec
    }
    print(f"  ✓ {successful}/{num_ops} successful in {elapsed:.2f}s")
    print(f"  📊 {ops_per_sec:.2f} ops/sec")
    print()
    
    # Summary
    print("=" * 60)
    print("Benchmark Summary")
    print("=" * 60)
    print(f"{'Operation':<15} {'Ops/sec':<15} {'Time (s)':<15} {'Success':<15}")
    print("-" * 60)
    for op_type, result in results.items():
        print(f"{op_type:<15} {result['ops_per_sec']:>13.2f} {result['elapsed']:>13.2f} {result['successful']:>14}/{num_ops}")
    print()
    
    avg_ops_per_sec = mean([r['ops_per_sec'] for r in results.values()])
    print(f"Average throughput: {avg_ops_per_sec:.2f} ops/sec")
    print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Benchmark Raft KV Store performance')
    parser.add_argument('-n', '--num-ops', type=int, default=100,
                       help='Number of operations per test (default: 100)')
    parser.add_argument('--warmup', type=int, default=10,
                       help='Number of warmup operations (default: 10)')
    
    args = parser.parse_args()
    
    run_benchmark(num_ops=args.num_ops, warmup_ops=args.warmup)

if __name__ == "__main__":
    main()

