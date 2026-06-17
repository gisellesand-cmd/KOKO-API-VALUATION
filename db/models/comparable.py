from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Text, Boolean, ForeignKey, Numeric, SmallInteger, BigInteger,
    DateTime, Enum, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


SOURCE_PORTAL_ENUM = Enum("inmuebles24", "vivanuncios", name="source_portal")
OPERATION_TYPE_ENUM = Enum("venta", "renta", name="operation_type")
CURRENCY_CODE_ENUM = Enum("MXN", "USD", name="currency_code")


class Comparable(Base):
    __tablename__ = "comparable"
    __table_args__ = (
        Index(
            "ix_comparable_lookup",
            "city_id", "zone_id", "property_type_id", "operation", "active",
        ),
        Index("ix_comparable_scraped_at", "scraped_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(SOURCE_PORTAL_ENUM, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_listing_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=False)
    zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("zone.id"), nullable=True)
    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"), nullable=False)
    operation: Mapped[str] = mapped_column(OPERATION_TYPE_ENUM, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CURRENCY_CODE_ENUM, nullable=False)
    area_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    price_per_m2_mxn: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    bathrooms: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    is_preventa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
