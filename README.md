# AirTasks

**Generic background task handling for Air applications**

A lightweight, database-agnostic library for managing background tasks in async Python applications, especially designed for [Air](https://github.com/feldroy/air) web apps.

## Features

- 🔒 **LRULockDict**: Resource locking with automatic LRU eviction to prevent race conditions
- 📝 **TaskLogger**: Database-agnostic task logging using callbacks
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

### 3. Database-Agnostic Task Logging

```python
from airtasks import TaskLogger
from datetime import datetime

# Define how to persist logs (works with any database)
async def save_log(
    resource_id: int,
    task_type: str,
    task_run_id: str,
    timestamp: datetime,
    level: str,
    message: str,
):
    # Could be SQLAlchemy, MongoDB, Redis, files, etc.
    await db.execute(
        "INSERT INTO task_logs VALUES (?, ?, ?, ?, ?, ?)",
        (resource_id, task_type, task_run_id, timestamp, level, message)
    )

# Create logger
logger = TaskLogger(
    resource_id=123,
    task_type="data_processing",
    task_run_id="uuid-here",
    log_callback=save_log,
)

# Log progress
await logger.log("Starting processing...")
await logger.log("Processing complete!", level="success")
await logger.log("Something went wrong", level="error")
```

### 4. Complete Example

```python
import uuid
from airtasks import LRULockDict, TaskLogger, spawn_task, run_task_with_lock

# Setup
locks = LRULockDict(max_size=1000)

async def log_to_db(resource_id, task_type, task_run_id, timestamp, level, message):
    # Your database persistence logic here
    pass

async def process_item(item_id: int):
    """Background task to process an item with lock and logging."""
    task_run_id = str(uuid.uuid4())
    logger = TaskLogger(item_id, "processing", task_run_id, log_to_db)
    
    async def do_work():
        await logger.log("Starting work...")
        # Do actual work
        result = await expensive_computation(item_id)
        await logger.log("Work complete!", level="success")
        return result
    
    # Run with automatic lock management
    return await run_task_with_lock(locks, item_id, do_work)

# Spawn the background task
spawn_task(process_item(456), name="process-456")
```

## Integration with Air

Perfect for Air applications:

```python
import air
from airtasks import spawn_task

async def generate_content(request: air.Request, item_id: int):
    # Spawn background task
    spawn_task(process_item(item_id), name=f"item-{item_id}")
    
    # Return immediately to user
    return air.Div("Processing started!")
```

## Why AirTasks?

- **Database-agnostic**: Uses callbacks instead of hardcoded database code
- **Minimal dependencies**: Only requires `loguru` for logging
- **Memory-efficient**: LRU eviction prevents unbounded lock growth
- **Safe**: Automatic exception logging prevents silent failures
- **Simple**: No complex queue systems, just `asyncio.create_task`

## Demo

Run the demo to see all features in action:

```bash
uv run python tests/demo.py
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
just test

# Format and lint
just qa

# Check formatting
just lint
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or PR on [GitHub](https://github.com/kentro-tech/airtasks).
