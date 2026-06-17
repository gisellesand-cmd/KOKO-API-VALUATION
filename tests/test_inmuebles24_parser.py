from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from scrapers.inmuebles24 import Inmuebles24Scraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def scraper():
    return Inmuebles24Scraper()


@pytest.fixture
def parsed_payloads(scraper):
    html = (FIXTURES / "inmuebles24_sample.html").read_text(encoding="utf-8")
    tree = HTMLParser(html)
    cards = tree.css("div[data-posting-type]")
    payloads = []
    for card in cards:
        p = scraper._parse_listing_card(card, "tulum", None, "casa", "venta")
        if p is not None:
            payloads.append(p)
    return payloads


def test_parses_3_valid_cards_drops_card_without_price(parsed_payloads):
    assert len(parsed_payloads) == 3
    ids = {p.source_listing_id for p in parsed_payloads}
    assert "MX-NID-100000001" in ids
    assert "MX-NID-100000002" in ids
    assert "MX-NID-100000003" in ids
    assert "MX-NID-100000004" not in ids


def test_currency_detection_per_card(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["MX-NID-100000001"].currency == "MXN"
    assert by_id["MX-NID-100000002"].currency == "USD"
    assert by_id["MX-NID-100000003"].currency == "MXN"


def test_preventa_flag(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["MX-NID-100000001"].is_preventa is False
    assert by_id["MX-NID-100000002"].is_preventa is False
    assert by_id["MX-NID-100000003"].is_preventa is True


def test_required_fields_present(parsed_payloads):
    for p in parsed_payloads:
        assert p.source_listing_id
        assert p.source_url.startswith("https://www.inmuebles24.com/")
        assert p.price > 0


def test_area_parsed_when_present(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["MX-NID-100000001"].area_m2 == Decimal("250")
    assert by_id["MX-NID-100000002"].area_m2 == Decimal("95")
    assert by_id["MX-NID-100000003"].area_m2 == Decimal("110")


def test_build_url_pagination(scraper):
    p1 = scraper._build_search_url("Tulum", None, "casa", "venta", 1)
    p2 = scraper._build_search_url("Tulum", None, "casa", "venta", 2)
    assert p1 == "https://www.inmuebles24.com/casas-en-venta-en-tulum.html"
    assert p2 == "https://www.inmuebles24.com/casas-en-venta-en-tulum-pagina-2.html"


def test_build_url_with_zone(scraper):
    url = scraper._build_search_url("Tulum", "Aldea Zamá", "departamento", "venta", 1)
    assert url == "https://www.inmuebles24.com/departamentos-en-venta-en-aldea-zama-tulum.html"
