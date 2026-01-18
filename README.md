# Python Key-Value Store with Raft Consensus

A distributed key-value store in Python that uses the [Raft consensus algorithm](https://github.com/eliben/raft) implemented in Go via an HTTP bridge.

## Performance

**Throughput: ~1000 ops/sec**

Run benchmarks:
```bash
python tests/benchmark.py -n 100
python tests/benchmark_async.py -n 500 -t 20
```

## Installation

### Prerequisites

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Go 1.23+** - [Download](https://go.dev/dl/) (required to build the Raft bridge)
- **pip** - Usually comes with Python

### Install from PyPI

```bash
pip install python-raft-kv
```

### Install from Source

```bash
# 1. Clone the repository
git clone https://github.com/atharvagasheTAMU/python-raft-kv.git
cd python-raft-kv

# 2. Install the package
pip install -e .

# Or install as a regular package
pip install .
```

This will:
- Install the `python_kv` Python package
- Install dependencies (`requests`, `psutil`)
- Make the `raft-kv-start` command available

**Note:** The Go bridge will be automatically built on first use when you start the cluster.

## Quick Start

### Start the Cluster

```bash
# Start the 3-node cluster
raft-kv-start
```

This will:
- Build the Go bridge if needed (requires Go to be installed)
- Start 3 Raft nodes on ports 8080, 8081, 8082
- Connect them together
- Wait for leader election

### Usage

```python
from python_kv import KVStore

# Connect to the leader (check which port is leader after starting)
kv = KVStore("http://localhost:8080", server_id=0)

# Put a value
prev_value, was_found = kv.put("hello", "world")

# Get a value
value, found = kv.get("hello")
print(value)  # "world"

# Compare-and-swap
old_value, was_found = kv.cas("key", "old", "new")

# Check if leader
is_leader = kv.is_leader()
```

## HTTP API

The bridge exposes HTTP endpoints on ports 8080, 8081, 8082 (for nodes 0, 1, 2).

### Check if leader
```bash
GET http://localhost:8080/is_leader
# Response: {"is_leader": true}
```

### Submit a command (PUT)
```bash
POST http://localhost:8080/submit
Content-Type: application/json

{
  "kind": "put",
  "key": "hello",
  "value": "world"
}

# Response: {"log_index": 0, "is_leader": true}
```

### Submit a command (GET)
```bash
POST http://localhost:8080/submit
Content-Type: application/json

{
  "kind": "get",
  "key": "hello"
}

# Response: {"log_index": 1, "is_leader": true}
```

### Submit a command (CAS)
```bash
POST http://localhost:8080/submit
Content-Type: application/json

{
  "kind": "cas",
  "key": "hello",
  "compare_value": "world",
  "value": "newvalue"
}

# Response: {"log_index": 2, "is_leader": true}
```

### Wait for commit
```bash
POST http://localhost:8080/wait_commit
Content-Type: application/json

{
  "log_index": 0,
  "timeout_ms": 30000
}

# Response: {
#   "index": 0,
#   "term": 1,
#   "command": {"kind": "put", "key": "hello", "value": "world", "id": 0}
# }
```

### Get commit by index
```bash
GET http://localhost:8080/get_commit?index=0

# Response: {
#   "index": 0,
#   "term": 1,
#   "command": {"kind": "put", "key": "hello", "value": "world", "id": 0}
# }
```

### Get commits since index
```bash
GET http://localhost:8080/get_commits_since?since_index=-1

# Response: {
#   "commits": [...],
#   "count": 5
# }
```

## Testing

```bash
# Basic functionality
python tests/test_setup.py
python tests/test_3node.py

# Fault tolerance
python tests/test_fault_tolerance.py
python tests/test_data_persistence.py

# Performance benchmarks
python tests/benchmark.py -n 100
python tests/benchmark_async.py -n 500 -t 20
```

## Architecture

```
Python KV Store ←→ HTTP API ←→ Go Raft Bridge ←→ Raft Implementation
```

The project includes:
- **`python_kv/`** - Python key-value store client
- **`raft-bridge/`** - Go HTTP bridge service
- **`raft/`** - Raft consensus implementation (from [eliben/raft](https://github.com/eliben/raft))

## Stopping the Cluster

**Windows:**
```powershell
Get-Process -Name raft-bridge | Stop-Process
```

**Linux/Mac:**
```bash
pkill -f raft-bridge
```

Or simply close the node windows.

## Credits

This project uses the Raft implementation from [eliben/raft](https://github.com/eliben/raft) by Eli Bendersky.
