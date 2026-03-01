"""
Shared pytest fixtures for CodeGuard AI backend tests.
"""

import pytest

# ── Sample Python source code ───────────────────────────────────

SAMPLE_PYTHON_SIMPLE = '''
"""A simple module."""

import os
from typing import Optional

CONFIG_VALUE = "hello"


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


async def async_fetch(url: str):
    """Async placeholder."""
    pass


class UserService:
    """Manages users."""

    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: int) -> Optional[dict]:
        """Fetch user by ID."""
        if user_id <= 0:
            return None
        return self.db.find(user_id)

    @staticmethod
    def validate_email(email: str) -> bool:
        return "@" in email
'''

SAMPLE_PYTHON_COMPLEX = '''
def complex_function(data, mode, flag=False):
    """A function with high cyclomatic complexity."""
    if not data:
        return None
    if mode == "a":
        for item in data:
            if item > 0:
                if flag:
                    return item * 2
                else:
                    return item
            elif item == 0:
                continue
            else:
                try:
                    result = 1 / item
                except ZeroDivisionError:
                    result = 0
                return result
    elif mode == "b":
        while data:
            val = data.pop()
            if val > 10:
                break
        return val
    return -1
'''

SAMPLE_PYTHON_SYNTAX_ERROR = '''
def broken_func(
    print("oops"
'''

SAMPLE_PYTHON_WITH_MAIN = '''
def main():
    print("running")

if __name__ == "__main__":
    main()
'''
