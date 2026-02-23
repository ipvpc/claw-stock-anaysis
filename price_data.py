from __future__ import annotations

import os
from typing import Dict

import pandas as pd
import yfinance as yf

from postgres_cache import PostgresCache


class PriceDataManager:
    def __init__(self):
        self.cache = PostgresCache()

    def get_daily_prices(self, ticker: str, *, days: int = 90, ttl_seconds: int = 86400, force_refresh: bool = False) -> pd.DataFrame:
        key = f"prices:{ticker}:{days}d"
        if not force_refresh:
            cached = self.cache.get(key, ttl_seconds=ttl_seconds)
            if cached is not None:
                df = pd.DataFrame(cached)
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                    df = df.set_index("timestamp")
                return df

        stock = yf.Ticker(ticker)
        df = stock.history(period=f"{days}d")
        if df is None or df.empty:
            raise RuntimeError(f"No data for {ticker}")

        # store as records with an explicit timestamp column (robust)
        df_out = df.reset_index().rename(columns={"index": "timestamp"})
        df_out["timestamp"] = df_out["timestamp"].astype(str)
        payload = df_out.to_dict(orient="records")
        self.cache.set(key, payload)

        df2 = pd.DataFrame(payload)
        df2["timestamp"] = pd.to_datetime(df2["timestamp"], errors="coerce")
        df2 = df2.set_index("timestamp")
        return df2

    def batch_fetch_prices(self, tickers: list[str], *, days: int = 90, workers: int = 10) -> Dict[str, pd.DataFrame]:
        """Fetch many tickers in parallel.

        Note: yfinance may throttle; caching helps a lot.
        """

        from concurrent.futures import ThreadPoolExecutor, as_completed

        out: Dict[str, pd.DataFrame] = {}
        workers = max(1, min(50, int(workers)))

        def one(t: str):
            return t, self.get_daily_prices(t, days=days)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(one, t) for t in tickers]
            for f in as_completed(futs):
                try:
                    t, df = f.result()
                    out[t] = df
                except Exception:
                    continue

        return out
