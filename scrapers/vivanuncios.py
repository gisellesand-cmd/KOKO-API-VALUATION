from __future__ import annotations

# URL pattern: /s-{property-type}-en-{operation}/{location-slug}/v1c1098p{page}
# Free tier enforces a ~1 run / 30 min window; see PRD §8.

import logging
import re
import time
import unicodedata
from typing import ClassVar, Optional
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from scrapers.base import BaseScraper, ListingPayload, ScrapeError

logger = logging.getLogger(__name__)


_PROPERTY_TYPE_SLUG = {
    "casa": "casas",
    "departamento": "departamentos",
    "terreno": "terrenos",
    "local": "locales",
    "oficina": "oficinas",
}

_OPERATION_SLUG = {"venta": "venta", "renta": "renta"}


def _slugify(value: str) -> str:
    if not value:
        return ""
    norm = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    lowered = ascii_only.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lowered)
    return replaced.strip("-")


class VivanunciosScraper(BaseScraper):
    SOURCE_NAME = "vivanuncios"
    MIN_DELAY_SECONDS = 4.0
    MIN_RUN_INTERVAL_SECONDS: ClassVar[float] = 1800.0
    BASE_URL = "https://www.vivanuncios.com.mx"

    _last_run_ended_at: ClassVar[Optional[float]] = None

    def __init__(self, *args, bypass_run_throttle: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.bypass_run_throttle = bypass_run_throttle

    def _build_search_url(
        self,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
        page: int,
    ) -> str:
        pt = _PROPERTY_TYPE_SLUG.get(property_type)
        if pt is None:
            raise ScrapeError("unknown_property_type", property_type=property_type)
        op = _OPERATION_SLUG.get(operation)
        if op is None:
            raise ScrapeError("unknown_operation", operation=operation)
        city_slug = _slugify(city)
        zone_slug = _slugify(zone) if zone else None
        location = f"{zone_slug}-{city_slug}" if zone_slug else city_slug
        base = f"{self.BASE_URL}/s-{pt}-en-{op}/{location}/v1c1098p{page}"
        return base

    def _first_text(self, node: Node, selectors: list[str]) -> Optional[str]:
        for sel in selectors:
            found = node.css_first(sel)
            if found is not None:
                text = found.text(strip=True)
                if text:
                    return text
        return None

    def _first_attr(self, node: Node, selectors: list[str], attr: str) -> Optional[str]:
        for sel in selectors:
            found = node.css_first(sel)
            if found is not None:
                val = found.attributes.get(attr)
                if val:
                    return val
        return None

    def _extract_area(self, features_text: str) -> Optional[str]:
        match = re.search(r"([\d.,]+)\s*m", features_text, flags=re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_bedrooms(self, features_text: str) -> Optional[int]:
        match = re.search(
            r"(\d+)\s*(?:rec|recám|recamar|dorm|habitac)",
            features_text,
            flags=re.IGNORECASE,
        )
        return int(match.group(1)) if match else None

    def _extract_bathrooms(self, features_text: str) -> Optional[int]:
        match = re.search(
            r"(\d+)(?:\.\d+)?\s*baño", features_text, flags=re.IGNORECASE
        )
        return int(match.group(1)) if match else None

    def _parse_listing_card(
        self,
        card: Node,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
    ) -> Optional[ListingPayload]:
        listing_id = (
            card.attributes.get("data-adid")
            or card.attributes.get("data-ad-id")
            or card.attributes.get("data-id")
        )
        if not listing_id:
            self.logger.info(
                "skip card — no listing id",
                extra={"event": "card_skipped", "source": self.SOURCE_NAME},
            )
            return None

        price_text = self._first_text(
            card,
            [
                "div.price",
                "span.ad-price",
                "[class*='price']",
                "[data-q='ad-price']",
            ],
        )
        if not price_text:
            self.logger.info(
                "skip card — no price",
                extra={
                    "event": "card_skipped",
                    "source": self.SOURCE_NAME,
                    "listing_id": listing_id,
                },
            )
            return None
        try:
            price = self._parse_price(price_text)
        except ScrapeError:
            self.logger.info(
                "skip card — unparseable price",
                extra={
                    "event": "card_skipped",
                    "source": self.SOURCE_NAME,
                    "listing_id": listing_id,
                    "price_text": price_text,
                },
            )
            return None

        currency = self._detect_currency(price_text)

        url_path = self._first_attr(
            card,
            ["a[href]", "h2 a", "[data-q='ad-title'] a"],
            "href",
        )
        if not url_path:
            self.logger.info(
                "skip card — no url",
                extra={
                    "event": "card_skipped",
                    "source": self.SOURCE_NAME,
                    "listing_id": listing_id,
                },
            )
            return None
        source_url = urljoin(self.BASE_URL, url_path)

        features_text = " ".join(
            n.text(strip=True)
            for n in card.css(
                "ul.features li, ul.attributes li, [class*='feature'], [class*='attribute']"
            )
        )
        area_raw = self._extract_area(features_text)
        area_m2 = None
        if area_raw:
            try:
                area_m2 = self._parse_price(area_raw)
            except ScrapeError:
                area_m2 = None
        bedrooms = self._extract_bedrooms(features_text)
        bathrooms = self._extract_bathrooms(features_text)

        address = self._first_text(
            card,
            [
                "div.location",
                "[data-q='ad-location']",
                "[class*='location']",
            ],
        )
        title = self._first_text(
            card,
            [
                "h2",
                "h3",
                "[data-q='ad-title']",
                "[class*='title']",
            ],
        )

        combined_text = " ".join(
            filter(None, [title or "", features_text, address or ""])
        )
        is_preventa = self._detect_preventa(combined_text)

        return ListingPayload(
            source=self.SOURCE_NAME,
            source_listing_id=str(listing_id),
            source_url=source_url,
            city=city,
            zone=zone,
            property_type=property_type,
            operation=operation,
            price=price,
            currency=currency,
            area_m2=area_m2,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            address=address,
            title=title,
            is_preventa=is_preventa,
            scraped_at=self._now(),
        )

    def _select_cards(self, html: str) -> list[Node]:
        tree = HTMLParser(html)
        selectors = [
            "article[data-q='ad-tile']",
            "div.tileV2",
            "li.tileV2",
            "div[data-adid]",
            "div.posting-card",
        ]
        for sel in selectors:
            nodes = tree.css(sel)
            if nodes:
                return nodes
        return []

    def _check_run_throttle(self) -> None:
        if self.bypass_run_throttle:
            return
        last = type(self)._last_run_ended_at
        if last is None:
            return
        elapsed = time.monotonic() - last
        if elapsed < self.MIN_RUN_INTERVAL_SECONDS:
            remaining = int(self.MIN_RUN_INTERVAL_SECONDS - elapsed)
            raise ScrapeError(
                "rate_limit_window_active", remaining_seconds=remaining
            )

    async def scrape(
        self,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
        max_pages: int,
    ) -> list[ListingPayload]:
        if max_pages < 1:
            raise ScrapeError("invalid_max_pages", max_pages=max_pages)
        self._check_run_throttle()
        all_payloads: list[ListingPayload] = []
        try:
            for page in range(1, max_pages + 1):
                url = self._build_search_url(
                    city, zone, property_type, operation, page
                )
                self.logger.info(
                    "fetching page",
                    extra={
                        "event": "fetch_page",
                        "source": self.SOURCE_NAME,
                        "url": url,
                        "page": page,
                    },
                )
                resp = await self._fetch(url)
                cards = self._select_cards(resp.text)
                if not cards:
                    if page == 1:
                        raise ScrapeError("no_listings_found", url=url, page=page)
                    self.logger.info(
                        "no more results, stopping pagination",
                        extra={
                            "event": "pagination_end",
                            "source": self.SOURCE_NAME,
                            "page": page,
                        },
                    )
                    break
                page_payloads = []
                for card in cards:
                    payload = self._parse_listing_card(
                        card, city, zone, property_type, operation
                    )
                    if payload is not None:
                        page_payloads.append(payload)
                self.logger.info(
                    "page parsed",
                    extra={
                        "event": "page_parsed",
                        "source": self.SOURCE_NAME,
                        "page": page,
                        "cards_total": len(cards),
                        "cards_valid": len(page_payloads),
                    },
                )
                all_payloads.extend(page_payloads)
        finally:
            # Always update — throttle should apply even on failed runs to avoid hammering.
            type(self)._last_run_ended_at = time.monotonic()
        return all_payloads
