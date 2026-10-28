"""Работа с SQLite: пользователи, документы, кэш результатов."""
import sqlite3

DB_PATH = "bot.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    pages INTEGER,
    chunks INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS results (
    doc_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, kind)
);
"""


def _connect() -> sqlite3.Connection:
    """Открывает соединение; строки читаются как словари."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет."""
    with _connect() as conn:
        conn.executescript(SCHEMA)


def add_document(user_id: int, filename: str, path: str,
                 pages: int, chunks: int) -> int:
    """Сохраняет документ и возвращает его doc_id."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        cur = conn.execute(
            "INSERT INTO documents (user_id, filename, path, pages, chunks) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, filename, path, pages, chunks),
        )
        return cur.lastrowid


def list_documents(user_id: int) -> list[dict]:
    """Все документы пользователя, новые сверху."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY doc_id DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(doc_id: int) -> dict | None:
    """Один документ по doc_id или None, если такого нет."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def get_cached(doc_id: int, kind: str) -> str | None:
    """Готовый результат (summary / cards / cheatsheet) или None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT text FROM results WHERE doc_id = ? AND kind = ?",
            (doc_id, kind),
        ).fetchone()
    return row["text"] if row else None


def save_cached(doc_id: int, kind: str, text: str) -> None:
    """Сохраняет результат; старый для той же пары заменяется."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO results (doc_id, kind, text) "
            "VALUES (?, ?, ?)",
            (doc_id, kind, text),
        )


def delete_document(doc_id: int) -> None:
    """Удаляет документ и его кэш. Нужна, если загрузка сорвалась."""
    with _connect() as conn:
        conn.execute("DELETE FROM results WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))

