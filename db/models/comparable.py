from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class Comparable(Base):
    __tablename__ = "comparables"
    __table_args__ = (
        UniqueConstraint(
            "source", "source_listing_id", name="uq_comparable_source_listing"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("city.id"), nullable=False, index=True
    )
    zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("zone.id"), nullable=True, index=True
    )
    property_type_id: Mapped[int] = mapped_column(
        ForeignKey("property_type.id"), nullable=False, index=True
    )
    operation: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    price_original: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency_original: Mapped[str] = mapped_column(String(3), nullable=False)
    price_mxn: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_m2_mxn: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_preventa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", index=True
    )
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["Comparable"]
