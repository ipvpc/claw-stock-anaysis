from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Provenance:
    value: float
    tag: str
    label: str | None
    unit: str | None
    form: str | None
    fy: int | None
    fp: str | None
    end: str | None
    filed: str | None


def _iter_facts(companyfacts: dict[str, Any], tag: str) -> Iterable[dict[str, Any]]:
    facts = companyfacts.get("facts") or {}
    us = facts.get("us-gaap") or {}
    obj = us.get(tag) or {}
    units = obj.get("units") or {}
    # Prefer USD for dollar values; fall back to first unit.
    if "USD" in units:
        vals = units["USD"]
    else:
        first = next(iter(units.values()), [])
        vals = first
    for v in vals or []:
        yield v


def latest_annual(companyfacts: dict[str, Any], tag: str, *, label: str | None = None) -> Provenance | None:
    """Get the latest annual (FY, 10-K) value for a given XBRL tag.

    We prefer:
    - fp == FY
    - form == 10-K
    - most recent end date

    Returns provenance so every number is traceable.
    """

    candidates: list[dict[str, Any]] = []
    for v in _iter_facts(companyfacts, tag):
        fp = v.get("fp")
        form = v.get("form")
        if fp != "FY":
            continue
        if form != "10-K":
            continue
        if v.get("val") is None:
            continue
        candidates.append(v)

    if not candidates:
        return None

    # Sort by end date then filed date
    candidates.sort(key=lambda x: (str(x.get("end") or ""), str(x.get("filed") or "")), reverse=True)
    best = candidates[0]

    try:
        val = float(best["val"])
    except Exception:
        return None

    return Provenance(
        value=val,
        tag=tag,
        label=label,
        unit=str(best.get("unit") or best.get("uom") or ""),
        form=str(best.get("form") or ""),
        fy=int(best.get("fy")) if best.get("fy") is not None else None,
        fp=str(best.get("fp") or ""),
        end=str(best.get("end") or ""),
        filed=str(best.get("filed") or ""),
    )


def annual_history(companyfacts: dict[str, Any], tag: str, *, years: int = 10, label: str | None = None) -> list[Provenance]:
    vals: list[Provenance] = []
    for v in _iter_facts(companyfacts, tag):
        if v.get("fp") != "FY" or v.get("form") != "10-K":
            continue
        if v.get("val") is None:
            continue
        try:
            val = float(v["val"])
        except Exception:
            continue
        vals.append(
            Provenance(
                value=val,
                tag=tag,
                label=label,
                unit=str(v.get("unit") or v.get("uom") or ""),
                form=str(v.get("form") or ""),
                fy=int(v.get("fy")) if v.get("fy") is not None else None,
                fp=str(v.get("fp") or ""),
                end=str(v.get("end") or ""),
                filed=str(v.get("filed") or ""),
            )
        )

    vals.sort(key=lambda x: (x.fy or 0, x.end or ""), reverse=True)
    return vals[:years]
