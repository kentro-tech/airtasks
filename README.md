# AirTasks

**Generic background task handling for Air applications**

A lightweight library for managing background tasks in async Python applications, especially designed for [Air](https://github.com/feldroy/air) web apps.

## Features

- 🔒 **LRULockDict**: Resource locking with automatic LRU eviction to prevent race conditions
- 🚀 **spawn_task**: Helper to spawn fire-and-forget background tasks with automatic exception logging
- 🔐 **run_task_with_lock**: Run tasks with automatic lock management

## Installation

```bash
pip install airtasks
```

Or with uv:

```bash
uv add airtasks
```

## Quick Start

### 1. Spawning Background Tasks

```python
from airtasks import spawn_task

async def process_data(data_id: int):
    # Do expensive work
    await expensive_operation(data_id)

# Spawn it - exceptions are automatically logged
spawn_task(process_data(123), name="process-123")
```

### 2. Resource Locking with LRU Eviction

```python
from airtasks import LRULockDict

# Create a lock dictionary (max 2000 locks in memory)
resource_locks = LRULockDict(max_size=2000)

# Use locks to prevent race conditions
async def process_resource(resource_id: int):
    async with resource_locks[resource_id]:
        # Only one task can process this resource at a time
        await do_work(resource_id)
```

### 4. Complete Example

Run the demo to see all features in action in `tests/demo.py`

```bash
just run
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/kentro-tech/airtasks).
