"""Mercado Libre Inmuebles scraper — no anti-bot, no Apify needed."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
from decimal import Decimal
from typing import ClassVar, Optional

from selectolax.parser import HTMLParser, Node

from scrapers.base import BaseScraper, ListingPayload, ScrapeError

logger = logging.getLogger(__name__)

_PROPERTY_TYPE_SLUG = {
    "casa": "casas",
    "departamento": "departamentos",
    "terreno": "terrenos",
    "local": "locales-comerciales",
    "oficina": "oficinas",
}

_OPERATION_SLUG = {"venta": "venta", "renta": "renta"}

_CITY_TO_STATE_PATH = {
    "tulum": "quintana-roo/tulum",
    "cancun": "quintana-roo/cancun",
    "playa-del-carmen": "quintana-roo/playa-del-carmen",
    "merida": "yucatan/merida",
    "queretaro": "queretaro/queretaro",
}


def _extract_jsonld_map(tree: HTMLParser) -> dict[str, dict]:
    """Parse JSON-LD scripts and build {MLM-id: structured_data} map."""
    ld_map: dict[str, dict] = {}
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        items: list[dict] = []
        if isinstance(data, list):
            items = [d for d in data if isinstance(d, dict)]
        elif isinstance(data, dict):
            if "@graph" in data:
                items = [d for d in data["@graph"] if isinstance(d, dict)]
            elif data.get("@type") == "ItemList":
                items = [d for d in data.get("itemListElement", []) if isinstance(d, dict)]
            else:
                items = [data]
        for item in items:
            inner = item.get("item", item)
            if not isinstance(inner, dict):
                continue
            url = (
                inner.get("mainEntityOfPage", "")
                or inner.get("url", "")
                or (inner.get("offers", {}) or {}).get("url", "")
                or item.get("url", "")
            )
            mid = re.search(r"MLM-?(\d+)", str(url))
            if mid:
                ld_map[f"MLM-{mid.group(1)}"] = inner
    return ld_map


def _ld_area(ld: dict) -> Optional[Decimal]:
    fs = ld.get("floorSize")
    if isinstance(fs, dict):
        val = fs.get("value")
        if val is not None:
            try:
                return Decimal(str(val))
            except Exception:
                pass
    return None


def _ld_rooms(ld: dict) -> Optional[int]:
    val = ld.get("numberOfRooms")
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return None


def _ld_address(ld: dict) -> Optional[str]:
    addr = ld.get("address")
    if isinstance(addr, dict):
        parts = [
            addr.get("streetAddress"),
            addr.get("addressLocality"),
            addr.get("addressRegion"),
        ]
        joined = ", ".join(p for p in parts if p)
        return joined or None
    if isinstance(addr, str) and addr:
        return addr
    return None


class MercadoLibreScraper(BaseScraper):
    SOURCE_NAME: ClassVar[str] = "mercadolibre"
    MIN_DELAY_SECONDS: ClassVar[float] = 2.0
    BASE_URL = "https://inmuebles.mercadolibre.com.mx"

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
        state_path = _CITY_TO_STATE_PATH.get(city, city)
        url = f"{self.BASE_URL}/{pt}/{op}/{state_path}/"
        if page > 1:
            offset = (page - 1) * 48 + 1
            url += f"_Desde_{offset}_NoIndex_True"
        return url

    def _parse_listing_card(
        self,
        card: Node,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
    ) -> Optional[ListingPayload]:
        link_el = card.css_first("a[href]")
        if not link_el:
            return None
        href = link_el.attributes.get("href", "")
        lid_match = re.search(r"MLM-?(\d+)", href)
        if not lid_match:
            return None
        listing_id = f"MLM-{lid_match.group(1)}"

        price_el = card.css_first("[class*='poly-price__current'] [class*='andes-money-amount__fraction']")
        if not price_el:
            price_el = card.css_first("[class*='price__fraction']")
        if not price_el:
            return None
        price_text = price_el.text(strip=True)
        try:
            price = self._parse_price(price_text)
        except ScrapeError:
            return None

        currency_el = card.css_first("[class*='andes-money-amount__currency-symbol']")
        currency_text = currency_el.text(strip=True) if currency_el else ""
        currency = "USD" if "US" in currency_text else "MXN"

        title_el = card.css_first("[class*='poly-component__title']")
        title = title_el.text(strip=True) if title_el else None

        area_m2 = None
        bedrooms = None
        bathrooms = None
        if title:
            area_match = re.search(r"(\d+)\s*m[²2]", title, re.IGNORECASE)
            if area_match:
                try:
                    area_m2 = self._parse_price(area_match.group(1))
                except ScrapeError:
                    pass
            bed_match = re.search(r"(\d+)\s*(?:rec[aá]mar|hab|dorm|bedroom)", title, re.IGNORECASE)
            if bed_match:
                bedrooms = int(bed_match.group(1))
            bath_match = re.search(r"(\d+)\s*(?:baño|bath)", title, re.IGNORECASE)
            if bath_match:
                bathrooms = int(bath_match.group(1))

        attrs_els = card.css("[class*='poly-attributes-list__item']")
        for attr_el in attrs_els:
            attr_text = attr_el.text(strip=True)
            if not area_m2:
                am = re.search(r"(\d+)\s*m[²2]", attr_text, re.IGNORECASE)
                if am:
                    try:
                        area_m2 = self._parse_price(am.group(1))
                    except ScrapeError:
                        pass
            if bedrooms is None:
                bm = re.search(r"(\d+)\s*(?:rec|hab|dorm)", attr_text, re.IGNORECASE)
                if bm:
                    bedrooms = int(bm.group(1))
            if bathrooms is None:
                btm = re.search(r"(\d+)\s*baño", attr_text, re.IGNORECASE)
                if btm:
                    bathrooms = int(btm.group(1))

        loc_el = card.css_first("[class*='poly-component__location']")
        address = loc_el.text(strip=True) if loc_el else None

        combined = title or ""
        is_preventa = self._detect_preventa(combined)

        return ListingPayload(
            source=self.SOURCE_NAME,
            source_listing_id=listing_id,
            source_url=href.split("?")[0] if href else "",
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

    def _enrich_from_jsonld(
        self, payload: ListingPayload, ld_map: dict[str, dict]
    ) -> ListingPayload:
        ld = ld_map.get(payload.source_listing_id)
        if not ld:
            return payload
        updates: dict = {}
        if not payload.area_m2:
            ld_a = _ld_area(ld)
            if ld_a and ld_a > 0:
                updates["area_m2"] = ld_a
        if payload.bedrooms is None:
            ld_r = _ld_rooms(ld)
            if ld_r is not None:
                updates["bedrooms"] = ld_r
        if not payload.address:
            ld_addr = _ld_address(ld)
            if ld_addr:
                updates["address"] = ld_addr
        if updates:
            return replace(payload, **updates)
        return payload

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
        all_payloads: list[ListingPayload] = []
        enriched_count = 0
        for page in range(1, max_pages + 1):
            url = self._build_search_url(city, zone, property_type, operation, page)
            self.logger.info(
                "fetching page",
                extra={"event": "fetch_page", "source": self.SOURCE_NAME, "url": url, "page": page},
            )
            try:
                resp = await self._fetch(url)
            except ScrapeError as exc:
                if page > 1 and "client_error" in str(exc):
                    self.logger.info(
                        "pagination ended",
                        extra={"event": "pagination_end", "page": page, "reason": str(exc)},
                    )
                    break
                raise
            tree = HTMLParser(resp.text)

            ld_map = _extract_jsonld_map(tree)

            cards = tree.css("li.ui-search-layout__item")
            if not cards:
                if page == 1:
                    raise ScrapeError("no_listings_found", url=url, page=page)
                break
            page_payloads = []
            for card in cards:
                payload = self._parse_listing_card(card, city, zone, property_type, operation)
                if payload is not None:
                    enriched = self._enrich_from_jsonld(payload, ld_map)
                    if enriched is not payload:
                        enriched_count += 1
                    page_payloads.append(enriched)
            self.logger.info(
                "page parsed",
                extra={
                    "event": "page_parsed", "source": self.SOURCE_NAME,
                    "page": page, "cards_total": len(cards), "cards_valid": len(page_payloads),
                    "jsonld_entries": len(ld_map), "enriched": enriched_count,
                },
            )
            all_payloads.extend(page_payloads)
        self.logger.info(
            "scrape complete",
            extra={
                "event": "scrape_done", "source": self.SOURCE_NAME,
                "total": len(all_payloads), "enriched_total": enriched_count,
            },
        )
        return all_payloads
