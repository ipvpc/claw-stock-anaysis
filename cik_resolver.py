from __future__ import annotations

import os
import time
from typing import Any

import requests

from postgres_cache import PostgresCache


TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_UA = os.getenv("SEC_USER_AGENT", "stock-analysis/0.1 (contact: you@example.com)")


class CikResolver:
    def __init__(self):
        self.cache = PostgresCache()

    def _load_map(self) -> dict[str, str]:
        key = "sec:ticker_map:v1"
        cached = self.cache.get(key, ttl_seconds=7 * 86400)
        if cached is not None:
            return cached

        resp = requests.get(TICKER_MAP_URL, headers={"User-Agent": SEC_UA}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        m: dict[str, str] = {}
        for _, row in data.items():
            t = str(row.get("ticker") or "").upper().strip()
            cik = str(row.get("cik_str") or "").strip()
            if t and cik:
                m[t] = cik.zfill(10)
        self.cache.set(key, m)
        time.sleep(0.12)
        return m

    def cik_for_ticker(self, ticker: str) -> str | None:
        t = ticker.upper().strip()
        m = self._load_map()
        return m.get(t)
