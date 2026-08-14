import json
import os
import sqlite3
import threading
from typing import Optional

from config import DB_PATH, MAX_HISTORY


class Database:
    def __init__(self, path: str = DB_PATH):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._init()

    def _init(self):
        with self.lock, self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    ai_mode TEXT NOT NULL DEFAULT 'nobody',
                    group_mode TEXT NOT NULL DEFAULT 'nobody'
                );
                CREATE TABLE IF NOT EXISTS ai_users (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(chat_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS allowed_ai_users (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS group_managers (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY(chat_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS user_restrictions (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    muted INTEGER NOT NULL DEFAULT 0,
                    banned INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(chat_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    history TEXT NOT NULL DEFAULT '[]',
                    last_ai_message_id INTEGER,
                    PRIMARY KEY(chat_id, user_id)
                );
                """
            )

    def ensure_group(self, chat_id: int):
        with self.lock, self.conn:
            self.conn.execute("INSERT OR IGNORE INTO groups(chat_id) VALUES(?)", (chat_id,))

    def get_group(self, chat_id: int):
        self.ensure_group(chat_id)
        with self.lock:
            return self.conn.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,)).fetchone()

    def set_ai_mode(self, chat_id: int, mode: str):
        self.ensure_group(chat_id)
        with self.lock, self.conn:
            self.conn.execute("UPDATE groups SET ai_mode=? WHERE chat_id=?", (mode, chat_id))

    def set_group_mode(self, chat_id: int, mode: str):
        self.ensure_group(chat_id)
        with self.lock, self.conn:
            self.conn.execute("UPDATE groups SET group_mode=? WHERE chat_id=?", (mode, chat_id))

    def allow_ai_user(self, chat_id: int, user_id: int):
        with self.lock, self.conn:
            self.conn.execute("INSERT OR IGNORE INTO allowed_ai_users(chat_id,user_id) VALUES(?,?)", (chat_id, user_id))

    def clear_ai_users(self, chat_id: int):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM allowed_ai_users WHERE chat_id=?", (chat_id,))

    def is_ai_explicitly_allowed(self, chat_id: int, user_id: int) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT 1 FROM allowed_ai_users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            return row is not None

    def allow_group_manager(self, chat_id: int, user_id: int):
        with self.lock, self.conn:
            self.conn.execute("INSERT OR IGNORE INTO group_managers(chat_id,user_id) VALUES(?,?)", (chat_id, user_id))

    def clear_group_managers(self, chat_id: int):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM group_managers WHERE chat_id=?", (chat_id,))

    def is_group_manager(self, chat_id: int, user_id: int) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT 1 FROM group_managers WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            return row is not None

    def set_enabled(self, chat_id: int, user_id: int, enabled: bool):
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO ai_users(chat_id,user_id,enabled) VALUES(?,?,?) "
                "ON CONFLICT(chat_id,user_id) DO UPDATE SET enabled=excluded.enabled",
                (chat_id, user_id, int(enabled)),
            )

    def is_enabled(self, chat_id: int, user_id: int) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT enabled FROM ai_users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            return bool(row and row[0])

    def get_restriction(self, chat_id: int, user_id: int):
        with self.lock:
            row = self.conn.execute("SELECT muted,banned FROM user_restrictions WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            if not row:
                return False, False
            return bool(row[0]), bool(row[1])

    def set_restriction(self, chat_id: int, user_id: int, muted: Optional[bool] = None, banned: Optional[bool] = None):
        old_m, old_b = self.get_restriction(chat_id, user_id)
        new_m = old_m if muted is None else muted
        new_b = old_b if banned is None else banned
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO user_restrictions(chat_id,user_id,muted,banned) VALUES(?,?,?,?) "
                "ON CONFLICT(chat_id,user_id) DO UPDATE SET muted=excluded.muted,banned=excluded.banned",
                (chat_id, user_id, int(new_m), int(new_b)),
            )
        return old_m, old_b, new_m, new_b

    def get_history(self, chat_id: int, user_id: int):
        with self.lock:
            row = self.conn.execute("SELECT history FROM conversations WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            if not row:
                return []
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return []

    def save_history(self, chat_id: int, user_id: int, history, last_ai_message_id: Optional[int] = None):
        history = history[-MAX_HISTORY:]
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO conversations(chat_id,user_id,history,last_ai_message_id) VALUES(?,?,?,?) "
                "ON CONFLICT(chat_id,user_id) DO UPDATE SET history=excluded.history,last_ai_message_id=excluded.last_ai_message_id",
                (chat_id, user_id, json.dumps(history, ensure_ascii=False), last_ai_message_id),
            )

    def get_last_ai_message_id(self, chat_id: int, user_id: int):
        with self.lock:
            row = self.conn.execute("SELECT last_ai_message_id FROM conversations WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            return row[0] if row else None

    def reset_conversation(self, chat_id: int, user_id: int):
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM conversations WHERE chat_id=? AND user_id=?", (chat_id, user_id))
