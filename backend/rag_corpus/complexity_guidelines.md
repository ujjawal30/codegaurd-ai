# Python Code Complexity Guidelines

## Cyclomatic Complexity

- Functions with complexity > 10 should be refactored
- Complexity 1-5: Simple, low risk (Grade A-B)
- Complexity 6-10: Moderate, review recommended (Grade C)
- Complexity 11-20: Complex, refactoring needed (Grade D)
- Complexity > 20: Very high risk, must refactor (Grade F)

## Reducing Complexity

- Extract conditional logic into named helper functions
- Use early returns to reduce nesting depth
- Replace complex if/elif chains with dictionaries or strategy patterns
- Use polymorphism instead of type-checking if/else chains

## Maintainability Index

- Score > 80: Highly maintainable
- Score 60-80: Moderately maintainable
- Score 40-60: Difficult to maintain, needs attention
- Score < 40: Unmaintainable, requires significant refactoring

## Function Design

- Functions should be no longer than 20-30 lines
- Maximum 3-4 parameters; use objects for more
- Single level of abstraction per function
- Functions should do one thing (Single Responsibility)

## Module Design

- Maximum 200-300 lines per module
- Group related functionality into cohesive modules
- Keep import graphs simple — avoid circular dependencies
- Use `__init__.py` exports to define public API
