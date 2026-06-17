"""ValuationResult — frozen output of a single valuation request."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

ConfidenceLevel = Literal["alta", "media", "baja", "insuficiente"]
GeographicScope = Literal["zone", "city"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ValuationResult:
    confidence_level: ConfidenceLevel
    comparables_count: int
    geographic_scope: Optional[GeographicScope]
    price_min_mxn: Optional[float]
    price_median_mxn: Optional[float]
    price_max_mxn: Optional[float]
    price_per_m2_median: Optional[float]
    comparables_used_ids: list[UUID] = field(default_factory=list)
    computed_at: datetime = field(default_factory=_utcnow)
    methodology_note: str = ""
