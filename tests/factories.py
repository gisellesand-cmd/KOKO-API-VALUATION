"""
factory-boy factories for SQLAlchemy models used in the test suite.

Conventions:
  * All factories share the per-test AsyncSession bound by ``conftest._wire_factories``.
  * Every field can be overridden on instantiation, e.g.::

        ComparableFactory(price=Decimal("9_500_000"), currency="USD")

  * ``ComparableFactory`` derives ``price_per_m2_mxn`` automatically when the
    price is in MXN. For USD prices the derived value is left as ``None`` —
    the valuation core is responsible for FX conversion using ExchangeRate
    rows, and "cero datos inventados" means we never silently guess.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import factory
from factory.alchemy import SQLAlchemyModelFactory

# Models live in `app.models`. We import lazily-friendly via a single import
# block so a missing app package surfaces a clear ImportError when tests run,
# rather than at module import time during collection of unrelated tests.
from app.models import (  # type: ignore
    ApiKey,
    City,
    Comparable,
    ExchangeRate,
    PropertyType,
    Zone,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("ñ", "n")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace(" ", "-")
    )


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# City
# ---------------------------------------------------------------------------


class CityFactory(SQLAlchemyModelFactory):
    class Meta:
        model = City
        sqlalchemy_session = None  # filled in by conftest
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"City {n}")
    slug = factory.LazyAttribute(lambda obj: _slugify(obj.name))


class TulumCityFactory(CityFactory):
    name = "Tulum"
    slug = "tulum"


class CancunCityFactory(CityFactory):
    name = "Cancún"
    slug = "cancun"


class PlayaDelCarmenCityFactory(CityFactory):
    name = "Playa del Carmen"
    slug = "playa-del-carmen"


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------


class ZoneFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Zone
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    city = factory.SubFactory(CityFactory)
    city_id = factory.SelfAttribute("city.id")
    name = factory.Sequence(lambda n: f"Zone {n}")
    slug = factory.LazyAttribute(lambda obj: _slugify(obj.name))


# ---------------------------------------------------------------------------
# PropertyType
# ---------------------------------------------------------------------------


class PropertyTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = PropertyType
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    slug = factory.Iterator(["casa", "departamento", "terreno", "villa"])


# ---------------------------------------------------------------------------
# Comparable
# ---------------------------------------------------------------------------


class ComparableFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Comparable
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)

    city = factory.SubFactory(CityFactory)
    city_id = factory.SelfAttribute("city.id")

    # Zone is nullable; tests can pass zone=None or pass an explicit ZoneFactory().
    zone = factory.SubFactory(ZoneFactory, city=factory.SelfAttribute("..city"))
    zone_id = factory.LazyAttribute(lambda obj: obj.zone.id if obj.zone else None)

    property_type = factory.SubFactory(PropertyTypeFactory)
    property_type_id = factory.SelfAttribute("property_type.id")

    source = factory.Iterator(["inmuebles24", "vivanuncios"])
    source_url = factory.Sequence(lambda n: f"https://example.com/listing/{n}")

    currency = "MXN"
    price = factory.LazyFunction(lambda: Decimal("8_500_000"))
    area_m2 = factory.LazyFunction(lambda: Decimal("200"))
    bedrooms = 3
    bathrooms = 2

    is_preventa = False

    scraped_at = factory.LazyFunction(_utcnow)
    last_seen_at = factory.LazyFunction(_utcnow)

    @factory.lazy_attribute
    def price_per_m2_mxn(self) -> Decimal | None:
        """
        Derived from price/area when currency is MXN. For USD comparables we
        deliberately leave it null — the valuation core converts using an
        ExchangeRate row at query time. NEVER auto-convert here.
        """
        if self.currency != "MXN":
            return None
        if not self.price or not self.area_m2 or Decimal(self.area_m2) == 0:
            return None
        return (Decimal(self.price) / Decimal(self.area_m2)).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# ExchangeRate
# ---------------------------------------------------------------------------


class ExchangeRateFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ExchangeRate
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    currency_pair = "USD_MXN"
    rate = factory.LazyFunction(lambda: Decimal("17.50"))
    as_of = factory.LazyFunction(_utcnow)


# ---------------------------------------------------------------------------
# ApiKey
# ---------------------------------------------------------------------------


class ApiKeyFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ApiKey
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    # By default the factory keys off the literal "test-key-free" string so
    # tests can authenticate predictably using the auth_headers fixture.
    key_hash = factory.LazyFunction(
        lambda: hashlib.sha256(b"test-key-free").hexdigest()
    )
    tier = factory.Iterator(["public", "free", "paid"])
    revoked = False
    label = factory.Sequence(lambda n: f"test-key-{n}")
    owner_email = factory.Sequence(lambda n: f"owner{n}@example.com")


# ---------------------------------------------------------------------------
# Registry used by conftest._wire_factories
# ---------------------------------------------------------------------------


ALL_FACTORIES: tuple[type[SQLAlchemyModelFactory], ...] = (
    CityFactory,
    TulumCityFactory,
    CancunCityFactory,
    PlayaDelCarmenCityFactory,
    ZoneFactory,
    PropertyTypeFactory,
    ComparableFactory,
    ExchangeRateFactory,
    ApiKeyFactory,
)
