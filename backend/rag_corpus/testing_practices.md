# Python Testing Best Practices

## Test Structure

- Follow the Arrange-Act-Assert (AAA) pattern
- One assertion per test when possible (test one behavior)
- Name tests descriptively: `test_<function>_<scenario>_<expected_result>`
- Group related tests in classes, organize by module

## Pytest Patterns

- Use fixtures for shared setup/teardown (`@pytest.fixture`)
- Use parametrize for testing multiple inputs: `@pytest.mark.parametrize`
- Use `conftest.py` for shared fixtures across modules
- Mark slow tests with `@pytest.mark.slow` for selective running

## Mocking

- Mock external dependencies at the boundary (APIs, databases, files)
- Use `unittest.mock.patch` or `pytest-mock` for mocking
- Don't mock what you don't own — wrap third-party APIs
- Assert mock call counts and arguments

## Coverage

- Aim for >80% line coverage on business logic
- Focus coverage on critical paths and error handlers
- Cover edge cases: empty inputs, None values, boundary conditions
- Test error paths and exception handling explicitly

## Anti-patterns

- Don't test implementation details, test behavior
- Avoid test interdependence — each test should be independent
- Don't use `time.sleep()` in tests — use async patterns or mocks
- Avoid excessive setup that obscures the test's purpose
