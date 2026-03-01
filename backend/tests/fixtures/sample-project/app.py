"""
TaskMaster — A simple task management API.

WARNING: This file contains intentional security and quality issues
for testing CodeGuard AI's detection pipeline.
"""

import sqlite3
import os
import hashlib
import json
import sys
from datetime import datetime

# ── Hardcoded secret ────────────────────────────────────────────
SECRET_KEY = "super-secret-key-12345"
DATABASE_URL = "sqlite:///tasks.db"
API_KEY = "sk-1234567890abcdef"


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect("tasks.db")
    conn.row_factory = sqlite3.Row
    return conn


# ── SQL Injection vulnerability ─────────────────────────────────
def get_user(user_id):
    """Fetch user by ID — vulnerable to SQL injection."""
    db = get_db()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # nosec: intentional
    cursor = db.execute(query)
    return cursor.fetchone()


def search_tasks(keyword):
    """Search tasks by keyword — vulnerable to SQL injection."""
    db = get_db()
    query = f"SELECT * FROM tasks WHERE title LIKE '%{keyword}%'"  # nosec
    return db.execute(query).fetchall()


# ── High cyclomatic complexity ──────────────────────────────────
def process_task(task_data, user, options=None):
    """Process a task with many branches — intentionally complex."""
    if not task_data:
        return {"error": "No data"}

    if "title" not in task_data:
        return {"error": "Missing title"}

    if len(task_data["title"]) > 200:
        return {"error": "Title too long"}

    if user is None:
        return {"error": "No user"}

    if not user.get("is_active"):
        return {"error": "User inactive"}

    if user.get("role") == "admin":
        priority = "high"
    elif user.get("role") == "manager":
        priority = "medium"
    elif user.get("role") == "developer":
        if options and options.get("urgent"):
            priority = "high"
        else:
            priority = "low"
    else:
        priority = "low"

    if options:
        if options.get("notify"):
            if options.get("notify_email"):
                send_email(options["notify_email"], task_data["title"])
            elif options.get("notify_slack"):
                send_slack(options["notify_slack"], task_data["title"])
            else:
                print("No notification method specified")

        if options.get("deadline"):
            try:
                deadline = datetime.fromisoformat(options["deadline"])
                if deadline < datetime.now():
                    return {"error": "Deadline in the past"}
            except ValueError:
                return {"error": "Invalid deadline format"}

    status = "open"
    if task_data.get("auto_start"):
        status = "in_progress"

    result = {
        "title": task_data["title"],
        "priority": priority,
        "status": status,
        "created_by": user["id"],
        "created_at": datetime.now().isoformat(),
    }

    db = get_db()
    db.execute(
        f"INSERT INTO tasks (title, priority, status, user_id) VALUES ('{result['title']}', '{priority}', '{status}', {user['id']})"
    )
    db.commit()

    return result


def send_email(to, subject):
    """Stub: send email notification."""
    pass


def send_slack(channel, message):
    """Stub: send Slack notification."""
    pass


# ── Eval usage (security risk) ──────────────────────────────────
def evaluate_expression(expr):
    """Evaluate a mathematical expression — uses eval (dangerous)."""
    return eval(expr)


# ── Weak hashing ────────────────────────────────────────────────
def hash_password(password):
    """Hash a password using MD5 — weak algorithm."""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password, hashed):
    """Verify password against MD5 hash."""
    return hashlib.md5(password.encode()).hexdigest() == hashed
