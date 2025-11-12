"""AirTasks - Generic background task handling for Air applications."""

from .main import LRULockDict as LRULockDict
from .main import run_task_with_lock as run_task_with_lock
from .main import spawn_task as spawn_task

__version__ = "0.1.0"
