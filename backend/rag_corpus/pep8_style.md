# PEP 8 Style Guidelines

## Naming Conventions

- Use `snake_case` for functions, variables, and module names
- Use `PascalCase` for class names
- Use `UPPER_SNAKE_CASE` for constants
- Prefix private attributes with a single underscore `_`
- Avoid single-character variable names except for loop counters

## Formatting Rules

- Maximum line length: 88 characters (Black default) or 79 (PEP 8 strict)
- Use 4 spaces for indentation, never tabs
- Two blank lines before top-level definitions, one blank line between methods
- Imports should be on separate lines and grouped: stdlib, third-party, local

## Docstrings

- All public modules, classes, and functions must have docstrings
- Use Google-style or NumPy-style docstrings consistently
- Include Args, Returns, and Raises sections for functions

## Common Violations

- Missing whitespace around operators
- Trailing whitespace and missing newline at end of file
- Wildcard imports (`from module import *`)
- Mutable default arguments (`def f(x=[])`)
