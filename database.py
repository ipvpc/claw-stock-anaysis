from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CacheRow:
    key: str
    fetched_at: float
    payload_json: str


class SqliteCache:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                create table if not exists cache (
                  key text primary key,
                  fetched_at real not null,
                  payload_json text not null
                )
                """
            )
            conn.commit()

    def get(self, key: str, *, ttl_seconds: int) -> Any | None:
        now = time.time()
        with self._conn() as conn:
            row = conn.execute("select key,fetched_at,payload_json from cache where key=?", (key,)).fetchone()
            if not row:
                return None
            fetched_at = float(row["fetched_at"])
            if now - fetched_at > ttl_seconds:
                return None
            return json.loads(row["payload_json"])

    def set(self, key: str, payload: Any) -> None:
        with self._conn() as conn:
            conn.execute(
                "insert into cache(key,fetched_at,payload_json) values(?,?,?) on conflict(key) do update set fetched_at=excluded.fetched_at, payload_json=excluded.payload_json",
                (key, time.time(), json.dumps(payload)),
            )
            conn.commit()
