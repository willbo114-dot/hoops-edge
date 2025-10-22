"""SQLite-backed TTL cache."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            expires REAL NOT NULL
        )
        """
    )
    conn.commit()


class TTLCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        _ensure_tables(self.conn)

    def get(self, key: str) -> Optional[Any]:
        cur = self.conn.execute("SELECT value, expires FROM cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        value, expires = row
        if expires < time.time():
            self.delete(key)
            return None
        return json.loads(value)

    def set(self, key: str, value: Any, ttl: float) -> None:
        expires = time.time() + ttl
        self.conn.execute(
            "REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
            (key, json.dumps(value), expires),
        )
        self.conn.commit()

    def delete(self, key: str) -> None:
        self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
