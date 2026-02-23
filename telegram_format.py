from __future__ import annotations

from typing import Any


def format_oversold_table(rows: list[dict[str, Any]], *, top_n: int = 20) -> str:
    lines = [f"Oversold (top {min(top_n, len(rows))}):"]
    for i, r in enumerate(rows[:top_n], start=1):
        t = r.get("ticker")
        wr = r.get("williams_r")
        ema = r.get("williams_r_ema")
        lines.append(f"{i:>2}. {t:<6} WR={wr:>7} EMA={ema:>7}")
    return "\n".join(lines)
