# Python Security Best Practices (OWASP)

## Input Validation

- Never trust user input; validate and sanitize all inputs
- Use allow-lists over deny-lists for input validation
- Validate file uploads: check type, size, and content
- Prevent path traversal by normalizing and validating file paths

## Injection Prevention

- Use parameterized queries for all database operations (SQLAlchemy ORM or bound params)
- Never use `eval()`, `exec()`, or `compile()` on untrusted input
- Avoid `os.system()` and `subprocess.call(shell=True)` — use `subprocess.run()` with arg lists
- Sanitize inputs used in Jinja2 templates to prevent XSS

## Authentication & Secrets

- Never hardcode secrets, API keys, or passwords in source code
- Use environment variables or secret managers for credentials
- Hash passwords with bcrypt or argon2, never MD5 or SHA-256 alone
- Implement rate limiting on authentication endpoints

## Dependency Security

- Keep dependencies updated and audit with `pip-audit` or `safety`
- Pin dependency versions for reproducible builds
- Use `bandit` for static security analysis
- Review third-party packages before adding them

## Common Vulnerabilities

- Avoid `pickle.loads()` on untrusted data (arbitrary code execution)
- Use `secrets` module instead of `random` for security-sensitive operations
- Set appropriate file permissions (avoid 777)
- Enable HTTPS and set secure cookie flags
