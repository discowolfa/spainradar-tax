import os
import sqlite3
import threading
from typing import Optional


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.connection: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def setup(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    published_at TEXT
                )
                """
            )
            self.connection.commit()

    def has_article(self, article_id: str) -> bool:
        with self._lock:
            cursor = self.connection.execute(
                "SELECT 1 FROM articles WHERE id = ? LIMIT 1", (article_id,)
            )
            return cursor.fetchone() is not None

    def save_article(self, article_id: str, title: str = "", published_at: str = "") -> None:
        with self._lock:
            self.connection.execute(
                "INSERT OR IGNORE INTO articles (id, title, published_at) VALUES (?, ?, ?)",
                (article_id, title, published_at),
            )
            self.connection.commit()

    def count_articles(self) -> int:
        with self._lock:
            cursor = self.connection.execute("SELECT COUNT(*) FROM articles")
            return int(cursor.fetchone()[0])

    def close(self) -> None:
        with self._lock:
            if self.connection:
                self.connection.close()
                self.connection = None
