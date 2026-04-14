"""SQLite 持久化服务."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from loguru import logger

from app.config import config


class DatabaseService:
    """负责 SQLite 连接、建表和基础查询."""

    def __init__(self) -> None:
        self.db_path = Path(config.database_path)
        self._initialized = False
        self._lock = Lock()

    def initialize(self) -> None:
        """初始化数据库和基础表结构."""
        with self._lock:
            if self._initialized:
                return

            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with self.get_connection() as conn:
                conn.executescript(
                    """
                    PRAGMA journal_mode = WAL;
                    PRAGMA foreign_keys = ON;

                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        password_salt TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        last_intent TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    );

                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        intent TEXT,
                        route TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    );

                    CREATE TABLE IF NOT EXISTS workflow_runs (
                        run_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        workflow_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        input_text TEXT,
                        result_summary TEXT,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        duration_ms INTEGER,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    );

                    CREATE TABLE IF NOT EXISTS tool_call_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        workflow_run_id TEXT,
                        tool_name TEXT NOT NULL,
                        server_name TEXT,
                        status TEXT NOT NULL,
                        latency_ms INTEGER,
                        input_payload TEXT,
                        output_payload TEXT,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                        FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(run_id)
                    );

                    CREATE TABLE IF NOT EXISTS document_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        source_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )

                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts
                        USING fts5(
                            content,
                            chunk_id UNINDEXED,
                            source_path UNINDEXED,
                            file_name UNINDEXED,
                            tokenize = 'unicode61 porter'
                        );
                        """
                    )
                except sqlite3.OperationalError as exc:
                    logger.warning(f"SQLite FTS5 初始化失败，将跳过稀疏检索: {exc}")

            self._initialized = True
            logger.info(f"SQLite 数据库初始化完成: {self.db_path}")

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """获取数据库连接."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def health_check(self) -> bool:
        """检查数据库可用性."""
        try:
            self.initialize()
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as exc:
            logger.error(f"SQLite 健康检查失败: {exc}")
            return False

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> None:
        """执行写操作."""
        self.initialize()
        with self.get_connection() as conn:
            conn.execute(sql, parameters)

    def fetch_one(self, sql: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """查询单行."""
        self.initialize()
        with self.get_connection() as conn:
            row = conn.execute(sql, parameters).fetchone()
        return dict(row) if row else None

    def fetch_all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """查询多行."""
        self.initialize()
        with self.get_connection() as conn:
            rows = conn.execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    def upsert_document_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """批量写入文档切片及 FTS 索引."""
        if not chunks:
            return

        self.initialize()
        with self.get_connection() as conn:
            for chunk in chunks:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO document_chunks (
                        chunk_id, source_path, file_name, content, metadata_json, content_hash, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk["chunk_id"],
                        chunk["source_path"],
                        chunk["file_name"],
                        chunk["content"],
                        json.dumps(chunk["metadata"], ensure_ascii=False),
                        chunk["content_hash"],
                        chunk["created_at"],
                    ),
                )
                try:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO document_chunks_fts (
                            rowid, content, chunk_id, source_path, file_name
                        )
                        VALUES (
                            (SELECT rowid FROM document_chunks WHERE chunk_id = ?),
                            ?, ?, ?, ?
                        )
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["content"],
                            chunk["chunk_id"],
                            chunk["source_path"],
                            chunk["file_name"],
                        ),
                    )
                except sqlite3.OperationalError:
                    # FTS5 不可用时跳过即可
                    pass

    def delete_document_chunks_by_source(self, source_path: str) -> None:
        """删除某个源文件对应的切片."""
        self.initialize()
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT rowid FROM document_chunks WHERE source_path = ?",
                (source_path,),
            ).fetchall()
            conn.execute("DELETE FROM document_chunks WHERE source_path = ?", (source_path,))
            try:
                for row in rows:
                    conn.execute("DELETE FROM document_chunks_fts WHERE rowid = ?", (row["rowid"],))
            except sqlite3.OperationalError:
                pass

    def search_sparse_documents(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """执行基于 FTS5 的稀疏检索."""
        self.initialize()
        sql = """
        SELECT
            chunk_id,
            source_path,
            file_name,
            content,
            bm25(document_chunks_fts) AS score
        FROM document_chunks_fts
        WHERE document_chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """
        try:
            return self.fetch_all(sql, (query, top_k))
        except sqlite3.OperationalError as exc:
            logger.warning(f"稀疏检索失败，跳过 FTS5 查询: {exc}")
            return []


database_service = DatabaseService()
