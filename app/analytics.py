from __future__ import annotations

from datetime import datetime
from statistics import mean, pstdev
from typing import Any

from app.repository import WarehouseRepository


def _numeric_values(points: list[dict[str, Any]], indicator: str) -> list[float]:
    values: list[float] = []
    for point in points:
        value = point.get("indicators", {}).get(indicator)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def summary(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, start=start, end=end, limit=10000)
    values = _numeric_values(points, indicator)
    if not values:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "count": 0,
            "message": "No numeric values found for the requested indicator.",
        }
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "average": mean(values),
        "first": values[0],
        "last": values[-1],
    }


def trend(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    values = _numeric_values(points, indicator)
    if len(values) < 2:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "direction": "unknown",
            "message": "At least two values are required.",
        }
    change = values[-1] - values[0]
    pct_change = change / values[0] * 100 if values[0] else 0
    if pct_change > 1:
        direction = "up"
    elif pct_change < -1:
        direction = "down"
    else:
        direction = "flat"
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "direction": direction,
        "absolute_change": change,
        "percent_change": pct_change,
        "first": values[0],
        "last": values[-1],
    }


def next_value_forecast(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    values = _numeric_values(points, indicator)
    if len(values) < 2:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "message": "At least two values are required.",
        }
    deltas = [right - left for left, right in zip(values, values[1:])]
    forecast = values[-1] + mean(deltas)
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "method": "naive_average_delta",
        "last_value": values[-1],
        "forecast_next_value": forecast,
    }


def risk_signal(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    values = _numeric_values(points, indicator)
    if len(values) < 3:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "risk": "unknown",
            "message": "At least three values are required.",
        }
    returns = [
        (right - left) / left
        for left, right in zip(values, values[1:])
        if left != 0
    ]
    volatility = pstdev(returns) if len(returns) > 1 else 0
    last_return = returns[-1] if returns else 0
    if volatility >= 0.04 or last_return <= -0.05:
        risk = "high"
    elif volatility >= 0.02 or last_return <= -0.025:
        risk = "medium"
    else:
        risk = "low"
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "risk": risk,
        "volatility": volatility,
        "last_return": last_return,
        "observations": len(values),
    }
