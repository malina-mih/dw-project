# Project Report: Acme Financial Markets Data Warehouse

## Goal

The project implements a small data warehouse for financial markets data. The fictional company Acme Ltd can ingest provider data, preserve provenance, store heterogeneous financial assets and time-series indicators, expose the data through a REST API, and provide Apache Spark analytics, Spark ML prediction, and LLM-assistant access.

## Data Used

The implementation includes synthetic sample data for:

- `asset-msft`: Microsoft stock, sourced from `nasdaq-demo`
- `asset-btc`: Bitcoin, sourced from `nasdaq-demo`
- `asset-gold`: Gold spot reference, sourced from `bloomberg-demo`

The sample intentionally uses heterogeneous indicators. Stocks and crypto use fields such as `open`, `high`, `low`, `close`, and `volume`; gold uses `quoted_price`, `bid`, `ask`, and `ask_size`.

The implementation also includes a public external-provider workflow for Stooq daily CSV data. `POST /ingest/stooq/{symbol}` downloads daily market data, normalizes it into warehouse schemas, preserves row-level provenance, and inserts it through the same repository layer as the sample payload.

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
- Pagination on `/assets` and `/sources` using `offset` and `limit`

FastAPI automatically exposes interactive documentation at `/docs`.

## Analytics

The analytics module uses Apache Spark as the execution engine. Time-series observations are converted into Spark DataFrames, and Spark SQL/DataFrame operations compute:

- count, min, max, average
- trend direction and percent change
- volatility-based risk signal

The prediction workflow uses Spark MLlib linear regression. It assembles a feature vector from the ordered time index, trains a `LinearRegression` model, evaluates training RMSE, and predicts the next time-series value. Responses include `engine: apache_spark` and the ML method name to make the Spark workflow explicit.

## LLM and MCP Integration

`mcp_server.py` exposes MCP tools over stdio. The tools call the running REST API, so LLM answers are grounded in warehouse data. The exposed tools can list assets, inspect asset details, retrieve time series, summarize data, and compute risk signals.

## Reproducibility

1. Install dependencies from `requirements.txt`.
2. Start MongoDB with `docker compose up -d`.
3. Start the API with `python -m uvicorn app.main:app --reload`.
4. Seed sample data with `python scripts/seed_sample_data.py` or `POST /ingest/sample`.
5. Optionally ingest real external data with `POST /ingest/stooq/msft.us?limit=30`.
6. Use `/docs`, REST commands, or the MCP server to demonstrate the platform.

## Testing

The test suite covers:

- Spark analytics summary and Spark MLlib forecast behavior
- Repository save, find-latest, find-all/history, deactivation, pagination, and idempotency patterns
- Ingestion payload dispatch and provider-row normalization

## Limitations and Extensions

The current external provider workflow uses a public CSV endpoint rather than a paid provider API. Forecasting uses a deliberately simple linear Spark MLlib model for explainability; richer models could be added behind the same analytics API.
