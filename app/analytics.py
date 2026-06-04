from __future__ import annotations

import os
import sys
from datetime import datetime
from functools import lru_cache
from typing import Any

from app.repository import WarehouseRepository


def _spark_imports():
    try:
        from pyspark.ml.evaluation import RegressionEvaluator
        from pyspark.ml.feature import VectorAssembler
        from pyspark.ml.regression import LinearRegression
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as sf
        from pyspark.sql import Window
    except ImportError as exc:
        raise RuntimeError(
            "PySpark is required for analytics. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc
    return SparkSession, sf, Window, VectorAssembler, LinearRegression, RegressionEvaluator


@lru_cache(maxsize=1)
def spark_session():
    SparkSession, *_ = _spark_imports()
    python_dir = os.path.dirname(sys.executable)
    os.environ["PATH"] = python_dir + os.pathsep + os.environ.get("PATH", "")
    worker_python = "python" if os.name == "nt" else sys.executable
    os.environ["PYSPARK_PYTHON"] = worker_python
    os.environ["PYSPARK_DRIVER_PYTHON"] = worker_python
    return (
        SparkSession.builder.appName("acme-finance-warehouse-analytics")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.pyspark.python", worker_python)
        .config("spark.pyspark.driver.python", worker_python)
        .getOrCreate()
    )


def _series_rows(points: list[dict[str, Any]], indicator: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        value = point.get("indicators", {}).get(indicator)
        if isinstance(value, int | float):
            rows.append(
                {
                    "idx": float(index),
                    "value": float(value),
                }
            )
    return rows


def _series_frame(points: list[dict[str, Any]], indicator: str):
    rows = _series_rows(points, indicator)
    if not rows:
        return None
    values_sql = ", ".join(f"({row['idx']}D, {row['value']}D)" for row in rows)
    return spark_session().sql(f"SELECT * FROM VALUES {values_sql} AS series(idx, value)")


def _no_values(asset_id: str, source_id: str, indicator: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "engine": "apache_spark",
        "count": 0,
        "message": "No numeric values found for the requested indicator.",
    }


def summary(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, start=start, end=end, limit=10000)
    frame = _series_frame(points, indicator)
    if frame is None:
        return _no_values(asset_id, source_id, indicator)
    _, sf, *_ = _spark_imports()
    aggregate = frame.agg(
        sf.count("value").alias("count"),
        sf.min("value").alias("min"),
        sf.max("value").alias("max"),
        sf.avg("value").alias("average"),
    ).first()
    first = frame.orderBy("idx").select("value").first()["value"]
    last = frame.orderBy(sf.desc("idx")).select("value").first()["value"]
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "engine": "apache_spark",
        "count": aggregate["count"],
        "min": aggregate["min"],
        "max": aggregate["max"],
        "average": aggregate["average"],
        "first": first,
        "last": last,
    }


def trend(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    frame = _series_frame(points, indicator)
    if frame is None or frame.count() < 2:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "engine": "apache_spark",
            "direction": "unknown",
            "message": "At least two values are required.",
        }
    _, sf, *_ = _spark_imports()
    endpoints = frame.agg(sf.min("idx").alias("first_idx"), sf.max("idx").alias("last_idx")).first()
    first = frame.where(frame.idx == endpoints["first_idx"]).select("value").first()["value"]
    last = frame.where(frame.idx == endpoints["last_idx"]).select("value").first()["value"]
    change = last - first
    pct_change = change / first * 100 if first else 0
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
        "engine": "apache_spark",
        "direction": direction,
        "absolute_change": change,
        "percent_change": pct_change,
        "first": first,
        "last": last,
    }


def next_value_forecast(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    frame = _series_frame(points, indicator)
    if frame is None or frame.count() < 2:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "engine": "apache_spark",
            "message": "At least two values are required.",
        }
    _, sf, _, VectorAssembler, LinearRegression, RegressionEvaluator = _spark_imports()
    assembler = VectorAssembler(inputCols=["idx"], outputCol="features")
    training = assembler.transform(frame).select("features", sf.col("value").alias("label"))
    model = LinearRegression(featuresCol="features", labelCol="label").fit(training)
    next_idx = frame.agg((sf.max("idx") + sf.lit(1.0)).alias("next_idx")).first()["next_idx"]
    prediction_frame = spark_session().sql(f"SELECT {float(next_idx)}D AS idx")
    prediction = assembler.transform(prediction_frame)
    forecast = model.transform(prediction).select("prediction").first()["prediction"]
    predictions = model.transform(training)
    rmse = RegressionEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="rmse",
    ).evaluate(predictions)
    last_value = frame.orderBy(sf.desc("idx")).select("value").first()["value"]
    return {
        "asset_id": asset_id,
        "source_id": source_id,
        "indicator": indicator,
        "engine": "apache_spark",
        "method": "spark_mllib_linear_regression",
        "training_rows": frame.count(),
        "last_value": last_value,
        "forecast_next_value": forecast,
        "model_coefficients": model.coefficients.toArray().tolist(),
        "model_intercept": model.intercept,
        "training_rmse": rmse,
    }


def risk_signal(
    repo: WarehouseRepository,
    asset_id: str,
    source_id: str,
    indicator: str = "close",
) -> dict[str, Any]:
    points = repo.get_time_series(asset_id, source_id, limit=10000)
    frame = _series_frame(points, indicator)
    if frame is None or frame.count() < 3:
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "indicator": indicator,
            "engine": "apache_spark",
            "risk": "unknown",
            "message": "At least three values are required.",
        }
    _, sf, Window, *_ = _spark_imports()
    window = Window.orderBy("idx")
    returns = (
        frame.withColumn("previous_value", sf.lag("value").over(window))
        .where((sf.col("previous_value").isNotNull()) & (sf.col("previous_value") != 0))
        .withColumn("return", (sf.col("value") - sf.col("previous_value")) / sf.col("previous_value"))
    )
    aggregate = returns.agg(
        sf.stddev_pop("return").alias("volatility"),
        sf.count("return").alias("return_count"),
    ).first()
    volatility = aggregate["volatility"] or 0
    last = returns.orderBy(sf.desc("idx")).select("return").first()
    last_return = last["return"] if last else 0
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
        "engine": "apache_spark",
        "risk": risk,
        "volatility": volatility,
        "last_return": last_return,
        "observations": frame.count(),
        "return_observations": aggregate["return_count"],
    }
