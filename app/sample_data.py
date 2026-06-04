from datetime import datetime, timezone

from app.schemas import AssetIn, DataSourceIn, IngestPayload, TimeSeriesPointIn


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def sample_payload() -> IngestPayload:
    return IngestPayload(
        sources=[
            DataSourceIn(
                source_id="nasdaq-demo",
                name="Nasdaq Data Link Demo",
                vendor_type="public_api_sample",
                api_url="https://data.nasdaq.com",
                license="demo/synthetic for coursework",
                attributes={"coverage": ["stocks", "crypto"]},
                valid_from=dt("2026-01-01T00:00:00"),
            ),
            DataSourceIn(
                source_id="bloomberg-demo",
                name="Bloomberg Market Data Demo",
                vendor_type="commercial_api_sample",
                api_url="https://www.bloomberg.com/professional/product/market-data/",
                license="demo/synthetic for coursework",
                attributes={"coverage": ["stocks", "commodities", "indexes"]},
                valid_from=dt("2026-01-01T00:00:00"),
            ),
        ],
        assets=[
            AssetIn(
                asset_id="asset-msft",
                symbol="MSFT",
                name="Microsoft Corporation",
                **{"class": "stock"},
                region="US",
                currency="USD",
                description="Large-cap technology equity.",
                attributes={"exchange": "NASDAQ", "sector": "Technology"},
                valid_from=dt("2026-01-01T00:00:00"),
            ),
            AssetIn(
                asset_id="asset-btc",
                symbol="BTC",
                name="Bitcoin",
                **{"class": "crypto"},
                region="Global",
                currency="USD",
                description="Decentralized cryptocurrency.",
                attributes={"network": "Bitcoin", "settlement": "blockchain"},
                valid_from=dt("2026-01-01T00:00:00"),
            ),
            AssetIn(
                asset_id="asset-gold",
                symbol="XAU",
                name="Gold Spot",
                **{"class": "metal"},
                region="Global",
                currency="USD",
                description="Gold spot market reference.",
                attributes={"unit": "troy_ounce"},
                valid_from=dt("2026-01-01T00:00:00"),
            ),
        ],
        time_series=[
            TimeSeriesPointIn(
                asset_id="asset-msft",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-13T00:00:00"),
                indicators={"open": 448.4, "high": 455.1, "low": 446.8, "close": 452.3, "volume": 18520000},
                provenance={"dataset": "sample_market_data", "row": 1},
            ),
            TimeSeriesPointIn(
                asset_id="asset-msft",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-14T00:00:00"),
                indicators={"open": 452.8, "high": 458.6, "low": 451.0, "close": 457.9, "volume": 19250000},
                provenance={"dataset": "sample_market_data", "row": 2},
            ),
            TimeSeriesPointIn(
                asset_id="asset-msft",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-15T00:00:00"),
                indicators={"open": 458.1, "high": 461.0, "low": 454.2, "close": 455.4, "volume": 20310000},
                provenance={"dataset": "sample_market_data", "row": 3},
            ),
            TimeSeriesPointIn(
                asset_id="asset-msft",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-18T00:00:00"),
                indicators={"open": 456.0, "high": 463.7, "low": 455.6, "close": 462.8, "volume": 17640000},
                provenance={"dataset": "sample_market_data", "row": 4},
            ),
            TimeSeriesPointIn(
                asset_id="asset-msft",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-19T00:00:00"),
                indicators={"open": 463.2, "high": 466.5, "low": 459.9, "close": 461.6, "volume": 18890000},
                provenance={"dataset": "sample_market_data", "row": 5},
            ),
            TimeSeriesPointIn(
                asset_id="asset-btc",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-13T00:00:00"),
                indicators={"open": 103800, "high": 105100, "low": 101700, "close": 104900, "volume": 31500},
                provenance={"dataset": "sample_market_data", "row": 6},
            ),
            TimeSeriesPointIn(
                asset_id="asset-btc",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-14T00:00:00"),
                indicators={"open": 104950, "high": 106400, "low": 103200, "close": 103500, "volume": 29800},
                provenance={"dataset": "sample_market_data", "row": 7},
            ),
            TimeSeriesPointIn(
                asset_id="asset-btc",
                source_id="nasdaq-demo",
                timestamp=dt("2026-05-15T00:00:00"),
                indicators={"open": 103550, "high": 108000, "low": 102800, "close": 107250, "volume": 35200},
                provenance={"dataset": "sample_market_data", "row": 8},
            ),
            TimeSeriesPointIn(
                asset_id="asset-gold",
                source_id="bloomberg-demo",
                timestamp=dt("2026-05-13T00:00:00"),
                indicators={"quoted_price": 3305.2, "bid": 3304.8, "ask": 3305.6, "ask_size": 120},
                provenance={"dataset": "sample_market_data", "row": 9},
            ),
            TimeSeriesPointIn(
                asset_id="asset-gold",
                source_id="bloomberg-demo",
                timestamp=dt("2026-05-14T00:00:00"),
                indicators={"quoted_price": 3318.7, "bid": 3318.2, "ask": 3319.1, "ask_size": 95},
                provenance={"dataset": "sample_market_data", "row": 10},
            ),
            TimeSeriesPointIn(
                asset_id="asset-gold",
                source_id="bloomberg-demo",
                timestamp=dt("2026-05-15T00:00:00"),
                indicators={"quoted_price": 3297.4, "bid": 3296.9, "ask": 3297.9, "ask_size": 140},
                provenance={"dataset": "sample_market_data", "row": 11},
            ),
        ],
    )


def ingest_payload(repo, payload: IngestPayload) -> dict[str, int]:
    counts = {"sources": 0, "assets": 0, "time_series": 0}
    for source in payload.sources:
        repo.insert_source(source)
        counts["sources"] += 1
    for asset in payload.assets:
        repo.insert_asset(asset)
        counts["assets"] += 1
    for point in payload.time_series:
        repo.insert_time_series_point(point)
        counts["time_series"] += 1
    return counts
