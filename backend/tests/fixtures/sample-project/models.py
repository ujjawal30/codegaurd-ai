"""
TaskMaster — Data models.
"""

import os
import sys
import json
import re
import sqlite3
from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    role: str = "developer"


class Task:
    def __init__(self, id, title, description="", priority="low",
                 status="open", user_id=None, created_at=None,
                 updated_at=None, deadline=None, tags=None):
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.user_id = user_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.deadline = deadline
        self.tags = tags or []

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "tags": self.tags,
        }

    def is_overdue(self):
        from datetime import datetime
        if self.deadline:
            return datetime.fromisoformat(self.deadline) < datetime.now()
        return False


class TaskRepository:
    def __init__(self, db_path="tasks.db"):
        self.db_path = db_path

    def get_all(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def find_by_id(self, task_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(f"SELECT * FROM tasks WHERE id = {task_id}")
        row = cursor.fetchone()
        conn.close()
        return row

    def delete(self, task_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"DELETE FROM tasks WHERE id = {task_id}")
        conn.commit()
        conn.close()
