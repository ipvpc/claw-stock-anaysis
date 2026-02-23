---
name: stock-analysis
description: Analyze stocks using technical oversold scan and (stubbed) Buffett formulas.
user-invocable: true
requires:
  bins:
    - python3
  packages:
    - yfinance
    - pandas
    - numpy
    - requests
---

# Stock Analysis Skill

This project supports **CLI** and a **web/API service** (recommended for integrations).

## Commands

### Run API service

```bash
cd /home/clawdbot/.openclaw/workspace/side-projects/stock-analysis
export BASIC_AUTH_PASS='change-me'
docker compose up -d --build
```

API is at: `http://localhost:8356`

### oversold (CLI)

```bash
python3 technical_only.py --top-n 20 --workers 10 --format telegram
```

### oversold (API)

```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"threshold":-80,"top_n":20,"workers":10,"format":"telegram"}' \
  http://localhost:8356/api/oversold
```

### analyze (CLI)

```bash
python3 analyze.py AAPL
```

### analyze (API)

```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"ticker":"AAPL"}' \
  http://localhost:8356/api/analyze
```

### screen (API)

```bash
curl -u admin:$BASIC_AUTH_PASS \
  -H 'content-type: application/json' \
  -d '{"threshold":-80,"min_score":5,"top_n":10,"workers":10}' \
  http://localhost:8356/api/screen
```
