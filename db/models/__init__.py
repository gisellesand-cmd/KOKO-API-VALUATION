"""STUB — replace with real models from the DB specialist's branch.

The fields here reflect the contract expected by `valuation.queries` and the
test fixtures. The DB schema is owned by another specialist; this module exists
only so the valuation module is importable and unit-testable in isolation
(against an in-memory aiosqlite database).

When the real `db/models/` lands, delete this stub and re-export the canonical
models. Keep the public names (Base, Comparable, City, Zone, PropertyType) and
the field names listed below stable, or update `valuation.queries` accordingly.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    _UUID_TYPE = PGUUID(as_uuid=True)
except ImportError:  # pragma: no cover - sqlite-only environments
    _UUID_TYPE = String(36)


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, ForeignKey("cities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class PropertyType(Base):
    __tablename__ = "property_types"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class Comparable(Base):
    __tablename__ = "comparables"

    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, ForeignKey("cities.id"), nullable=False)
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        _UUID_TYPE, ForeignKey("zones.id"), nullable=True
    )
    property_type_id: Mapped[uuid.UUID] = mapped_column(
        _UUID_TYPE, ForeignKey("property_types.id"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    price_per_m2_mxn: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MXN")
    is_preventa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


__all__ = ["Base", "City", "Zone", "PropertyType", "Comparable"]
