from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings


_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    return _client


def get_database() -> Database:
    return get_client()[settings.mongodb_db]


def ensure_indexes(db: Database) -> None:
    db.data_sources.create_index(
        [("source_id", 1), ("valid_from", -1), ("record_kind", 1)],
        unique=True,
        name="uniq_source_version",
    )
    db.data_sources.create_index([("valid_from", -1), ("status", 1)])

    db.assets.create_index(
        [("asset_id", 1), ("valid_from", -1), ("record_kind", 1)],
        unique=True,
        name="uniq_asset_version_or_marker",
    )
    db.assets.create_index([("symbol", 1), ("valid_from", -1)])
    db.assets.create_index("asset_class")

    db.time_series.create_index(
        [("asset_id", 1), ("source_id", 1), ("timestamp", 1), ("ingested_at", -1)]
    )
    db.time_series.create_index(
        [("asset_id", 1), ("source_id", 1), ("timestamp", 1), ("record_kind", 1)],
        unique=True,
        name="uniq_time_series_observation",
    )
    db.time_series.create_index([("source_id", 1), ("timestamp", 1)])
