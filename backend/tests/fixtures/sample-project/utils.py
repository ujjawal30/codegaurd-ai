"""
TaskMaster — Utility functions.
"""

import os
import subprocess


def format_date(date_str):
    """Format a date string to a human-readable format."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        return date_str


def run_shell_command(cmd):
    """Run a shell command — dangerous: arbitrary command execution."""
    return subprocess.call(cmd, shell=True)


def read_file_unsafe(filename):
    """Read a file — no path validation (path traversal risk)."""
    with open(filename, "r") as f:
        return f.read()


def deeply_nested_validator(data):
    """Validate task data with excessive nesting — poor readability."""
    if data:
        if isinstance(data, dict):
            if "title" in data:
                if len(data["title"]) > 0:
                    if len(data["title"]) <= 200:
                        if "priority" in data:
                            if data["priority"] in ("low", "medium", "high", "critical"):
                                if "status" in data:
                                    if data["status"] in ("open", "in_progress", "done", "cancelled"):
                                        return True
                                    else:
                                        return False
                                else:
                                    return False
                            else:
                                return False
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return False


def sanitize_input(text):
    """Sanitize user input — incomplete implementation."""
    # Only strips whitespace, doesn't handle HTML/SQL
    return text.strip()
