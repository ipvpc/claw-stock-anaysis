# stock-analysis (from Medium article scaffold)

This folder is a **reconstructed scaffold** based on the Medium post:
<https://florinelchis.medium.com/building-a-wall-street-grade-stock-screener-with-openclaw-ai-agents-and-free-apis-48cbeeadd9d5>

It contains a runnable implementation of the architecture described:

- **Technical scan:** `technical_only.py` (Williams %R oversold)
- **Fundamentals:** `analyze.py` (Buffett rules using SEC EDGAR companyfacts)
- **Combined screen:** `screening.py` (30% technical + 70% fundamentals)
- **Caching layer:** Postgres (`postgres_cache.py`) via docker-compose
- **Web/API:** `api_server.py` (FastAPI + basic auth) exposed on port **8356**

## Features
- Oversold scan across S&P 500 (parallel fetching, cached)
- Buffett-style rules from SEC XBRL companyfacts (annual-only: FY + 10-K)
- Data provenance: each metric includes the XBRL tag + FY + end date
- Postgres cache (JSONB KV) for price + SEC payloads
- API + minimal web UI (Basic Auth)

## Folder structure
- `api_server.py` — FastAPI app + minimal HTML UI
- `technical_only.py` — oversold scan
- `technical_indicators.py` — Williams %R + EMA
- `screening.py` — combined screen
- `analyze.py` — single-ticker fundamentals
- `sec_api.py` — SEC EDGAR client
- `cik_resolver.py` — ticker → CIK resolver (cached)
- `xbrl_extract.py` — annual-only XBRL extraction helpers
- `formulas.py` — Buffett rules
- `postgres_cache.py` — Postgres cache implementation

## Configuration

### Required (API mode)
- `BASIC_AUTH_PASS` — protects the API/web UI

### Recommended
- `SEC_USER_AGENT` — SEC requires a real User-Agent. Example:
  `stock-analysis/0.1 (contact: you@yourdomain.com)`

### Postgres
- Compose starts a local Postgres on host port `54331`.
- App uses `DATABASE_URL` (defaults to the internal compose DNS `db`).

## How to run (3 modes)

### Mode 1: Web UI + API (recommended)

```bash
cd /home/clawdbot/.openclaw/workspace/side-projects/stock-analysis
export BASIC_AUTH_PASS='change-me'
# optional but recommended
export SEC_USER_AGENT='stock-analysis/0.1 (contact: you@yourdomain.com)'

docker compose up -d --build
```

Open:
- Web UI: `http://localhost:8356/`
- Health: `http://localhost:8356/health`

### Mode 2: CLI (local Python)

```bash
cd /home/clawdbot/.openclaw/workspace/side-projects/stock-analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Requires DATABASE_URL pointing at Postgres (either the compose db or your own)
export DATABASE_URL='postgresql://stock:stock@localhost:54331/stock_analysis'
export SEC_USER_AGENT='stock-analysis/0.1 (contact: you@yourdomain.com)'

python technical_only.py --top-n 20 --workers 10 --format telegram
python analyze.py AAPL
python screening.py
```

### Mode 3: CLI inside Docker

```bash
cd /home/clawdbot/.openclaw/workspace/side-projects/stock-analysis
export BASIC_AUTH_PASS='change-me'
docker compose up -d --build

# run a one-shot CLI command in the api container
docker compose run --rm api python technical_only.py --top-n 20 --workers 10 --format telegram
```

## API usage examples (curl)

### Oversold
```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"threshold":-80,"top_n":20,"days":90,"workers":10,"format":"telegram"}' \
  http://localhost:8356/api/oversold
```

### Analyze
```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"ticker":"AAPL"}' \
  http://localhost:8356/api/analyze
```

### Screen
```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"threshold":-80,"min_score":5,"top_n":10,"workers":10}' \
  http://localhost:8356/api/screen
```

## OpenClaw integration

You can integrate in two ways:

### A) Skill (CLI)
Use `SKILL.md` commands to run scripts directly (good for Telegram-driven workflows).

### B) Call the API
Have OpenClaw call the API endpoints (good for integration into dashboards/services).

## Troubleshooting
- **401 Unauthorized:** set `BASIC_AUTH_PASS` and use `-u admin:$BASIC_AUTH_PASS`.
- **SEC 403 / rate limits:** set a real `SEC_USER_AGENT` and reduce request rate.
- **Slow first run:** expected (cold cache). Subsequent runs should be much faster.
