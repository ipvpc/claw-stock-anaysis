from __future__ import annotations

"""Combined screening (stub).

Intended flow:
- run technical oversold scan
- for each candidate, run SEC/Buffett formulas
- rank by combined score

Implement fundamentals in formulas.py + a ticker->CIK resolver.
"""

from formulas import BuffettFormulaEngine
from sec_api import SecClient
from technical_only import run_technical_screening


def main() -> None:
    oversold = run_technical_screening(threshold=-80.0, top_n=50, workers=10)
    print(f"oversold candidates: {len(oversold)}")

    sec = SecClient()

    ranked = []
    for r in oversold:
        t = r["ticker"]
        try:
            from cik_resolver import CikResolver

            cik = CikResolver().cik_for_ticker(t)
            if not cik:
                continue
            facts = sec.company_facts(cik)
            engine = BuffettFormulaEngine(facts)
            results = engine.evaluate_all()
            pass_count = sum(1 for x in results if x.status == "PASS")
            if pass_count < 5:
                continue

            tech_score = (float(r["williams_r"]) + 100.0) / 100.0 * 100.0
            fundamental_score = (pass_count / 10.0) * 100.0
            combined = (tech_score * 0.3) + (fundamental_score * 0.7)

            ranked.append(
                {
                    "ticker": t,
                    "williams_r": r["williams_r"],
                    "buffett_score": pass_count,
                    "combined_score": round(combined, 3),
                }
            )
        except Exception:
            continue

    ranked.sort(key=lambda x: x["combined_score"], reverse=True)

    print("\nTop results:")
    for i, x in enumerate(ranked[:10], start=1):
        print(f"{i:>2}. {x['ticker']:<6} combined={x['combined_score']:<7} buffett={x['buffett_score']}/10 WR={x['williams_r']}")


if __name__ == "__main__":
    main()
