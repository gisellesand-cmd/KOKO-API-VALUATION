from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_run"
    __table_args__ = (
        Index("ix_scrape_run_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    zone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    property_type: Mapped[str] = mapped_column(String(40), nullable=False)
    operation: Mapped[str] = mapped_column(String(10), nullable=False)
    max_pages: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    listings_scraped: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    listings_inserted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    listings_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    listings_dropped: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )


__all__ = ["ScrapeRun"]
