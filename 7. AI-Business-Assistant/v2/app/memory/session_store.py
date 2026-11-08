"""Session store for conversation history, TTL eviction, and user-isolated memory.

Specifications:
- Spec §5 T2, T7
- TC-T2-07: TTL cutoff, expired purge, and user erasure
- Review Focus #1: Strict cross-user isolation across all operations
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from db.apply_db import get_app_engine


class TurnRecord(BaseModel):
    """Data transfer object for a single conversation turn in app.chat_turn."""

    id: int
    session_id: str
    user_id: str
    query: str
    standalone_query: str | None = None
    intent: str | None = None
    kpi_keys: list[str] = Field(default_factory=list)
    sql_query: str | None = None
    answer: dict[str, Any] | None = None
    confidence: float | None = None
    request_id: str | None = None
    created_at: datetime


class SessionStore:
    """PostgreSQL-backed multi-turn session memory with user isolation and TTL enforcement."""

    def __init__(
        self,
        engine: Engine | None = None,
        data_profile: str = "real",
        ttl_days: int = 30,
    ) -> None:
        self.data_profile = data_profile
        self.ttl_days = ttl_days
        self.engine = engine if engine is not None else get_app_engine(profile=data_profile)

    def add_turn(
        self,
        session_id: str,
        user_id: str,
        query: str,
        standalone_query: str | None = None,
        intent: str | None = None,
        kpi_keys: list[str] | None = None,
        sql_query: str | None = None,
        answer: dict[str, Any] | None = None,
        confidence: float | None = None,
        request_id: str | None = None,
        created_at: datetime | None = None,
    ) -> int:
        """Insert a conversation turn into app.chat_turn. Returns the generated primary key id."""
        ans_json = json.dumps(answer, default=str) if answer is not None else None
        kpis = list(kpi_keys) if kpi_keys is not None else []

        stmt = sa.text("""
            INSERT INTO app.chat_turn (
                session_id, user_id, query, standalone_query, intent,
                kpi_keys, sql_query, answer, confidence, request_id, created_at
            ) VALUES (
                :session_id, :user_id, :query, :standalone_query, :intent,
                :kpi_keys, :sql_query, CAST(:answer AS jsonb), :confidence, :request_id, COALESCE(:created_at, now())
            ) RETURNING id;
        """)

        with self.engine.begin() as conn:
            turn_id = conn.execute(
                stmt,
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "query": query,
                    "standalone_query": standalone_query,
                    "intent": intent,
                    "kpi_keys": kpis,
                    "sql_query": sql_query,
                    "answer": ans_json,
                    "confidence": confidence,
                    "request_id": request_id,
                    "created_at": created_at,
                },
            ).scalar()

        return int(turn_id)

    def get_history(
        self,
        session_id: str,
        user_id: str,
        n: int = 5,
        now: datetime | None = None,
    ) -> list[TurnRecord]:
        """Retrieve chronological (oldest -> newest) non-expired turns matching session_id AND user_id.

        Review Focus #1: Enforces user_id filtering to guarantee zero cross-user leakage.
        """
        current_time = now or datetime.now(timezone.utc)
        cutoff = current_time - timedelta(days=self.ttl_days)

        stmt = sa.text("""
            SELECT id, session_id, user_id, query, standalone_query, intent,
                   kpi_keys, sql_query, answer, confidence, request_id, created_at
            FROM (
                SELECT id, session_id, user_id, query, standalone_query, intent,
                       kpi_keys, sql_query, answer, confidence, request_id, created_at
                FROM app.chat_turn
                WHERE session_id = :session_id
                  AND user_id = :user_id
                  AND created_at >= :cutoff
                ORDER BY created_at DESC, id DESC
                LIMIT :n
            ) sub
            ORDER BY created_at ASC, id ASC;
        """)

        with self.engine.connect() as conn:
            rows = conn.execute(
                stmt,
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "cutoff": cutoff,
                    "n": n,
                },
            ).fetchall()

        records: list[TurnRecord] = []
        for r in rows:
            ans = r.answer
            if isinstance(ans, str):
                try:
                    ans = json.loads(ans)
                except Exception:
                    pass
            records.append(
                TurnRecord(
                    id=r.id,
                    session_id=r.session_id,
                    user_id=r.user_id,
                    query=r.query,
                    standalone_query=r.standalone_query,
                    intent=r.intent,
                    kpi_keys=r.kpi_keys or [],
                    sql_query=r.sql_query,
                    answer=ans,
                    confidence=r.confidence,
                    request_id=r.request_id,
                    created_at=r.created_at,
                )
            )
        return records

    def list_user_turns(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 50,
        now: datetime | None = None,
    ) -> list[TurnRecord]:
        """List user's turns (newest -> oldest) strictly isolated by user_id."""
        current_time = now or datetime.now(timezone.utc)
        cutoff = current_time - timedelta(days=self.ttl_days)

        if session_id:
            stmt = sa.text("""
                SELECT id, session_id, user_id, query, standalone_query, intent,
                       kpi_keys, sql_query, answer, confidence, request_id, created_at
                FROM app.chat_turn
                WHERE user_id = :user_id
                  AND session_id = :session_id
                  AND created_at >= :cutoff
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
            """)
            params = {
                "user_id": user_id,
                "session_id": session_id,
                "cutoff": cutoff,
                "limit": limit,
            }
        else:
            stmt = sa.text("""
                SELECT id, session_id, user_id, query, standalone_query, intent,
                       kpi_keys, sql_query, answer, confidence, request_id, created_at
                FROM app.chat_turn
                WHERE user_id = :user_id
                  AND created_at >= :cutoff
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
            """)
            params = {
                "user_id": user_id,
                "cutoff": cutoff,
                "limit": limit,
            }

        with self.engine.connect() as conn:
            rows = conn.execute(stmt, params).fetchall()

        records: list[TurnRecord] = []
        for r in rows:
            ans = r.answer
            if isinstance(ans, str):
                try:
                    ans = json.loads(ans)
                except Exception:
                    pass
            records.append(
                TurnRecord(
                    id=r.id,
                    session_id=r.session_id,
                    user_id=r.user_id,
                    query=r.query,
                    standalone_query=r.standalone_query,
                    intent=r.intent,
                    kpi_keys=r.kpi_keys or [],
                    sql_query=r.sql_query,
                    answer=ans,
                    confidence=r.confidence,
                    request_id=r.request_id,
                    created_at=r.created_at,
                )
            )
        return records

    def purge_expired(
        self,
        ttl_days: int | None = None,
        now: datetime | None = None,
    ) -> int:
        """Purge turns older than ttl_days from app.chat_turn. Returns count of deleted rows."""
        effective_ttl = ttl_days if ttl_days is not None else self.ttl_days
        current_time = now or datetime.now(timezone.utc)
        cutoff = current_time - timedelta(days=effective_ttl)

        stmt = sa.text("DELETE FROM app.chat_turn WHERE created_at < :cutoff;")
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"cutoff": cutoff})
            return int(res.rowcount or 0)

    def delete_user_history(
        self,
        user_id: str,
        session_id: str | None = None,
    ) -> int:
        """Delete all turns for user_id (and optionally session_id). Returns count of deleted rows.

        Review Focus #1: Strictly scoped to the specified user_id.
        """
        if session_id:
            stmt = sa.text("""
                DELETE FROM app.chat_turn
                WHERE user_id = :user_id AND session_id = :session_id;
            """)
            params = {"user_id": user_id, "session_id": session_id}
        else:
            stmt = sa.text("""
                DELETE FROM app.chat_turn
                WHERE user_id = :user_id;
            """)
            params = {"user_id": user_id}

        with self.engine.begin() as conn:
            res = conn.execute(stmt, params)
            return int(res.rowcount or 0)
