from __future__ import annotations

import pandas as pd


def williams_r(df: pd.DataFrame, *, period: int = 21) -> pd.Series:
    high = df["High"].rolling(period).max()
    low = df["Low"].rolling(period).min()
    wr = ((high - df["Close"]) / (high - low)) * -100.0
    return wr


def ema(series: pd.Series, *, period: int = 13) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()
