import os
import sqlite3
from typing import Optional


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.connection: Optional[sqlite3.Connection] = None

    def setup(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.connection = sqlite3.connect(self.path)
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
        cursor = self.connection.execute(
            "SELECT 1 FROM articles WHERE id = ? LIMIT 1", (article_id,)
        )
        return cursor.fetchone() is not None

    def save_article(self, article_id: str, title: str = "", published_at: str = "") -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO articles (id, title, published_at) VALUES (?, ?, ?)",
            (article_id, title, published_at),
        )
        self.connection.commit()

    def close(self) -> None:
        if self.connection:
            self.connection.close()
