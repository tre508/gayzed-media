from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, Tuple

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "desktop-media-gui"
DB_PATH = CONFIG_DIR / "history.sqlite3"
SETTINGS_PATH = CONFIG_DIR / "settings.json"


class HistoryStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    output_path TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_row(self, url: str, title: str, status: str, output_path: str = "", error: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO downloads (url, title, status, output_path, error) VALUES (?, ?, ?, ?, ?)",
                (url, title, status, output_path, error),
            )
            conn.commit()

    def list_rows(self, limit: int = 200) -> List[Tuple]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT created_at, status, title, url, output_path, error FROM downloads ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()
