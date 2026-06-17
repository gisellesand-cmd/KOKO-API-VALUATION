from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DISCLAIMER_TEXT = "Esta es una referencia de mercado, no un avalúo profesional."


class ValuationInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    city_slug: str = Field(..., min_length=1, max_length=80)
    zone_slug: Optional[str] = Field(default=None, max_length=80)
    property_type_slug: str = Field(..., min_length=1, max_length=40)
    operation: Literal["venta", "renta"]
    area_m2: float = Field(..., gt=0, le=10000)
    bedrooms: Optional[int] = Field(default=None, ge=0, le=20)
    bathrooms: Optional[int] = Field(default=None, ge=0, le=20)


class ValuationOutput(BaseModel):
    request_id: UUID
    confidence_level: Literal["alta", "media", "baja", "insuficiente"]
    comparables_count: int = Field(..., ge=0)
    geographic_scope: Literal["zone", "city"]
    price_min_mxn: Optional[float] = None
    price_median_mxn: Optional[float] = None
    price_max_mxn: Optional[float] = None
    price_per_m2_median: Optional[float] = None
    methodology_note: str
    computed_at: datetime
    disclaimer: str = DISCLAIMER_TEXT


class CityInfo(BaseModel):
    slug: str
    name: str
    state: str


class ZoneInfo(BaseModel):
    slug: str
    name: str
    city_slug: str


class PropertyTypeInfo(BaseModel):
    slug: str
    name: str


class HealthCheckResult(BaseModel):
    status: Literal["ok", "degraded", "down"]
    db_connected: bool
    comparables_by_city: dict[str, int]
    last_scrape_by_portal: dict[str, Optional[datetime]]
    checked_at: datetime


__all__ = [
    "DISCLAIMER_TEXT",
    "ValuationInput",
    "ValuationOutput",
    "CityInfo",
    "ZoneInfo",
    "PropertyTypeInfo",
    "HealthCheckResult",
]
