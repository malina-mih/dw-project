from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataSourceIn(BaseModel):
    source_id: str
    name: str
    vendor_type: str = "sample"
    api_url: str | None = None
    license: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None


class AssetIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str
    symbol: str
    name: str
    asset_class: str = Field(alias="class")
    region: str
    currency: str | None = None
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None


class TimeSeriesPointIn(BaseModel):
    asset_id: str
    source_id: str
    timestamp: datetime
    indicators: dict[str, Any]
    quality: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class AssetDeactivateIn(BaseModel):
    valid_from: datetime
    reason: str = "not available anymore"


class IngestPayload(BaseModel):
    sources: list[DataSourceIn] = Field(default_factory=list)
    assets: list[AssetIn] = Field(default_factory=list)
    time_series: list[TimeSeriesPointIn] = Field(default_factory=list)
