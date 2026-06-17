from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(80))

    zones: Mapped[list["Zone"]] = relationship(
        back_populates="city",
        cascade="all, delete-orphan",
    )


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(160))
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)

    city: Mapped["City"] = relationship(back_populates="zones")


class PropertyType(Base):
    __tablename__ = "property_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))


__all__ = ["City", "Zone", "PropertyType"]
