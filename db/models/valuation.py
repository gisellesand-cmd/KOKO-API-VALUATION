from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class ValuationRequest(Base):
    __tablename__ = "valuation_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    city_id: Mapped[int]
    zone_id: Mapped[int | None]
    property_type_id: Mapped[int]
    operation: Mapped[str] = mapped_column(String(10))
    area_m2: Mapped[float]
    bedrooms: Mapped[int | None]
    bathrooms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ValuationResponse(Base):
    __tablename__ = "valuation_responses"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("valuation_requests.id"),
        index=True,
    )
    confidence_level: Mapped[str] = mapped_column(String(20))
    comparables_count: Mapped[int]
    geographic_scope: Mapped[str] = mapped_column(String(10))
    comparable_ids: Mapped[list[int]] = mapped_column(JSON)
    price_min_mxn: Mapped[float | None]
    price_median_mxn: Mapped[float | None]
    price_max_mxn: Mapped[float | None]
    price_per_m2_median: Mapped[float | None]
    methodology_note: Mapped[str] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


__all__ = ["ValuationRequest", "ValuationResponse"]
