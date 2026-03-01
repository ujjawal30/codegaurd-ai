# Python Async/Await Best Practices

## Async Design

- Use `async def` for I/O-bound operations (network, file, database)
- Don't use async for CPU-bound work — use `concurrent.futures` instead
- Prefer `asyncio.gather()` for concurrent I/O operations
- Use `asyncio.TaskGroup` (Python 3.11+) for structured concurrency

## Common Pitfalls

- Don't call sync blocking functions inside async code (blocks event loop)
- Use `asyncio.to_thread()` to run blocking I/O in a thread pool
- Don't forget to `await` coroutines — unawaited coroutines are silently dropped
- Avoid global mutable state; use `contextvars` for async-safe context

## Resource Management

- Use `async with` for async context managers (connections, sessions)
- Close async resources explicitly with `aclose()` or async context managers
- Implement connection pooling for databases and HTTP clients
- Set timeouts on all external async calls to prevent hanging

## Error Handling

- Catch exceptions in individual tasks to prevent group cancellation
- Use `asyncio.shield()` to protect critical operations from cancellation
- Handle `asyncio.CancelledError` for graceful shutdown
- Log errors with task context (task name, correlation ID)

## Testing Async Code

- Use `pytest-asyncio` with `@pytest.mark.asyncio` decorator
- Mock async functions with `AsyncMock` from `unittest.mock`
- Test timeout behavior and cancellation paths
- Use `asyncio.Event` for synchronization in tests
