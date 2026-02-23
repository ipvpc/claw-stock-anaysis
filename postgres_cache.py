from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import psycopg


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else default


def db_dsn() -> str:
    dsn = _env("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")
    return dsn


@dataclass(frozen=True)
class CacheRow:
    key: str
    fetched_at: float
    payload: Any


class PostgresCache:
    def __init__(self):
        self._migrate()

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(db_dsn(), autocommit=True)

    def _migrate(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists cache_kv (
                      key text primary key,
                      fetched_at double precision not null,
                      payload jsonb not null
                    );
                    """
                )

    def get(self, key: str, *, ttl_seconds: int) -> Any | None:
        now = time.time()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select fetched_at, payload from cache_kv where key=%s", (key,))
                row = cur.fetchone()
                if not row:
                    return None
                fetched_at = float(row[0])
                if now - fetched_at > ttl_seconds:
                    return None
                return row[1]

    def set(self, key: str, payload: Any) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into cache_kv(key, fetched_at, payload)
                    values (%s, %s, %s::jsonb)
                    on conflict (key) do update set fetched_at=excluded.fetched_at, payload=excluded.payload
                    """,
                    (key, time.time(), json.dumps(payload)),
                )
