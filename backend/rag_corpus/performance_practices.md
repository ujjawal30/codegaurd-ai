# Python Performance Best Practices

## Data Structures

- Use sets for membership testing (O(1) vs O(n) for lists)
- Use `collections.defaultdict` and `Counter` instead of manual dict operations
- Prefer generators over lists for large sequences (`yield` vs `return []`)
- Use `deque` for efficient queue operations instead of list pop(0)

## Algorithmic Efficiency

- Avoid nested loops where possible — use dict lookups or set operations
- Precompute values outside loops when possible
- Use `itertools` for efficient combinatorial operations
- Limit recursion depth; prefer iterative solutions for deep recursion

## I/O and Async

- Use async I/O for network-bound operations
- Batch database queries — avoid N+1 query patterns
- Use connection pooling for database and HTTP connections
- Cache expensive computations with `functools.lru_cache` or Redis

## Memory Management

- Close files and connections explicitly or use context managers
- Use `__slots__` for classes with many instances
- Avoid circular references that prevent garbage collection
- Profile memory with `tracemalloc` or `memory_profiler`

## String Operations

- Use `str.join()` instead of `+=` for string concatenation in loops
- Use f-strings for formatting (fastest string interpolation method)
- Compile regular expressions used in loops with `re.compile()`
