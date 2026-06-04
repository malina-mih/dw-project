# Acme Financial Markets Data Warehouse

Runnable coursework platform for a fictional company, Acme Ltd. It ingests financial-market data, stores heterogeneous financial assets and time-series indicators in MongoDB, exposes a REST API, provides basic analytics, and includes an MCP server so an LLM assistant can query grounded warehouse data.

## Architecture

- **FastAPI backend** in `app/main.py`
- **MongoDB NoSQL storage** with immutable temporal records
- **Sample ingestion** in `app/sample_data.py` and `scripts/seed_sample_data.py`
- **Analytics** in `app/analytics.py`
- **MCP stdio server** in `mcp_server.py`

Temporal rule: records are inserted as new versions. The application does not update or delete stored business records. If an asset is unavailable, `/assets/{asset_id}/deactivate` inserts an `availability_marker` with a `valid_from` timestamp.

## Setup

```powershell
cd "C:\Malina\BD1\DW PROJECT\DW_project"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d
```

If you do not use Docker, start a local MongoDB server on `mongodb://localhost:27017`.

Optional environment variables:

```powershell
$env:MONGODB_URI="mongodb://localhost:27017"
$env:MONGODB_DB="acme_finance_dw"
$env:API_BASE_URL="http://localhost:8000"
```

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Seed the sample dataset:

```powershell
.\.venv\Scripts\python.exe scripts\seed_sample_data.py
```

You can also seed through the API:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/ingest/sample
```

## Required Use Cases

### Q1: available financial assets

```powershell
Invoke-RestMethod http://localhost:8000/assets
```

### Q2: details for one asset

```powershell
Invoke-RestMethod http://localhost:8000/assets/asset-msft
```

### Q3: available financial data sources

```powershell
Invoke-RestMethod http://localhost:8000/sources
```

### Q4: time-series metadata

```powershell
Invoke-RestMethod http://localhost:8000/timeseries/asset-msft/nasdaq-demo/details
```

### Q5: time-series data for asset and source

```powershell
Invoke-RestMethod "http://localhost:8000/timeseries/asset-msft/nasdaq-demo?limit=5"
```

## Analytics Examples

```powershell
Invoke-RestMethod "http://localhost:8000/analytics/summary?asset_id=asset-msft&source_id=nasdaq-demo&indicator=close"
Invoke-RestMethod "http://localhost:8000/analytics/trend?asset_id=asset-msft&source_id=nasdaq-demo&indicator=close"
Invoke-RestMethod "http://localhost:8000/analytics/forecast?asset_id=asset-msft&source_id=nasdaq-demo&indicator=close"
Invoke-RestMethod "http://localhost:8000/analytics/risk?asset_id=asset-btc&source_id=nasdaq-demo&indicator=close"
```

For heterogeneous data, gold uses `quoted_price` instead of `close`:

```powershell
Invoke-RestMethod "http://localhost:8000/analytics/summary?asset_id=asset-gold&source_id=bloomberg-demo&indicator=quoted_price"
```

## Temporal Demo

Insert a marker saying an asset is no longer available from a future date:

```powershell
Invoke-RestMethod -Method Post `
  -ContentType "application/json" `
  -Body '{"valid_from":"2026-06-01T00:00:00Z","reason":"provider delisted sample asset"}' `
  http://localhost:8000/assets/asset-gold/deactivate
```

Historical lookup before the marker still returns the asset:

```powershell
Invoke-RestMethod "http://localhost:8000/assets/asset-gold?as_of=2026-05-20T00:00:00Z"
```

Lookup after the marker returns 404:

```powershell
Invoke-RestMethod "http://localhost:8000/assets/asset-gold?as_of=2026-06-02T00:00:00Z"
```

## MCP Assistant

Start the API first, then configure an MCP client to run:

```powershell
.\.venv\Scripts\python.exe mcp_server.py
```

The MCP server exposes these tools:

- `list_assets`
- `get_asset_details`
- `list_sources`
- `get_time_series`
- `summarize_series`
- `risk_signal`

Demo assistant prompts:

- "List the assets available in the Acme warehouse."
- "Summarize MSFT close prices from the Nasdaq demo source."
- "Which sample asset looks riskier, MSFT or BTC?"

## Project Files

- `app/database.py`: MongoDB connection and indexes
- `app/repository.py`: immutable insert/query behavior
- `app/main.py`: REST API
- `app/analytics.py`: summary, trend, forecast, risk signal
- `mcp_server.py`: MCP tools backed by the REST API
- `docs/project_report.md`: report draft
- `docs/ai_usage_statement.md`: AI usage statement draft
