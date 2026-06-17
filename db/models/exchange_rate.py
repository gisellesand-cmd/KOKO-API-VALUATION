from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rate"
    __table_args__ = (
        UniqueConstraint(
            "base_currency", "target_currency", "valid_for_date", "source",
            name="uq_exchange_rate_pair_date_source",
        ),
        Index("ix_exchange_rate_valid_for_date", "valid_for_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MXN")
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False, server_default="banxico")
    valid_for_date: Mapped[date] = mapped_column(Date, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
