from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xbrl_extract import Provenance, annual_history, latest_annual


@dataclass(frozen=True)
class FormulaResult:
    name: str
    status: str  # PASS/FAIL/UNKNOWN
    value: float | None = None
    detail: str | None = None
    provenance: Provenance | None = None


def _passfail(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


class BuffettFormulaEngine:
    """Implements the rules listed in the Medium article (annual-only).

    Notes:
    - Uses SEC companyfacts us-gaap tags.
    - Prefers FY + 10-K values.
    """

    def __init__(self, companyfacts: dict[str, Any]):
        self.companyfacts = companyfacts

    def _need(self, tag: str, label: str) -> Provenance | None:
        return latest_annual(self.companyfacts, tag, label=label)

    def evaluate_all(self) -> list[FormulaResult]:
        res: list[FormulaResult] = []

        cash = self._need("CashAndCashEquivalentsAtCarryingValue", "Cash")
        st_inv = self._need("ShortTermInvestments", "Short-term investments")
        debt_curr = self._need("DebtCurrent", "Debt (current)")
        debt_long = self._need("LongTermDebtNoncurrent", "Long-term debt")
        liabilities = self._need("Liabilities", "Total liabilities")
        equity = self._need("StockholdersEquity", "Shareholders equity")
        net_income = self._need("NetIncomeLoss", "Net income")
        assets = self._need("Assets", "Total assets")
        ca = self._need("AssetsCurrent", "Current assets")
        cl = self._need("LiabilitiesCurrent", "Current liabilities")
        revenue = self._need("Revenues", "Revenue")
        op_income = self._need("OperatingIncomeLoss", "Operating income")
        interest = self._need("InterestExpense", "Interest expense")
        fcf = self._need("NetCashProvidedByUsedInOperatingActivities", "Operating cash flow")

        # 1) Cash test: cash + short-term investments > total debt
        if cash and debt_curr and debt_long:
            cash_total = cash.value + (st_inv.value if st_inv else 0.0)
            debt_total = debt_curr.value + debt_long.value
            ok = cash_total > debt_total
            res.append(
                FormulaResult(
                    name="Cash Test (cash+ST inv > total debt)",
                    status=_passfail(ok),
                    value=cash_total / debt_total if debt_total else None,
                    detail=f"cash_total={cash_total:.2f}, debt_total={debt_total:.2f}",
                    provenance=cash,
                )
            )
        else:
            res.append(FormulaResult(name="Cash Test (cash+ST inv > total debt)", status="UNKNOWN", detail="missing tags"))

        # 2) Debt-to-Equity: total liabilities / equity < 0.25
        if liabilities and equity and equity.value != 0:
            ratio = liabilities.value / equity.value
            ok = ratio < 0.25
            res.append(
                FormulaResult(
                    name="Debt-to-Equity (liabilities/equity < 0.25)",
                    status=_passfail(ok),
                    value=ratio,
                    detail=f"liabilities={liabilities.value:.2f}, equity={equity.value:.2f}",
                    provenance=liabilities,
                )
            )
        else:
            res.append(FormulaResult(name="Debt-to-Equity (liabilities/equity < 0.25)", status="UNKNOWN", detail="missing tags"))

        # 3) ROE: net income / equity > 15%
        if net_income and equity and equity.value != 0:
            roe = net_income.value / equity.value
            ok = roe > 0.15
            res.append(
                FormulaResult(
                    name="ROE (net income/equity > 15%)",
                    status=_passfail(ok),
                    value=roe,
                    detail=f"net_income={net_income.value:.2f}, equity={equity.value:.2f}",
                    provenance=net_income,
                )
            )
        else:
            res.append(FormulaResult(name="ROE (net income/equity > 15%)", status="UNKNOWN", detail="missing tags"))

        # 4) Current ratio: current assets / current liabilities > 1.5
        if ca and cl and cl.value != 0:
            cr = ca.value / cl.value
            ok = cr > 1.5
            res.append(
                FormulaResult(
                    name="Current Ratio (CA/CL > 1.5)",
                    status=_passfail(ok),
                    value=cr,
                    detail=f"CA={ca.value:.2f}, CL={cl.value:.2f}",
                    provenance=ca,
                )
            )
        else:
            res.append(FormulaResult(name="Current Ratio (CA/CL > 1.5)", status="UNKNOWN", detail="missing tags"))

        # 5) Operating margin: operating income / revenue > 12%
        if op_income and revenue and revenue.value != 0:
            om = op_income.value / revenue.value
            ok = om > 0.12
            res.append(
                FormulaResult(
                    name="Operating Margin (op/rev > 12%)",
                    status=_passfail(ok),
                    value=om,
                    detail=f"op_income={op_income.value:.2f}, revenue={revenue.value:.2f}",
                    provenance=op_income,
                )
            )
        else:
            res.append(FormulaResult(name="Operating Margin (op/rev > 12%)", status="UNKNOWN", detail="missing tags"))

        # 6) Asset turnover: revenue / total assets > 0.5
        if revenue and assets and assets.value != 0:
            at = revenue.value / assets.value
            ok = at > 0.5
            res.append(
                FormulaResult(
                    name="Asset Turnover (rev/assets > 0.5)",
                    status=_passfail(ok),
                    value=at,
                    detail=f"revenue={revenue.value:.2f}, assets={assets.value:.2f}",
                    provenance=revenue,
                )
            )
        else:
            res.append(FormulaResult(name="Asset Turnover (rev/assets > 0.5)", status="UNKNOWN", detail="missing tags"))

        # 7) Interest coverage: operating income / interest expense > 3x
        if op_income and interest and interest.value != 0:
            ic = op_income.value / abs(interest.value)
            ok = ic > 3.0
            res.append(
                FormulaResult(
                    name="Interest Coverage (op/interest > 3x)",
                    status=_passfail(ok),
                    value=ic,
                    detail=f"op_income={op_income.value:.2f}, interest={interest.value:.2f}",
                    provenance=interest,
                )
            )
        else:
            res.append(FormulaResult(name="Interest Coverage (op/interest > 3x)", status="UNKNOWN", detail="missing tags"))

        # 8) Earnings stability: positive net income 8+ of last 10 years
        hist = annual_history(self.companyfacts, "NetIncomeLoss", years=10, label="Net income")
        if hist:
            positives = sum(1 for p in hist if p.value > 0)
            ok = positives >= 8
            res.append(
                FormulaResult(
                    name="Earnings Stability (8+/10 years positive)",
                    status=_passfail(ok),
                    value=float(positives),
                    detail=f"positive_years={positives}/10",
                    provenance=hist[0],
                )
            )
        else:
            res.append(FormulaResult(name="Earnings Stability (8+/10 years positive)", status="UNKNOWN", detail="missing history"))

        # 9) Capital allocation: ROE > 15% (value creation check)
        # (This is essentially ROE; included verbatim from article list.)
        if net_income and equity and equity.value != 0:
            roe = net_income.value / equity.value
            ok = roe > 0.15
            res.append(
                FormulaResult(
                    name="Capital Allocation (ROE > 15%)",
                    status=_passfail(ok),
                    value=roe,
                    detail="same as ROE gate",
                    provenance=net_income,
                )
            )
        else:
            res.append(FormulaResult(name="Capital Allocation (ROE > 15%)", status="UNKNOWN", detail="missing tags"))

        # 10) Free cash flow debt coverage (proxy): operating cash flow / total debt > 1.0
        if fcf and debt_curr and debt_long:
            debt_total = debt_curr.value + debt_long.value
            ratio = fcf.value / debt_total if debt_total else None
            ok = bool(ratio is not None and ratio > 1.0)
            res.append(
                FormulaResult(
                    name="Cash Flow Coverage (CFO/debt > 1.0)",
                    status=_passfail(ok),
                    value=ratio,
                    detail=f"CFO={fcf.value:.2f}, debt_total={debt_total:.2f}",
                    provenance=fcf,
                )
            )
        else:
            res.append(FormulaResult(name="Cash Flow Coverage (CFO/debt > 1.0)", status="UNKNOWN", detail="missing tags"))

        return res
