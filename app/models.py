import os
import sqlite3
from datetime import datetime

import bcrypt
from flask import Flask, g, current_app

# Register adapters and converters for datetime (required since Python 3.12)
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()))


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_slug TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE INDEX IF NOT EXISTS idx_comments_post_slug ON comments(post_slug);
        CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);
    """)
    db.commit()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        db_path = app.config["DATABASE_PATH"]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        init_db()


def create_user(first_name: str, last_name: str, username: str, password: str) -> None:
    db = get_db()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    db.execute(
        "INSERT INTO users (first_name, last_name, username, password_hash) VALUES (?, ?, ?, ?)",
        (first_name, last_name, username, password_hash.decode("utf-8")),
    )
    db.commit()


def get_user_by_password(password: str) -> sqlite3.Row | None:
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    for user in users:
        if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return user
    return None


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def add_comment(post_slug: str, user_id: int, content: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO comments (post_slug, user_id, content) VALUES (?, ?, ?)",
        (post_slug, user_id, content),
    )
    db.commit()


def get_comments_for_post(post_slug: str) -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        """
        SELECT c.*, u.username, u.first_name, u.last_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_slug = ?
        ORDER BY c.created_at ASC
        """,
        (post_slug,),
    ).fetchall()
