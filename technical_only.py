from __future__ import annotations

import argparse

from price_data import PriceDataManager
from sp500_tickers import get_sp500_tickers
from technical_indicators import ema, williams_r


def run_technical_screening(
    *,
    threshold: float = -80.0,
    top_n: int = 20,
    days: int = 90,
    workers: int = 10,
) -> list[dict]:
    tickers = get_sp500_tickers()
    mgr = PriceDataManager()

    price_data = mgr.batch_fetch_prices(tickers, days=days, workers=workers)

    signals: list[dict] = []
    for t, df in price_data.items():
        try:
            wr = williams_r(df, period=21)
            wr_ema = ema(wr, period=13)
            latest = float(wr.iloc[-1])
            if latest < threshold:
                signals.append(
                    {
                        "ticker": t,
                        "williams_r": round(latest, 3),
                        "williams_r_ema": round(float(wr_ema.iloc[-1]), 3),
                        "signal": "oversold",
                    }
                )
        except Exception:
            continue

    signals.sort(key=lambda x: x["williams_r"])
    return signals[:top_n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=-80.0)
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--format", choices=["text", "telegram"], default="text")
    args = ap.parse_args()

    rows = run_technical_screening(threshold=args.threshold, top_n=args.top_n, days=args.days, workers=args.workers)

    if args.format == "telegram":
        from telegram_format import format_oversold_table

        print(format_oversold_table(rows, top_n=args.top_n))
        return

    for r in rows:
        print(f"{r['ticker']}: WR={r['williams_r']} EMA={r['williams_r_ema']}")


if __name__ == "__main__":
    main()
