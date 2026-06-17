from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Text, ForeignKey, Numeric, SmallInteger, BigInteger, DateTime, Enum, func,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


_OPERATION_REUSE = Enum("venta", "renta", name="operation_type", create_type=False)


class ValuationRequest(Base):
    __tablename__ = "valuation_request"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"), nullable=False)
    zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("zone.id"), nullable=True)
    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"), nullable=False)
    operation: Mapped[str] = mapped_column(_OPERATION_REUSE, nullable=False)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    bedrooms: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    bathrooms: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 1), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    client_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
