"""
SQLite database for Douyin comment dedup and reply tracking.
Mirrors douyin-creator-tools/src/lib/db.mjs + db-ops.mjs in Python.

Schema: comments (work_title, username, comment_text, reply_message,
                  comment_time, reply_count, UNIQUE constraint)
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import date

from app.logger import get_logger

logger = get_logger("douyin_db")

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "data", "douyin_comments.db")
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(_DB_PATH)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                work_title    TEXT NOT NULL,
                username      TEXT NOT NULL,
                comment_text  TEXT NOT NULL,
                reply_message TEXT,
                comment_time  TEXT NOT NULL DEFAULT '2026-01-01',
                reply_count   INTEGER NOT NULL DEFAULT 0,
                UNIQUE(work_title, username, comment_text)
            )
        """)
        for col, t in [("comment_time", "TEXT NOT NULL DEFAULT '2026-01-01'"),
                       ("reply_count", "INTEGER NOT NULL DEFAULT 0")]:
            try:
                _local.conn.execute(f"ALTER TABLE comments ADD COLUMN {col} {t}")
            except sqlite3.OperationalError:
                pass
        _local.conn.commit()
    return _local.conn


def upsert_comments(work_title: str, comments: list[dict]) -> None:
    if not work_title or not comments:
        return
    conn = _get_conn()
    today = date.today().isoformat()
    for c in comments:
        username = c.get("username", "")
        comment_text = c.get("commentText", c.get("comment_text", ""))
        reply_message = c.get("replyMessage", c.get("reply_message"))
        comment_time = c.get("commentTime", c.get("comment_time", today))
        if not username or not comment_text:
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO comments (work_title, username, comment_text, "
                "reply_message, comment_time) VALUES (?,?,?,?,?)",
                (work_title, username, comment_text, None, comment_time))
            if reply_message:
                conn.execute(
                    "UPDATE comments SET reply_message=? "
                    "WHERE work_title=? AND username=? AND comment_text=?",
                    (reply_message, work_title, username, comment_text))
        except Exception as e:
            logger.warning(f"upsert_comments error: {e}")
    conn.commit()


def get_reply_count_map(work_title: str, comments: list[dict]) -> dict[str, int]:
    if not work_title or not comments:
        return {}
    conn = _get_conn()
    result: dict[str, int] = {}
    for c in comments:
        username = c.get("username", "")
        comment_text = c.get("commentText", c.get("comment_text", ""))
        if not username or not comment_text:
            continue
        row = conn.execute(
            "SELECT reply_count FROM comments "
            "WHERE work_title=? AND username=? AND comment_text=?",
            (work_title, username, comment_text)).fetchone()
        key = f"{username}|||{comment_text}"
        result[key] = row[0] if row else 0
    return result


def increment_reply_count(work_title: str, username: str, comment_text: str) -> int:
    if not work_title or not username or not comment_text:
        return 0
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE comments SET reply_count=reply_count+1 "
        "WHERE work_title=? AND username=? AND comment_text=?",
        (work_title, username, comment_text))
    conn.commit()
    return cur.rowcount


def get_user_history(usernames: list[str]) -> dict[str, list[dict]]:
    if not usernames:
        return {}
    unique = list(dict.fromkeys(u for u in usernames if u))
    if not unique:
        return {}
    conn = _get_conn()
    placeholders = ",".join("?" for _ in unique)
    rows = conn.execute(
        f"SELECT username, comment_text, comment_time, work_title "
        f"FROM comments WHERE username IN ({placeholders}) "
        f"ORDER BY comment_time DESC, id DESC",
        unique).fetchall()
    result: dict[str, list[dict]] = {}
    for row in rows:
        u = row[0]
        if u not in result:
            result[u] = []
        result[u].append({"date": row[2], "text": row[1], "work": row[3]})
    return result


def close_db() -> None:
    if hasattr(_local, "conn") and _local.conn is not None:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None
