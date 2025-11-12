"""Tests for airtasks."""

import asyncio
from datetime import datetime

import pytest

from airtasks import LRULockDict, TaskLogger, run_task_with_lock, spawn_task


def test_lru_lock_dict_creates_locks():
    """Test that LRULockDict creates locks on demand."""
    locks = LRULockDict(max_size=10)
    lock1 = locks[1]
    lock2 = locks[1]
    assert lock1 is lock2  # Same lock for same ID


def test_lru_lock_dict_evicts_old_locks():
    """Test that LRULockDict evicts old locks when max_size is reached."""
    locks = LRULockDict(max_size=2)
    lock1 = locks[1]  # noqa: F841
    lock2 = locks[2]  # noqa: F841
    lock3 = locks[3]  # noqa: F841  # Should evict lock for ID 1

    assert 1 not in locks.locks
    assert 2 in locks.locks
    assert 3 in locks.locks


@pytest.mark.asyncio
async def test_task_logger_calls_callback():
    """Test that TaskLogger calls the log callback."""
    logs = []

    async def save_log(
        resource_id: int,
        task_type: str,
        task_run_id: str,
        timestamp: datetime,
        level: str,
        message: str,
    ):
        logs.append((resource_id, task_type, level, message))

    logger = TaskLogger(123, "test_task", "run-1", save_log)
    await logger.log("Test message", level="info")

    assert len(logs) == 1
    assert logs[0][0] == 123
    assert logs[0][1] == "test_task"
    assert logs[0][2] == "info"
    assert logs[0][3] == "Test message"


@pytest.mark.asyncio
async def test_spawn_task_executes():
    """Test that spawn_task executes the coroutine."""
    result = []

    async def simple_task():
        result.append("done")

    task = spawn_task(simple_task(), name="test")
    await task
    assert result == ["done"]


@pytest.mark.asyncio
async def test_spawn_task_logs_exceptions():
    """Test that spawn_task logs exceptions without crashing."""

    async def failing_task():
        raise ValueError("Test error")

    task = spawn_task(failing_task(), name="failing")
    # Should not raise - exception is logged
    await asyncio.sleep(0.1)
    assert task.done()


@pytest.mark.asyncio
async def test_run_task_with_lock():
    """Test that run_task_with_lock acquires lock before running."""
    locks = LRULockDict(max_size=10)
    execution_order = []

    async def task(task_id: int):
        execution_order.append(f"{task_id}-start")
        await asyncio.sleep(0.1)
        execution_order.append(f"{task_id}-end")

    # Run two tasks on same resource - should be serialized
    await asyncio.gather(
        run_task_with_lock(locks, 1, lambda: task(1)),
        run_task_with_lock(locks, 1, lambda: task(2)),
    )

    # One should complete before the other starts
    assert execution_order in [
        ["1-start", "1-end", "2-start", "2-end"],
        ["2-start", "2-end", "1-start", "1-end"],
    ]


@pytest.mark.asyncio
async def test_run_task_with_lock_parallel_resources():
    """Test that different resources can run in parallel."""
    locks = LRULockDict(max_size=10)
    execution_order = []

    async def task(task_id: int):
        execution_order.append(f"{task_id}-start")
        await asyncio.sleep(0.1)
        execution_order.append(f"{task_id}-end")

    # Run two tasks on different resources - should be parallel
    await asyncio.gather(
        run_task_with_lock(locks, 1, lambda: task(1)),
        run_task_with_lock(locks, 2, lambda: task(2)),
    )

    # Both should start before either ends (parallel execution)
    start_indices = [i for i, x in enumerate(execution_order) if x.endswith("-start")]
    end_indices = [i for i, x in enumerate(execution_order) if x.endswith("-end")]

    # Both starts should come before both ends
    assert max(start_indices) < min(end_indices)
