from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from technical_only import run_technical_screening
from analyze import main as analyze_main  # not used directly
from cik_resolver import CikResolver
from formulas import BuffettFormulaEngine
from sec_api import SecClient
from screening import main as screening_main  # not used directly

security = HTTPBasic()
app = FastAPI(title="stock-analysis", version="0.1.0")


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else default


def require_basic_auth(creds: HTTPBasicCredentials = Depends(security)) -> bool:
    user = _env("BASIC_AUTH_USER", "admin")
    pw = _env("BASIC_AUTH_PASS", "")
    if not pw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="BASIC_AUTH_PASS is required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if creds.username != user or creds.password != pw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(_auth: bool = Depends(require_basic_auth)) -> str:
    return """<!doctype html>
<html>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>stock-analysis</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:20px;background:#0b0f17;color:#e5e7eb}
.card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px;max-width:900px}
input,select{background:#0f172a;color:#e5e7eb;border:1px solid #334155;border-radius:10px;padding:8px}
button{background:#0f172a;color:#e5e7eb;border:1px solid #334155;border-radius:10px;padding:8px 12px;cursor:pointer}
pre{white-space:pre-wrap}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
</style></head>
<body>
<div class='card'>
<h2>stock-analysis</h2>
<div class='row'>
  <button onclick='runOversold()'>Oversold</button>
  <input id='ticker' placeholder='Ticker (e.g. AAPL)' />
  <button onclick='runAnalyze()'>Analyze</button>
  <button onclick='runScreen()'>Screen</button>
</div>
<pre id='out'>Ready.</pre>
</div>
<script>
async function postJson(url, body){
  const r = await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
  const t = await r.text();
  try{ return JSON.parse(t);}catch{ return {ok:false, raw:t, status:r.status}; }
}
async function runOversold(){
  document.getElementById('out').textContent='Running oversold...';
  const data = await postJson('/api/oversold',{threshold:-80, top_n:20, workers:10, format:'telegram'});
  document.getElementById('out').textContent = data.text || JSON.stringify(data,null,2);
}
async function runAnalyze(){
  const ticker=document.getElementById('ticker').value.trim();
  if(!ticker){alert('enter ticker');return;}
  document.getElementById('out').textContent='Analyzing...';
  const data = await postJson('/api/analyze',{ticker});
  document.getElementById('out').textContent = JSON.stringify(data,null,2);
}
async function runScreen(){
  document.getElementById('out').textContent='Running screen...';
  const data = await postJson('/api/screen',{threshold:-80, min_score:5, top_n:10, workers:10});
  document.getElementById('out').textContent = JSON.stringify(data,null,2);
}
</script>
</body>
</html>"""


@app.post("/api/oversold")
def api_oversold(payload: dict[str, Any], _auth: bool = Depends(require_basic_auth)):
    threshold = float(payload.get("threshold", -80.0))
    top_n = int(payload.get("top_n", 20))
    days = int(payload.get("days", 90))
    workers = int(payload.get("workers", 10))
    fmt = str(payload.get("format", "json"))

    rows = run_technical_screening(threshold=threshold, top_n=top_n, days=days, workers=workers)
    if fmt == "telegram":
        from telegram_format import format_oversold_table

        return {"ok": True, "text": format_oversold_table(rows, top_n=top_n), "rows": rows}
    return {"ok": True, "rows": rows}


@app.post("/api/analyze")
def api_analyze(payload: dict[str, Any], _auth: bool = Depends(require_basic_auth)):
    ticker = str(payload.get("ticker") or "").upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")

    cik = CikResolver().cik_for_ticker(ticker)
    if not cik:
        raise HTTPException(status_code=404, detail="could not resolve ticker to CIK")

    facts = SecClient().company_facts(cik)
    engine = BuffettFormulaEngine(facts)
    results = engine.evaluate_all()

    passed = sum(1 for r in results if r.status == "PASS")

    out = []
    for r in results:
        out.append(
            {
                "name": r.name,
                "status": r.status,
                "value": r.value,
                "detail": r.detail,
                "provenance": (r.provenance.__dict__ if r.provenance else None),
            }
        )

    return {"ok": True, "ticker": ticker, "cik": cik, "score": f"{passed}/{len(results)}", "results": out}


@app.post("/api/screen")
def api_screen(payload: dict[str, Any], _auth: bool = Depends(require_basic_auth)):
    threshold = float(payload.get("threshold", -80.0))
    min_score = int(payload.get("min_score", 5))
    top_n = int(payload.get("top_n", 10))
    workers = int(payload.get("workers", 10))

    oversold = run_technical_screening(threshold=threshold, top_n=50, days=90, workers=workers)

    sec = SecClient()
    ranked = []

    for r in oversold:
        t = r["ticker"]
        cik = CikResolver().cik_for_ticker(t)
        if not cik:
            continue
        try:
            facts = sec.company_facts(cik)
            engine = BuffettFormulaEngine(facts)
            results = engine.evaluate_all()
            pass_count = sum(1 for x in results if x.status == "PASS")
            if pass_count < min_score:
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
    return {"ok": True, "count": len(ranked), "top": ranked[:top_n]}
