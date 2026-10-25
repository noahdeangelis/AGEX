import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "data" / "chats.db"

# Storing the model just in case if it comes useful in the fututre
# it's currently not very useful.
class ChatStorage:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    model TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (chat_id)
                        REFERENCES chats(id) ON DELETE CASCADE
                )
            """)

    def create_chat(self, title="New chat", model=None):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "INSERT INTO chats (title, model, updated_at) VALUES (?, ?, ?)",
                (title, model, self._now())
            )
            return cursor.lastrowid

    def save_message(self, chat_id, message):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (chat_id, data) VALUES (?, ?)",
                (chat_id, json.dumps(message, ensure_ascii=False))
            )
            conn.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?",
                (self._now(), chat_id)
            )

    def load_messages(self, chat_id):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT data FROM messages WHERE chat_id = ? ORDER BY id",
                (chat_id,)
            ).fetchall()

        return [json.loads(row[0]) for row in rows]

    def list_chats(self):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, title, model, updated_at FROM chats ORDER BY updated_at DESC"
            ).fetchall()

        return [
            {
                "id": row[0],
                "title": row[1],
                "model": row[2],
                "updated_at": row[3]
            }
            for row in rows
        ]

    def delete_chat(self, chat_id):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            cursor = conn.execute(
                "DELETE FROM chats WHERE id = ?",
                (chat_id,)
            )

            return cursor.rowcount > 0

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()