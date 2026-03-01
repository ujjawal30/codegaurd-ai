# SOLID Principles for Python

## Single Responsibility Principle (SRP)

- Each class/module should have one reason to change
- Functions should do one thing and do it well
- Avoid "god classes" with too many responsibilities
- Split large modules into focused sub-modules

## Open/Closed Principle (OCP)

- Classes should be open for extension, closed for modification
- Use abstract base classes and protocols for extensibility
- Prefer composition over deep inheritance hierarchies

## Liskov Substitution Principle (LSP)

- Subtypes must be substitutable for their base types
- Don't override methods to do nothing or raise NotImplementedError
- Maintain pre/post-conditions in overridden methods

## Interface Segregation Principle (ISP)

- Don't force classes to implement interfaces they don't use
- Use Python Protocols for structural typing
- Prefer many small, focused interfaces over one large one

## Dependency Inversion Principle (DIP)

- Depend on abstractions, not concrete implementations
- Use dependency injection for external services
- Configuration should flow inward, not be hardcoded
