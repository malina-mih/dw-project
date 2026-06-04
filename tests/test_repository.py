from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from app.repository import WarehouseRepository
from app.schemas import AssetDeactivateIn, AssetIn, DataSourceIn, TimeSeriesPointIn


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def matches_query(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        actual = doc.get(key)
        if isinstance(expected, dict):
            if "$lte" in expected and not actual <= expected["$lte"]:
                return False
            if "$gte" in expected and not actual >= expected["$gte"]:
                return False
        elif actual != expected:
            return False
    return True


def apply_projection(doc: dict[str, Any], projection: dict[str, int] | None) -> dict[str, Any]:
    if not projection:
        return deepcopy(doc)
    return {key: deepcopy(doc[key]) for key, include in projection.items() if include and key in doc}


class Cursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self.docs = docs

    def sort(self, key_or_list, direction: int | None = None):
        sort_fields = key_or_list if isinstance(key_or_list, list) else [(key_or_list, direction or 1)]
        for key, sort_direction in reversed(sort_fields):
            self.docs.sort(key=lambda doc: doc.get(key), reverse=sort_direction < 0)
        return self

    def limit(self, limit: int):
        self.docs = self.docs[:limit]
        return self

    def __iter__(self):
        return iter(deepcopy(self.docs))


class Collection:
    def __init__(self):
        self.docs: list[dict[str, Any]] = []
        self.next_id = 1

    def insert_one(self, doc: dict[str, Any]):
        stored = deepcopy(doc)
        stored["_id"] = self.next_id
        self.next_id += 1
        self.docs.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def find_one(
        self,
        query: dict[str, Any],
        projection: dict[str, int] | None = None,
        sort: list[tuple[str, int]] | None = None,
    ):
        docs = [doc for doc in self.docs if matches_query(doc, query)]
        if sort:
            docs = list(Cursor(docs).sort(sort).docs)
        return apply_projection(docs[0], projection) if docs else None

    def find(self, query: dict[str, Any], projection: dict[str, int] | None = None):
        docs = [apply_projection(doc, projection) for doc in self.docs if matches_query(doc, query)]
        return Cursor(docs)

    def count_documents(self, query: dict[str, Any]) -> int:
        return len([doc for doc in self.docs if matches_query(doc, query)])


class Db:
    def __init__(self):
        self.assets = Collection()
        self.data_sources = Collection()
        self.time_series = Collection()


def test_asset_save_find_latest_and_history():
    repo = WarehouseRepository(Db())
    repo.insert_asset(
        AssetIn(
            asset_id="asset-msft",
            symbol="MSFT",
            name="Microsoft Corporation",
            **{"class": "stock"},
            region="US",
            valid_from=dt("2026-01-01T00:00:00"),
        )
    )
    repo.insert_asset(
        AssetIn(
            asset_id="asset-msft",
            symbol="MSFT",
            name="Microsoft Corp Updated",
            **{"class": "stock"},
            region="US",
            valid_from=dt("2026-02-01T00:00:00"),
        )
    )

    latest = repo.get_asset("asset-msft")
    assert latest["name"] == "Microsoft Corp Updated"
    assert latest["asset_class"] == "stock"
    assert repo.get_asset("asset-msft", as_of=dt("2026-01-15T00:00:00"))["name"] == "Microsoft Corporation"
    assert [item["name"] for item in repo.get_asset_history("asset-msft")] == [
        "Microsoft Corporation",
        "Microsoft Corp Updated",
    ]


def test_list_assets_hides_inactive_latest_marker_and_paginates():
    repo = WarehouseRepository(Db())
    for symbol in ("AAA", "BBB", "CCC"):
        repo.insert_asset(
            AssetIn(
                asset_id=f"asset-{symbol.lower()}",
                symbol=symbol,
                name=f"{symbol} Inc",
                **{"class": "stock"},
                region="US",
                valid_from=dt("2026-01-01T00:00:00"),
            )
        )
    repo.deactivate_asset(
        "asset-bbb",
        AssetDeactivateIn(valid_from=dt("2026-02-01T00:00:00"), reason="delisted"),
    )

    assets = repo.list_assets(offset=0, limit=10)
    assert {asset["asset_id"] for asset in assets} == {"asset-aaa", "asset-ccc"}
    assert len(repo.list_assets(offset=1, limit=1)) == 1
    assert repo.get_asset("asset-bbb") is None


def test_source_save_find_latest_and_list_all():
    repo = WarehouseRepository(Db())
    repo.insert_source(
        DataSourceIn(
            source_id="nasdaq-demo",
            name="Nasdaq Demo",
            vendor_type="sample",
            valid_from=dt("2026-01-01T00:00:00"),
        )
    )
    repo.insert_source(
        DataSourceIn(
            source_id="nasdaq-demo",
            name="Nasdaq Demo Updated",
            vendor_type="sample",
            valid_from=dt("2026-02-01T00:00:00"),
        )
    )

    assert repo.get_source("nasdaq-demo")["name"] == "Nasdaq Demo Updated"
    assert repo.get_source("nasdaq-demo", as_of=dt("2026-01-15T00:00:00"))["name"] == "Nasdaq Demo"
    assert [source["source_id"] for source in repo.list_sources()] == ["nasdaq-demo"]


def test_time_series_save_find_all_and_idempotency():
    repo = WarehouseRepository(Db())
    point = TimeSeriesPointIn(
        asset_id="asset-msft",
        source_id="nasdaq-demo",
        timestamp=dt("2026-05-01T00:00:00"),
        indicators={"close": 100.0},
    )

    first_id = repo.insert_time_series_point(point)
    second_id = repo.insert_time_series_point(point)

    assert first_id == second_id
    series = repo.get_time_series("asset-msft", "nasdaq-demo")
    assert len(series) == 1
    assert series[0]["indicators"]["close"] == 100.0
    assert repo.time_series_details("asset-msft", "nasdaq-demo")["indicator_fields"] == ["close"]
