"""Interactive Air web app demo of airtasks.

Run with: just run
Then visit: http://localhost:8000
"""

import asyncio

import air

from airtasks import LRULockDict, run_task_with_lock, spawn_task

# In-memory storage for demo
task_counters = {"unsafe": 0, "safe": 0}
task_spawn_counts = {"unsafe": 0, "safe": 0}
task_results = {"unsafe": [], "safe": []}
locks = LRULockDict(max_size=500)


async def unsafe_increment_task(task_id: int):
    """Demonstrates race condition without locks."""
    current = task_counters["unsafe"]
    await asyncio.sleep(1)  # Simulate work - creates race condition
    new_value = current + 1
    task_counters["unsafe"] = new_value

    # Store what this task read and wrote
    task_results["unsafe"].append(
        {"task": task_id, "read": current, "wrote": new_value}
    )


async def safe_increment_task(task_id: int):
    """Demonstrates safe increment with locks."""

    async def do_increment():
        current = task_counters["safe"]
        await asyncio.sleep(1)  # Simulate work - but protected by lock
        new_value = current + 1
        task_counters["safe"] = new_value

        # Store what this task read and wrote
        task_results["safe"].append(
            {"task": task_id, "read": current, "wrote": new_value}
        )

    # Use resource_id=1 so all tasks are serialized
    await run_task_with_lock(locks, 1, do_increment)


# Air routes
app = air.Air()


@app.get("/")
async def index(request: air.Request):
    """Main demo page."""
    return air.layouts.mvpcss(
        air.Title("AirTasks Demo"),
        air.H1("AirTasks Demo"),
        air.P("Demonstrates why locks are needed for concurrent task execution"),
        # Demo 1: Race condition without locks
        air.Article(
            air.H2("❌ Without Locks (Broken)"),
            air.P(
                "Each task reads the counter, sleeps 0.5s, then writes counter+1. "
                "When tasks run concurrently, multiple tasks read the SAME value, "
                "causing lost updates."
            ),
            air.P(
                "Expected: ",
                air.Span(str(task_spawn_counts["unsafe"]), id="unsafe-expected"),
                " | Actual: ",
                air.Span(str(task_counters["unsafe"]), id="unsafe-counter"),
            ),
            air.Div(
                air.Button(
                    "Increment Once",
                    hx_post="/spawn/unsafe",
                    hx_target="#unsafe-results",
                    hx_swap="afterbegin",
                ),
                air.Button(
                    "Increment 5x Fast! 🚀",
                    hx_post="/spawn-multiple/unsafe/5",
                    hx_target="#unsafe-results",
                    hx_swap="afterbegin",
                ),
            ),
            air.Div(id="unsafe-results"),
            air.Div(
                id="unsafe-poller",
                hx_get="/counter/unsafe",
                hx_trigger="every 1s",
                hx_swap="none",
            ),
        ),
        # Demo 2: Safe with locks
        air.Article(
            air.H2("✅ With Locks (Working)"),
            air.P(
                "Using run_task_with_lock() ensures only ONE task executes at a time. "
                "Tasks wait their turn, so each reads the correct incremented value. "
                "Expected always equals Actual!"
            ),
            air.P(
                "Expected: ",
                air.Span(str(task_spawn_counts["safe"]), id="safe-expected"),
                " | Actual: ",
                air.Span(str(task_counters["safe"]), id="safe-counter"),
            ),
            air.Div(
                air.Button(
                    "Increment Once",
                    hx_post="/spawn/safe",
                    hx_target="#safe-results",
                    hx_swap="afterbegin",
                ),
                air.Button(
                    "Increment 5x Fast! 🚀",
                    hx_post="/spawn-multiple/safe/5",
                    hx_target="#safe-results",
                    hx_swap="afterbegin",
                ),
            ),
            air.Div(id="safe-results"),
            air.Div(
                id="safe-poller",
                hx_get="/counter/safe",
                hx_trigger="every 1s",
                hx_swap="none",
            ),
        ),
    )


task_id_counter = 0


@app.post("/spawn/unsafe")
async def spawn_unsafe(request: air.Request):
    """Spawn unsafe increment task."""
    global task_id_counter
    task_id_counter += 1
    task_id = task_id_counter
    task_spawn_counts["unsafe"] += 1

    spawn_task(unsafe_increment_task(task_id), name=f"unsafe-{task_id}")

    return air.Div(
        air.Code(f"Task {task_id}: "),
        id=f"result-{task_id}",
        hx_get=f"/result/{task_id}/unsafe",
        hx_trigger="load delay:100ms, load delay:600ms, load delay:1200ms",
    )


@app.post("/spawn-multiple/{counter_type}/{count}")
async def spawn_multiple(request: air.Request, counter_type: str, count: int):
    """Spawn multiple tasks at once to demonstrate race condition."""
    global task_id_counter
    results = []

    for _ in range(count):
        task_id_counter += 1
        task_id = task_id_counter
        task_spawn_counts[counter_type] += 1

        if counter_type == "unsafe":
            spawn_task(unsafe_increment_task(task_id), name=f"unsafe-{task_id}")
        else:
            spawn_task(safe_increment_task(task_id), name=f"safe-{task_id}")

        results.append(
            air.Div(
                air.Code(f"Task {task_id}: "),
                id=f"result-{task_id}",
                hx_get=f"/result/{task_id}/{counter_type}",
                hx_trigger="load delay:100ms, load delay:600ms, load delay:1200ms",
            )
        )

    return air.Children(*results)


@app.post("/spawn/safe")
async def spawn_safe(request: air.Request):
    """Spawn safe increment task."""
    global task_id_counter
    task_id_counter += 1
    task_id = task_id_counter
    task_spawn_counts["safe"] += 1

    spawn_task(safe_increment_task(task_id), name=f"safe-{task_id}")

    return air.Div(
        air.Code(f"Task {task_id}: "),
        id=f"result-{task_id}",
        hx_get=f"/result/{task_id}/safe",
        hx_trigger="load delay:100ms, load delay:600ms, load delay:1200ms",
    )


@app.get("/result/{task_id}/{counter_type}")
async def get_result(request: air.Request, task_id: int, counter_type: str):
    """Get result for a specific task."""
    # Find the result for this task
    results = task_results.get(counter_type, [])
    result = next((r for r in results if r["task"] == task_id), None)

    if not result:
        return air.Code(f"Task {task_id} started")

    # When result is ready, also update the counters
    actual = task_counters.get(counter_type, 0)
    expected = task_spawn_counts.get(counter_type, 0)

    return air.Children(
        air.Code(f"Task {task_id}: read {result['read']}, wrote {result['wrote']}"),
        air.Span(str(expected), id=f"{counter_type}-expected", hx_swap_oob="true"),
        air.Span(str(actual), id=f"{counter_type}-counter", hx_swap_oob="true"),
    )


@app.get("/counter/{counter_type}")
async def get_counter(request: air.Request, counter_type: str):
    """Get current counter value and update display."""
    actual = task_counters.get(counter_type, 0)
    expected = task_spawn_counts.get(counter_type, 0)

    return air.Children(
        air.Span(str(expected), id=f"{counter_type}-expected", hx_swap_oob="true"),
        air.Span(str(actual), id=f"{counter_type}-counter", hx_swap_oob="true"),
    )
