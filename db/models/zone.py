from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin


class Zone(Base, TimestampMixin):
    __tablename__ = "zone"
    __table_args__ = (
        UniqueConstraint("city_id", "slug", name="uq_zone_city_slug"),
        Index("ix_zone_city_id", "city_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("city.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
