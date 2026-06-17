from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""

    pass


from db.models.catalog import City, PropertyType, Zone  # noqa: E402
from db.models.comparable import Comparable  # noqa: E402
from db.models.scrape_log import ScrapeLog  # noqa: E402
from db.models.valuation import ValuationRequest, ValuationResponse  # noqa: E402

__all__ = [
    "Base",
    "City",
    "Zone",
    "PropertyType",
    "Comparable",
    "ValuationRequest",
    "ValuationResponse",
    "ScrapeLog",
]
