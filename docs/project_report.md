# Project Report: Acme Financial Markets Data Warehouse

## Goal

The project implements a small data warehouse for financial markets data. The fictional company Acme Ltd can ingest provider data, preserve provenance, store heterogeneous financial assets and time-series indicators, expose the data through a REST API, and provide analytics and LLM-assistant access.

## Data Used

The implementation includes synthetic sample data for:

- `asset-msft`: Microsoft stock, sourced from `nasdaq-demo`
- `asset-btc`: Bitcoin, sourced from `nasdaq-demo`
- `asset-gold`: Gold spot reference, sourced from `bloomberg-demo`

The sample intentionally uses heterogeneous indicators. Stocks and crypto use fields such as `open`, `high`, `low`, `close`, and `volume`; gold uses `quoted_price`, `bid`, `ask`, and `ask_size`.

## Storage Design

MongoDB is used as the mandatory NoSQL storage system. The database contains:

- `data_sources`: provider metadata and provenance information
- `assets`: asset versions and availability marker records
- `time_series`: immutable market observations

Business records are insert-only. New information creates a new version. Deactivation creates an `availability_marker` with `valid_from`, rather than updating or deleting the existing asset.

## REST API

The API supports:

- Listing all available assets
- Looking up one asset by identifier
- Listing data sources
- Inspecting a time-series definition
- Returning time-series points for an asset/source pair
- Running analytics: summary, trend, forecast, and risk signal

FastAPI automatically exposes interactive documentation at `/docs`.

## Analytics

The analytics module computes simple but explainable outputs:

- count, min, max, average
- trend direction and percent change
- naive next-value forecast using average historical delta
- volatility-based risk signal

The design keeps analytics separate from storage so the platform could later feed Spark, Pandas, or an ML pipeline.

## LLM and MCP Integration

`mcp_server.py` exposes MCP tools over stdio. The tools call the running REST API, so LLM answers are grounded in warehouse data. The exposed tools can list assets, inspect asset details, retrieve time series, summarize data, and compute risk signals.

## Reproducibility

1. Install dependencies from `requirements.txt`.
2. Start MongoDB with `docker compose up -d`.
3. Start the API with `python -m uvicorn app.main:app --reload`.
4. Seed sample data with `python scripts/seed_sample_data.py` or `POST /ingest/sample`.
5. Use `/docs`, REST commands, or the MCP server to demonstrate the platform.

## Limitations and Extensions

The current implementation uses synthetic sample data, not paid provider APIs. The ingestion layer is structured so real REST provider clients can be added later. Forecasting and risk are intentionally simple for clarity; they could be replaced with richer models.
