from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin


class City(Base, TimestampMixin):
    __tablename__ = "city"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, server_default="MX")
    state: Mapped[str] = mapped_column(String(80), nullable=False, server_default="Quintana Roo")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
