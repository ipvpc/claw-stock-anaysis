from __future__ import annotations

import os
import time
from typing import Any

import requests

from postgres_cache import PostgresCache


SEC_UA = os.getenv("SEC_USER_AGENT", "stock-analysis/0.1 (contact: you@example.com)")


class SecClient:
    def __init__(self):
        self.cache = PostgresCache()

    def company_facts(self, cik: str, *, ttl_seconds: int = 7 * 86400) -> dict[str, Any]:
        key = f"sec:companyfacts:{cik}"
        cached = self.cache.get(key, ttl_seconds=ttl_seconds)
        if cached is not None:
            return cached

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        self.cache.set(key, data)
        # be kind to SEC
        time.sleep(0.12)
        return data
