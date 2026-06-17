from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer, Text, ForeignKey, BigInteger, DateTime, Enum, Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


SCRAPE_STATUS_ENUM = Enum("running", "success", "failed", "partial", name="scrape_status")

# Reuse the existing source_portal enum without re-creating the type in DDL.
_SOURCE_PORTAL_REUSE = Enum(
    "inmuebles24", "vivanuncios", name="source_portal", create_type=False
)


class ScrapeRun(Base):
    __tablename__ = "scrape_run"
    __table_args__ = (
        Index("ix_scrape_run_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(_SOURCE_PORTAL_REUSE, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    listings_found: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    listings_new: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    listings_updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(SCRAPE_STATUS_ENUM, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
