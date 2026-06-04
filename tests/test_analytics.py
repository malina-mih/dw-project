import pytest

pytest.importorskip("pyspark")

from app import analytics


class FakeRepo:
    def get_time_series(self, asset_id, source_id, start=None, end=None, limit=500):
        return [
            {"indicators": {"close": 100.0}},
            {"indicators": {"close": 105.0}},
            {"indicators": {"close": 103.0}},
            {"indicators": {"close": 110.0}},
        ]


def test_summary_close_values():
    result = analytics.summary(FakeRepo(), "asset-x", "source-y")
    assert result["engine"] == "apache_spark"
    assert result["count"] == 4
    assert result["min"] == 100.0
    assert result["max"] == 110.0


def test_forecast_uses_spark_mllib_linear_regression():
    result = analytics.next_value_forecast(FakeRepo(), "asset-x", "source-y")
    assert result["engine"] == "apache_spark"
    assert result["method"] == "spark_mllib_linear_regression"
    assert result["forecast_next_value"] == pytest.approx(111.5, abs=0.01)
