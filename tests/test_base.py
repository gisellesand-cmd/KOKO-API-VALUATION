from __future__ import annotations

from decimal import Decimal

import pytest

from scrapers.base import BaseScraper, ScrapeError


class _DummyScraper(BaseScraper):
    SOURCE_NAME = "test"

    async def scrape(self, city, zone, property_type, operation, max_pages):
        return []


@pytest.fixture
def scraper():
    return _DummyScraper()


def test_detect_preventa_matches_known_phrases(scraper):
    assert scraper._detect_preventa("Preventa Entrega 2028") is True
    assert scraper._detect_preventa("Proyecto en desarrollo") is True
    assert scraper._detect_preventa("Obra Gris en venta") is True
    assert scraper._detect_preventa("OBRA BLANCA") is True
    assert scraper._detect_preventa("Casa lista para habitar") is False
    assert scraper._detect_preventa("Departamento amueblado") is False
    assert scraper._detect_preventa("") is False


def test_detect_currency_usd(scraper):
    assert scraper._detect_currency("USD 150,000") == "USD"
    assert scraper._detect_currency("US$ 150,000") == "USD"
    assert scraper._detect_currency("u$s 150") == "USD"
    assert scraper._detect_currency("$4,500,000") == "MXN"
    assert scraper._detect_currency("$ 4.500.000 MXN") == "MXN"
    assert scraper._detect_currency("") == "MXN"


def test_parse_price_strips_formatting(scraper):
    assert scraper._parse_price("$4,500,000") == Decimal("4500000")
    assert scraper._parse_price("USD 185,000.50") == Decimal("185000.50")
    assert scraper._parse_price("$ 35.000 / mes") == Decimal("35000")
    assert scraper._parse_price("$2,900,000") == Decimal("2900000")


def test_parse_price_raises_when_no_digits(scraper):
    with pytest.raises(ScrapeError):
        scraper._parse_price("Consultar precio")
    with pytest.raises(ScrapeError):
        scraper._parse_price("")


def test_parse_int_returns_first(scraper):
    assert scraper._parse_int("3 recámaras") == 3
    assert scraper._parse_int("2.5 baños") == 2
    assert scraper._parse_int("—") is None
    assert scraper._parse_int(None) is None
    assert scraper._parse_int("") is None
