from app.provider_clients import payload_from_stooq_csv
from app.sample_data import ingest_payload, sample_payload


class RecordingRepo:
    def __init__(self):
        self.sources = []
        self.assets = []
        self.points = []

    def insert_source(self, source):
        self.sources.append(source)
        return source.source_id

    def insert_asset(self, asset):
        self.assets.append(asset)
        return asset.asset_id

    def insert_time_series_point(self, point):
        self.points.append(point)
        return f"{point.asset_id}:{point.source_id}:{point.timestamp.isoformat()}"


def test_ingest_payload_validates_and_dispatches_all_sections():
    payload = sample_payload()
    repo = RecordingRepo()

    counts = ingest_payload(repo, payload)

    assert counts == {
        "sources": len(payload.sources),
        "assets": len(payload.assets),
        "time_series": len(payload.time_series),
    }
    assert repo.sources[0].source_id == "nasdaq-demo"
    assert repo.assets[0].asset_id == "asset-msft"
    assert repo.points[0].provenance["dataset"] == "sample_market_data"


def test_sample_payload_normalizes_provider_data_to_schema_models():
    payload = sample_payload()

    assert payload.sources[0].api_url.startswith("https://")
    assert payload.assets[0].asset_class == "stock"
    assert payload.time_series[0].indicators["close"] == 452.3
    assert payload.time_series[0].timestamp.tzinfo is not None


def test_stooq_csv_payload_normalizes_external_provider_rows():
    csv_text = "\n".join(
        [
            "Date,Open,High,Low,Close,Volume",
            "2026-05-01,100.0,103.0,99.5,102.5,15000",
            "2026-05-04,102.5,104.0,101.0,103.25,17500",
        ]
    )

    payload = payload_from_stooq_csv("msft.us", csv_text, limit=1)

    assert payload.sources[0].source_id == "stooq-public"
    assert payload.assets[0].asset_id == "asset-msft-us"
    assert payload.assets[0].attributes["provider"] == "stooq"
    assert len(payload.time_series) == 1
    assert payload.time_series[0].indicators["close"] == 103.25
    assert payload.time_series[0].provenance["symbol"] == "msft.us"
