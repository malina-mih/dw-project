from datetime import datetime, timezone
from typing import Any, Iterable

from pymongo.errors import DuplicateKeyError
from pymongo.database import Database

from app.schemas import AssetDeactivateIn, AssetIn, DataSourceIn, TimeSeriesPointIn


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def clean_docs(docs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [clean_doc(doc) for doc in docs]


class WarehouseRepository:
    def __init__(self, db: Database):
        self.db = db

    def _insert_or_existing_id(self, collection, identity: dict[str, Any], doc: dict[str, Any]) -> str:
        existing = collection.find_one(identity, {"_id": 1})
        if existing:
            return str(existing["_id"])
        try:
            result = collection.insert_one(doc)
            return str(result.inserted_id)
        except DuplicateKeyError:
            existing = collection.find_one(identity, {"_id": 1})
            if existing:
                return str(existing["_id"])
            raise

    def insert_source(self, source: DataSourceIn) -> str:
        now = utc_now()
        doc = source.model_dump()
        doc["valid_from"] = source.valid_from or now
        doc["ingested_at"] = now
        doc["status"] = "active"
        doc["record_kind"] = "version"
        identity = {
            "source_id": doc["source_id"],
            "valid_from": doc["valid_from"],
            "record_kind": doc["record_kind"],
        }
        return self._insert_or_existing_id(self.db.data_sources, identity, doc)

    def insert_asset(self, asset: AssetIn) -> str:
        now = utc_now()
        doc = asset.model_dump(by_alias=True)
        doc["asset_class"] = doc.pop("class")
        doc["valid_from"] = asset.valid_from or now
        doc["ingested_at"] = now
        doc["status"] = "active"
        doc["record_kind"] = "version"
        identity = {
            "asset_id": doc["asset_id"],
            "valid_from": doc["valid_from"],
            "record_kind": doc["record_kind"],
        }
        return self._insert_or_existing_id(self.db.assets, identity, doc)

    def deactivate_asset(self, asset_id: str, marker: AssetDeactivateIn) -> str:
        doc = {
            "asset_id": asset_id,
            "valid_from": marker.valid_from,
            "ingested_at": utc_now(),
            "status": "inactive",
            "record_kind": "availability_marker",
            "reason": marker.reason,
        }
        identity = {
            "asset_id": doc["asset_id"],
            "valid_from": doc["valid_from"],
            "record_kind": doc["record_kind"],
        }
        return self._insert_or_existing_id(self.db.assets, identity, doc)

    def insert_time_series_point(self, point: TimeSeriesPointIn) -> str:
        doc = point.model_dump()
        doc["ingested_at"] = utc_now()
        doc["record_kind"] = "observation"
        identity = {
            "asset_id": doc["asset_id"],
            "source_id": doc["source_id"],
            "timestamp": doc["timestamp"],
            "record_kind": doc["record_kind"],
        }
        return self._insert_or_existing_id(self.db.time_series, identity, doc)

    def list_sources(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if as_of:
            query["valid_from"] = {"$lte": as_of}
        docs = list(self.db.data_sources.find(query).sort("valid_from", -1))
        latest: dict[str, dict[str, Any]] = {}
        for doc in docs:
            if doc["source_id"] not in latest:
                latest[doc["source_id"]] = doc
        return clean_docs(latest.values())

    def get_source(self, source_id: str, as_of: datetime | None = None) -> dict[str, Any] | None:
        query: dict[str, Any] = {"source_id": source_id}
        if as_of:
            query["valid_from"] = {"$lte": as_of}
        doc = self.db.data_sources.find_one(query, sort=[("valid_from", -1)])
        return clean_doc(doc) if doc else None

    def list_assets(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if as_of:
            query["valid_from"] = {"$lte": as_of}
        docs = list(self.db.assets.find(query).sort("valid_from", -1))
        latest: dict[str, dict[str, Any]] = {}
        for doc in docs:
            asset_id = doc["asset_id"]
            if asset_id not in latest and doc.get("status") == "active":
                latest[asset_id] = doc
            elif asset_id not in latest:
                latest[asset_id] = doc
        return clean_docs(doc for doc in latest.values() if doc.get("status") == "active")

    def get_asset(self, asset_id: str, as_of: datetime | None = None) -> dict[str, Any] | None:
        query: dict[str, Any] = {"asset_id": asset_id}
        if as_of:
            query["valid_from"] = {"$lte": as_of}
        doc = self.db.assets.find_one(query, sort=[("valid_from", -1)])
        if not doc or doc.get("status") != "active":
            return None
        return clean_doc(doc)

    def get_asset_history(self, asset_id: str) -> list[dict[str, Any]]:
        docs = self.db.assets.find({"asset_id": asset_id}).sort("valid_from", 1)
        return clean_docs(docs)

    def get_time_series(
        self,
        asset_id: str,
        source_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"asset_id": asset_id, "source_id": source_id}
        if start or end:
            query["timestamp"] = {}
            if start:
                query["timestamp"]["$gte"] = start
            if end:
                query["timestamp"]["$lte"] = end
        docs = self.db.time_series.find(query).sort("timestamp", 1).limit(limit)
        return clean_docs(docs)

    def time_series_details(self, asset_id: str, source_id: str) -> dict[str, Any]:
        query = {"asset_id": asset_id, "source_id": source_id}
        first = self.db.time_series.find_one(query, sort=[("timestamp", 1)])
        last = self.db.time_series.find_one(query, sort=[("timestamp", -1)])
        count = self.db.time_series.count_documents(query)
        fields = set()
        for doc in self.db.time_series.find(query, {"indicators": 1}).limit(5000):
            fields.update(doc.get("indicators", {}).keys())
        return {
            "asset_id": asset_id,
            "source_id": source_id,
            "count": count,
            "first_timestamp": first["timestamp"] if first else None,
            "last_timestamp": last["timestamp"] if last else None,
            "indicator_fields": sorted(fields),
        }
