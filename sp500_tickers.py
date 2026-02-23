from __future__ import annotations

import pandas as pd

SP500_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"


def get_sp500_tickers() -> list[str]:
    df = pd.read_csv(SP500_URL)
    syms = df["Symbol"].astype(str).str.strip().tolist()
    # yfinance uses '-' for some symbols already; keep as-is
    return sorted(set(syms))
