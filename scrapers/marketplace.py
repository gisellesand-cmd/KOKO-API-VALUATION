"""Facebook Marketplace scraper via Apify actor apify/facebook-marketplace-scraper."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from decimal import Decimal
from typing import ClassVar, Optional

from scrapers.base import BaseScraper, ListingPayload, ScrapeError

logger = logging.getLogger(__name__)

_ACTOR_ID = "apify/facebook-marketplace-scraper"
_RUN_TIMEOUT_SECONDS = 180

_CATEGORY_MAP = {
    "renta": "propertyrentals",
    "venta": "propertyforsale",
}

_CITY_SLUG_TO_FB = {
    "tulum": "tulum",
    "cancun": "cancun",
    "playa-del-carmen": "playa-del-carmen",
    "merida": "merida",
}


class MarketplaceScraper(BaseScraper):
    SOURCE_NAME: ClassVar[str] = "marketplace"

    def __init__(self, *, token: Optional[str] = None, logger_: Optional[logging.Logger] = None):
        super().__init__(client=None, logger_=logger_)
        env_token = token or os.environ.get("APIFY_TOKEN")
        if not env_token:
            raise ScrapeError("apify_token_missing")
        self._token = env_token
        try:
            from apify_client import ApifyClientAsync
        except ImportError as exc:
            raise ScrapeError("apify_client_missing") from exc
        self._apify = ApifyClientAsync(env_token)

    async def scrape(
        self,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
        max_pages: int,
    ) -> list[ListingPayload]:
        fb_city = _CITY_SLUG_TO_FB.get(city, city)
        category = _CATEGORY_MAP.get(operation)
        if not category:
            raise ScrapeError("unknown_operation", operation=operation)

        max_items = max_pages * 30
        url = f"https://www.facebook.com/marketplace/{fb_city}/{category}"

        self.logger.info(
            "marketplace scrape starting",
            extra={"event": "marketplace_start", "url": url, "max_items": max_items},
        )

        run_input = {
            "startUrls": [{"url": url}],
            "maxItems": max_items,
        }

        try:
            run = await asyncio.wait_for(
                self._apify.actor(_ACTOR_ID).call(
                    run_input=run_input,
                    timeout_secs=_RUN_TIMEOUT_SECONDS,
                    memory_mbytes=1024,
                ),
                timeout=_RUN_TIMEOUT_SECONDS + 30,
            )
        except asyncio.TimeoutError as exc:
            raise ScrapeError("marketplace_timeout", seconds=_RUN_TIMEOUT_SECONDS) from exc
        except Exception as exc:
            raise ScrapeError("marketplace_call_failed", error=str(exc)) from exc

        if run is None:
            raise ScrapeError("marketplace_no_response")

        status = run.get("status") if isinstance(run, dict) else getattr(run, "status", None)
        run_id = run.get("id") if isinstance(run, dict) else getattr(run, "id", None)
        if status != "SUCCEEDED":
            raise ScrapeError("marketplace_run_failed", status=status, run_id=run_id)

        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None)
        if not dataset_id:
            raise ScrapeError("marketplace_no_dataset", run_id=run_id)

        items_result = await self._apify.dataset(dataset_id).list_items()
        if hasattr(items_result, "items"):
            items = items_result.items
        elif isinstance(items_result, dict):
            items = items_result.get("items", [])
        else:
            items = list(items_result) if items_result else []

        self.logger.info(
            "marketplace scrape finished",
            extra={"event": "marketplace_done", "run_id": run_id, "items": len(items)},
        )

        payloads: list[ListingPayload] = []
        for raw in items:
            payload = self._item_to_payload(raw, city, zone, property_type, operation)
            if payload is not None:
                payloads.append(payload)

        return payloads

    def _item_to_payload(
        self,
        raw: dict,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
    ) -> Optional[ListingPayload]:
        listing_id = raw.get("id")
        listing_url = raw.get("listingUrl", "")
        if not listing_id or not listing_url:
            return None

        price_data = raw.get("listing_price") or {}
        amount_str = price_data.get("amount")
        if not amount_str:
            return None
        try:
            price = Decimal(amount_str)
        except Exception:
            return None
        if price <= 0:
            return None

        formatted = price_data.get("formatted_amount", "")
        currency = "USD" if "US$" in formatted else "MXN"

        title = raw.get("marketplace_listing_title", "")

        area_m2 = self._extract_area(title)

        bed_match = re.search(r"(\d+)\s*(?:hab|rec|dorm|bedroom)", title, re.IGNORECASE)
        bedrooms = int(bed_match.group(1)) if bed_match else None
        bath_match = re.search(r"(\d+)\s*(?:baño|bath)", title, re.IGNORECASE)
        bathrooms = int(bath_match.group(1)) if bath_match else None

        location = raw.get("location", {})
        reverse = location.get("reverse_geocode", {})
        address = reverse.get("city_page", {}).get("display_name")

        return ListingPayload(
            source="marketplace",
            source_listing_id=str(listing_id),
            source_url=listing_url,
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
            is_preventa=False,
            scraped_at=self._now(),
        )

    def _extract_area(self, text: str) -> Optional[Decimal]:
        match = re.search(r"(\d+)\s*m[²2]", text, re.IGNORECASE)
        if match:
            try:
                return Decimal(match.group(1))
            except Exception:
                pass
        return None
