from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from selectolax.parser import HTMLParser

from scrapers.base import ScrapeError
from scrapers.vivanuncios import VivanunciosScraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def scraper():
    return VivanunciosScraper(bypass_run_throttle=True)


@pytest.fixture
def parsed_payloads(scraper):
    html = (FIXTURES / "vivanuncios_sample.html").read_text(encoding="utf-8")
    tree = HTMLParser(html)
    cards = tree.css("article[data-q='ad-tile']")
    payloads = []
    for card in cards:
        p = scraper._parse_listing_card(card, "cancun", None, "casa", "venta")
        if p is not None:
            payloads.append(p)
    return payloads


def test_parses_4_cards(parsed_payloads):
    assert len(parsed_payloads) == 4
    ids = {p.source_listing_id for p in parsed_payloads}
    assert {
        "VU-AD-900000001",
        "VU-AD-900000002",
        "VU-AD-900000003",
        "VU-AD-900000004",
    } == ids


def test_usd_card_currency(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["VU-AD-900000001"].currency == "MXN"
    assert by_id["VU-AD-900000002"].currency == "USD"
    assert by_id["VU-AD-900000003"].currency == "MXN"
    assert by_id["VU-AD-900000004"].currency == "MXN"


def test_preventa_card_4(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["VU-AD-900000001"].is_preventa is False
    assert by_id["VU-AD-900000002"].is_preventa is False
    assert by_id["VU-AD-900000003"].is_preventa is False
    assert by_id["VU-AD-900000004"].is_preventa is True


def test_area_parsed(parsed_payloads):
    by_id = {p.source_listing_id: p for p in parsed_payloads}
    assert by_id["VU-AD-900000001"].area_m2 == Decimal("300")
    assert by_id["VU-AD-900000002"].area_m2 == Decimal("75")
    assert by_id["VU-AD-900000003"].area_m2 == Decimal("200")
    assert by_id["VU-AD-900000004"].area_m2 == Decimal("90")


def test_renta_operation_passed_through():
    scraper = VivanunciosScraper(bypass_run_throttle=True)
    html = (FIXTURES / "vivanuncios_sample.html").read_text(encoding="utf-8")
    tree = HTMLParser(html)
    cards = tree.css("article[data-q='ad-tile']")
    payloads = [
        scraper._parse_listing_card(c, "tulum", None, "casa", "renta") for c in cards
    ]
    for p in payloads:
        assert p is not None
        assert p.operation == "renta"


def test_rate_limit_throttle_bypass():
    s1 = VivanunciosScraper(bypass_run_throttle=True)
    s1._check_run_throttle()  # should not raise


def test_rate_limit_throttle_active():
    import time
    VivanunciosScraper._last_run_ended_at = time.monotonic()
    s = VivanunciosScraper(bypass_run_throttle=False)
    with pytest.raises(ScrapeError) as exc_info:
        s._check_run_throttle()
    assert exc_info.value.code == "rate_limit_window_active"
    VivanunciosScraper._last_run_ended_at = None


def test_build_url_with_zone(scraper):
    url = scraper._build_search_url("Cancún", None, "casa", "venta", 1)
    assert url == "https://www.vivanuncios.com.mx/s-casas-en-venta/cancun/v1c1098p1"
    url2 = scraper._build_search_url("Cancún", "Zona Hotelera", "departamento", "venta", 2)
    assert url2 == "https://www.vivanuncios.com.mx/s-departamentos-en-venta/zona-hotelera-cancun/v1c1098p2"
