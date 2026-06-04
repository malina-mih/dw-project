from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pymongo.database import Database

from app import analytics
from app.config import settings
from app.database import ensure_indexes, get_database
from app.repository import WarehouseRepository
from app.sample_data import ingest_payload, sample_payload
from app.schemas import AssetDeactivateIn, IngestPayload


app = FastAPI(title=settings.api_title, version=settings.api_version)


def get_repo(db: Database = Depends(get_database)) -> WarehouseRepository:
    return WarehouseRepository(db)


@app.on_event("startup")
def startup() -> None:
    ensure_indexes(get_database())


@app.get("/health")
def health(db: Database = Depends(get_database)) -> dict[str, str]:
    db.client.admin.command("ping")
    return {"status": "ok", "database": settings.mongodb_db}


@app.post("/ingest")
def ingest(payload: IngestPayload, repo: WarehouseRepository = Depends(get_repo)) -> dict[str, int]:
    return ingest_payload(repo, payload)


@app.post("/ingest/sample")
def ingest_sample(repo: WarehouseRepository = Depends(get_repo)) -> dict[str, int]:
    return ingest_payload(repo, sample_payload())


@app.get("/assets")
def list_assets(
    as_of: datetime | None = Query(default=None),
    repo: WarehouseRepository = Depends(get_repo),
) -> list[dict]:
    return repo.list_assets(as_of=as_of)


@app.get("/assets/{asset_id}")
def get_asset(
    asset_id: str,
    as_of: datetime | None = Query(default=None),
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    asset = repo.get_asset(asset_id, as_of=as_of)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found for the requested time.")
    return asset


@app.get("/assets/{asset_id}/history")
def get_asset_history(asset_id: str, repo: WarehouseRepository = Depends(get_repo)) -> list[dict]:
    return repo.get_asset_history(asset_id)


@app.post("/assets/{asset_id}/deactivate")
def deactivate_asset(
    asset_id: str,
    marker: AssetDeactivateIn,
    repo: WarehouseRepository = Depends(get_repo),
) -> dict[str, str]:
    inserted_id = repo.deactivate_asset(asset_id, marker)
    return {"inserted_id": inserted_id, "asset_id": asset_id, "status": "inactive"}


@app.get("/sources")
def list_sources(
    as_of: datetime | None = Query(default=None),
    repo: WarehouseRepository = Depends(get_repo),
) -> list[dict]:
    return repo.list_sources(as_of=as_of)


@app.get("/sources/{source_id}")
def get_source(
    source_id: str,
    as_of: datetime | None = Query(default=None),
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    source = repo.get_source(source_id, as_of=as_of)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return source


@app.get("/timeseries/{asset_id}/{source_id}")
def get_time_series(
    asset_id: str,
    source_id: str,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=10000),
    repo: WarehouseRepository = Depends(get_repo),
) -> list[dict]:
    return repo.get_time_series(asset_id, source_id, start=start, end=end, limit=limit)


@app.get("/timeseries/{asset_id}/{source_id}/details")
def get_time_series_details(
    asset_id: str,
    source_id: str,
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    return repo.time_series_details(asset_id, source_id)


@app.get("/analytics/summary")
def analytics_summary(
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    return analytics.summary(repo, asset_id, source_id, indicator, start, end)


@app.get("/analytics/trend")
def analytics_trend(
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    return analytics.trend(repo, asset_id, source_id, indicator)


@app.get("/analytics/forecast")
def analytics_forecast(
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    return analytics.next_value_forecast(repo, asset_id, source_id, indicator)


@app.get("/analytics/risk")
def analytics_risk(
    asset_id: str,
    source_id: str,
    indicator: str = "close",
    repo: WarehouseRepository = Depends(get_repo),
) -> dict:
    return analytics.risk_signal(repo, asset_id, source_id, indicator)
