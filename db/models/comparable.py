from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.models import Base


class Comparable(Base):
    __tablename__ = "comparables"

    id: Mapped[int] = mapped_column(primary_key=True)
    portal: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("zones.id"), nullable=True, index=True
    )
    property_type_id: Mapped[int] = mapped_column(
        ForeignKey("property_types.id"), index=True
    )
    operation: Mapped[str] = mapped_column(String(10), index=True)
    price_mxn: Mapped[float]
    area_m2: Mapped[float]
    bedrooms: Mapped[int | None]
    bathrooms: Mapped[int | None]
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )


__all__ = ["Comparable"]
