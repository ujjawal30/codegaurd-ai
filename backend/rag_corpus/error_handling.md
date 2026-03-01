# Python Error Handling Best Practices

## Exception Design

- Create custom exception hierarchies for your application
- Inherit from specific built-in exceptions, not bare `Exception`
- Include meaningful error messages with context
- Use exception chaining: `raise NewError("msg") from original_error`

## Try/Except Patterns

- Catch specific exceptions, never bare `except:` or `except Exception:`
- Keep try blocks as small as possible
- Use `else` clause for code that runs only when no exception occurs
- Use `finally` for cleanup that must always run

## Logging Errors

- Log errors at the appropriate level (warning, error, critical)
- Include stack traces with `logger.exception()` in except blocks
- Add context to error logs (user ID, request ID, input values)
- Don't log and re-raise without adding value

## Graceful Degradation

- Return sensible defaults when non-critical operations fail
- Implement circuit breaker patterns for external service calls
- Use retry logic with exponential backoff for transient failures
- Provide user-friendly error messages while logging details internally

## Common Anti-patterns

- Silently swallowing exceptions (`except: pass`)
- Using exceptions for control flow
- Catching too broadly and masking bugs
- Not cleaning up resources on error (use context managers)
