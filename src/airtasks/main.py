"""Generic background task handling for Air applications.

This module provides reusable components for managing background tasks:
- LRULockDict: Thread-safe lock management with LRU eviction
- spawn_task: Helper to spawn fire-and-forget background tasks
- run_task_with_lock: Run task with automatic lock management

Can be used in any Air application that needs background task management.
"""

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger


class LRULockDict:
    """LRU cache for resource locks with automatic cleanup.

    Maintains locks for recently accessed resources, automatically evicting
    the least recently used locks when the cache reaches max_size.

    This prevents unbounded memory growth while ensuring that actively
    processed resources always have their locks available.
    """

    def __init__(self, max_size: int = 2000):
        """Initialize LRU lock dictionary.

        Args:
            max_size: Maximum number of locks to keep in cache.
                     At ~400 bytes per lock, 2000 locks = ~800KB memory.
        """
        self.locks: OrderedDict[int, asyncio.Lock] = OrderedDict()
        self.max_size = max_size

    def __getitem__(self, resource_id: int) -> asyncio.Lock:
        """Get lock for resource, creating if needed and evicting LRU if at capacity."""
        # Move to end (mark as recently used)
        if resource_id in self.locks:
            self.locks.move_to_end(resource_id)
        else:
            # Create new lock
            self.locks[resource_id] = asyncio.Lock()
            self.locks.move_to_end(resource_id)

            # Evict oldest if over max size
            if len(self.locks) > self.max_size:
                oldest_id = next(iter(self.locks))
                del self.locks[oldest_id]
                logger.warning(
                    f"Evicted lock for resource {oldest_id} from cache "
                    f"(cache size: {len(self.locks)}/{self.max_size})"
                )

        return self.locks[resource_id]


def spawn_task(coro: Awaitable[Any], name: str | None = None) -> asyncio.Task:
    """Spawn a fire-and-forget background task.

    Args:
        coro: Coroutine to run in background
        name: Optional task name for debugging

    Returns:
        The created asyncio.Task
    """
    task = asyncio.create_task(coro, name=name)

    def log_exception(t: asyncio.Task) -> None:
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Background task {name or 'unnamed'} failed: {e}")

    task.add_done_callback(log_exception)
    return task


async def run_task_with_lock(
    lock_dict: LRULockDict,
    resource_id: int,
    task_fn: Callable[[], Awaitable[Any]],
) -> Any:
    """Run a task with automatic lock management.

    Args:
        lock_dict: LRULockDict instance to get lock from
        resource_id: ID of resource to lock
        task_fn: Async function to run while holding the lock

    Returns:
        Result from task_fn
    """
    async with lock_dict[resource_id]:
        return await task_fn()
