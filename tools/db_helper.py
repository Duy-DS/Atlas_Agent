import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

class DatabaseHelper:
    def __init__(self, db_path: Path = Path("data/aawb_storage.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_default_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_default_tables(self):
        """Initializes default tables for caching LLM responses and logging execution steps."""
        schema = """
        CREATE TABLE IF NOT EXISTS llm_cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qid TEXT,
            action TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        conn = self._get_connection()
        try:
            conn.executescript(schema)
            conn.commit()
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> int:
        """Executes a write query (INSERT/UPDATE/DELETE) and returns affected row count."""
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.rowcount
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a read query and returns a list of dictionaries."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Executes a read query and returns the first row as a dictionary, or None."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # --- Cache helpers (Very useful to avoid duplicate LLM costs during prompt tuning) ---
    def get_cache(self, key: str) -> Optional[str]:
        row = self.fetch_one("SELECT value FROM llm_cache WHERE key = ?", (key,))
        return row["value"] if row else None

    def set_cache(self, key: str, value: str):
        self.execute(
            "INSERT OR REPLACE INTO llm_cache (key, value, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )

    def clear_cache(self):
        self.execute("DELETE FROM llm_cache")
