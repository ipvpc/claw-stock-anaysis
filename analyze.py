from __future__ import annotations

import argparse

from formulas import BuffettFormulaEngine
from sec_api import SecClient


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--cik", help="CIK (optional; will resolve via SEC mapping if omitted)")
    args = ap.parse_args()

    cik = args.cik
    if not cik:
        from cik_resolver import CikResolver

        cik = CikResolver().cik_for_ticker(args.ticker)
        if not cik:
            raise SystemExit("Could not resolve ticker->CIK; provide --cik")

    sec = SecClient()
    facts = sec.company_facts(cik)
    engine = BuffettFormulaEngine(facts)
    results = engine.evaluate_all()

    passed = sum(1 for r in results if r.status == "PASS")
    total = len(results)
    print(f"{args.ticker.upper()} — Buffett analysis: {passed}/{total} PASS")
    for r in results:
        val = ""
        if r.value is not None:
            if "%" in r.name or "Margin" in r.name or "ROE" in r.name:
                val = f"{(r.value * 100):.2f}%"
            else:
                val = f"{r.value:.4f}" if abs(r.value) < 1000 else f"{r.value:.2f}"
        prov = ""
        if r.provenance is not None:
            prov = f"[{r.provenance.tag} FY={r.provenance.fy} end={r.provenance.end} form={r.provenance.form}]"
        detail = f" ({r.detail})" if r.detail else ""
        print(f"- {r.name}: {r.status} {val} {prov}{detail}")


if __name__ == "__main__":
    main()
