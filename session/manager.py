"""Session management for SQLAgent."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Set
import json
import asyncpg

# 在内存中跟踪已创建但尚未保存到数据库的会话ID
_pending_sessions: Set[str] = set()


@dataclass
class SessionMetadata:
    """Session metadata stored in database."""

    thread_id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionManager:
    """Manages SQLAgent sessions using PostgreSQL."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def init_tables(self) -> None:
        """Initialize session tables if not exists."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    thread_id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    title VARCHAR(256) NOT NULL DEFAULT '新会话',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
                ON agent_sessions(user_id);

                CREATE INDEX IF NOT EXISTS idx_sessions_updated 
                ON agent_sessions(updated_at DESC);
                
                CREATE TABLE IF NOT EXISTS agent_messages (
                    id SERIAL PRIMARY KEY,
                    thread_id VARCHAR(64) NOT NULL,
                    role VARCHAR(10) NOT NULL,
                    content JSONB NOT NULL,
                    message_info JSONB,
                    token_info JSONB,
                    error_info JSONB,
                    request_time TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_messages_thread_id 
                ON agent_messages(thread_id);
            """)

    def create_thread_id(self, user_id: str) -> str:
        """Generate a unique permanent thread_id."""
        return f"{user_id}_{uuid.uuid4().hex[:12]}"

    async def create_session(
            self,
            user_id: str,
            title: Optional[str] = None
    ) -> SessionMetadata:
        """Create a new session metadata but don't save to DB yet."""
        thread_id = self.create_thread_id(user_id)
        title = title
        
        # 将会话ID添加到待处理集合中
        _pending_sessions.add(thread_id)

        return SessionMetadata(
            thread_id=thread_id,
            user_id=user_id,
            title=title
        )

    async def save_session_if_needed(self, thread_id: str, user_id: str, title: str) -> None:
        """Save session to database if it hasn't been saved yet."""
        if thread_id in _pending_sessions:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO agent_sessions (thread_id, user_id, title)
                       VALUES ($1, $2, $3)
                       ON CONFLICT (thread_id) DO UPDATE 
                       SET title = EXCLUDED.title, updated_at = NOW()""",
                    thread_id, user_id, title
                )
            # 从待处理集合中移除
            _pending_sessions.discard(thread_id)

    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 50
    ) -> list[SessionMetadata]:
        """Get all sessions for a user."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT thread_id, user_id, title, created_at, updated_at
                   FROM agent_sessions
                   WHERE user_id = $1
                   ORDER BY updated_at DESC
                   LIMIT $2""",
                user_id, limit
            )

        return [
            SessionMetadata(
                thread_id=row["thread_id"],
                user_id=row["user_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

    async def get_session(self, thread_id: str) -> Optional[SessionMetadata]:
        """Get a specific session by thread_id."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT thread_id, user_id, title, created_at, updated_at
                   FROM agent_sessions
                   WHERE thread_id = $1""",
                thread_id
            )

        if not row:
            return None

        return SessionMetadata(
            thread_id=row["thread_id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def update_session_title(
            self,
            thread_id: str,
            title: str
    ) -> None:
        """Update session title."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE agent_sessions 
                   SET title = $1, updated_at = NOW()
                   WHERE thread_id = $2""",
                title, thread_id
            )

    async def touch_session(self, thread_id: str) -> None:
        """Update session's updated_at timestamp."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE agent_sessions 
                   SET updated_at = NOW()
                   WHERE thread_id = $1""",
                thread_id
            )

    async def delete_session(self, thread_id: str) -> bool:
        """Delete a session (does not delete LangGraph checkpointer data)."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM agent_sessions WHERE thread_id = $1""",
                thread_id
            )

        return result != "DELETE 0"

    async def has_interaction(self, thread_id: str) -> bool:
        """Check if session has any user interaction (checks LangGraph checkpoint data)."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT 1 FROM checkpoints WHERE thread_id = $1 LIMIT 1""",
                    thread_id
                )
                return row is not None
        except Exception:
            return False

    async def save_message(self, thread_id: str, role: str, content: dict, request_timestamp: Optional[float] = None, message_info: Optional[dict] = None, token_info: Optional[dict] = None, error_info: Optional[dict] = None) -> dict:
        """Save a message to the database and return the saved message info."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO agent_messages (thread_id, role, content, request_time, message_info, token_info, error_info)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                thread_id, role, json.dumps(content), request_timestamp,
                json.dumps(message_info) if message_info is not None else None,
                json.dumps(token_info) if token_info is not None else None,
                json.dumps(error_info) if error_info is not None else None
            )

    async def get_session_messages(self, thread_id: str) -> list:
        """Get all messages for a session."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, role, content, message_info ,token_info ,error_info ,request_time ,created_at
                   FROM agent_messages
                   WHERE thread_id = $1
                   ORDER BY created_at ASC""",
                thread_id
            )

        messages = []
        for row in rows:
            message = {
                "id": str(row["id"]),
                "role": row["role"],
                "request_time": row["request_time"].isoformat() if row["created_at"] else None,
                "message_info": json.loads(row["message_info"]) if row["message_info"] else None,
                "error_info": json.loads(row["error_info"]) if row["error_info"] else None,
                "token_info": json.loads(row["token_info"]) if row["token_info"] else None,
                "content": json.loads(row["content"]) ,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            
            messages.append(message)
            
        return messages


async def create_session_manager(db_pool: asyncpg.Pool) -> SessionManager:
    """Create and initialize session manager."""
    manager = SessionManager(db_pool)
    await manager.init_tables()
    return manager