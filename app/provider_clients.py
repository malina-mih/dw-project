from __future__ import annotations

import csv
from datetime import date, datetime, time, timezone
from io import StringIO

import requests

from app.schemas import AssetIn, DataSourceIn, IngestPayload, TimeSeriesPointIn


STOOQ_SOURCE_ID = "stooq-public"
STOOQ_DAILY_URL = "https://stooq.com/q/d/l/"


def _symbol_to_asset_id(symbol: str) -> str:
    return f"asset-{symbol.lower().replace('.', '-')}"


def _daily_timestamp(value: str) -> datetime:
    parsed = date.fromisoformat(value)
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def payload_from_stooq_csv(
    symbol: str,
    csv_text: str,
    asset_id: str | None = None,
    asset_class: str = "stock",
    region: str = "US",
    currency: str = "USD",
    limit: int = 100,
) -> IngestPayload:
    normalized_symbol = symbol.strip().lower()
    resolved_asset_id = asset_id or _symbol_to_asset_id(normalized_symbol)
    reader = csv.DictReader(StringIO(csv_text))
    rows = [row for row in reader if row.get("Date") and row.get("Close")]
    rows = rows[-limit:]
    points = [
        TimeSeriesPointIn(
            asset_id=resolved_asset_id,
            source_id=STOOQ_SOURCE_ID,
            timestamp=_daily_timestamp(row["Date"]),
            indicators={
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(float(row["Volume"])),
            },
            provenance={
                "provider": "stooq",
                "url": STOOQ_DAILY_URL,
                "symbol": normalized_symbol,
                "date": row["Date"],
            },
        )
        for row in rows
    ]
    return IngestPayload(
        sources=[
            DataSourceIn(
                source_id=STOOQ_SOURCE_ID,
                name="Stooq Daily Market Data",
                vendor_type="public_rest_csv",
                api_url=STOOQ_DAILY_URL,
                license="public web endpoint; terms apply",
                attributes={"format": "csv", "frequency": "daily"},
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ],
        assets=[
            AssetIn(
                asset_id=resolved_asset_id,
                symbol=normalized_symbol.upper(),
                name=f"{normalized_symbol.upper()} market instrument",
                **{"class": asset_class},
                region=region,
                currency=currency,
                attributes={"provider_symbol": normalized_symbol, "provider": "stooq"},
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ],
        time_series=points,
    )


def fetch_stooq_daily_payload(
    symbol: str,
    asset_id: str | None = None,
    asset_class: str = "stock",
    region: str = "US",
    currency: str = "USD",
    limit: int = 100,
) -> IngestPayload:
    response = requests.get(
        STOOQ_DAILY_URL,
        params={"s": symbol.strip().lower(), "i": "d"},
        timeout=20,
    )
    response.raise_for_status()
    return payload_from_stooq_csv(
        symbol=symbol,
        csv_text=response.text,
        asset_id=asset_id,
        asset_class=asset_class,
        region=region,
        currency=currency,
        limit=limit,
    )
