from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, ClassVar, Optional

from scrapers.base import BaseScraper, ListingPayload, ScrapeError
from scrapers.inmuebles24 import Inmuebles24Scraper
from scrapers.vivanuncios import VivanunciosScraper

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


_PAGE_FUNCTIONS_DIR = Path(__file__).parent / "page_functions"

# Map our source key -> (page_function file, helper scraper class used for URL building).
# We reuse the URL builders from the existing scrapers so Apify hits the same pages.
_SOURCE_CONFIG = {
    "inmuebles24": {
        "page_function": "inmuebles24.js",
        "url_builder_cls": Inmuebles24Scraper,
    },
    "vivanuncios": {
        "page_function": "vivanuncios.js",
        "url_builder_cls": VivanunciosScraper,
    },
}

# Use apify/playwright-scraper. The other generic actors (web-scraper,
# cheerio-scraper, puppeteer-scraper) all require a one-time human approval
# in the Apify Console ("full-permission-actor-not-approved"); playwright-scraper
# does not, so it's the only one we can launch headlessly. Headless Chromium
# also handles the Cloudflare/anti-bot 403 that blocks httpx.
_ACTOR_ID = "apify/playwright-scraper"

_RUN_TIMEOUT_SECONDS = 300


def _load_page_function(filename: str) -> str:
    path = _PAGE_FUNCTIONS_DIR / filename
    if not path.exists():
        raise ConfigurationError(f"page function file missing: {path}")
    return path.read_text(encoding="utf-8")


class ApifyScraper(BaseScraper):
    """Scrapes via Apify Cloud (apify/web-scraper actor) — bypasses Cloudflare/anti-bot."""

    SOURCE_NAME: ClassVar[str] = "apify"  # overridden per-instance via source_key

    def __init__(
        self,
        source_key: str,
        *,
        token: Optional[str] = None,
        logger_: Optional[logging.Logger] = None,
    ):
        # ApifyScraper does not use httpx — pass a no-op client placeholder by
        # constructing BaseScraper with client=None and immediately closing it.
        super().__init__(client=None, logger_=logger_)
        # Close the httpx client we never use, so we don't leak it.
        # (We still own it; closing here is safe since we never make requests.)
        # The async close happens in our overridden close().
        self._source_key = source_key
        if source_key not in _SOURCE_CONFIG:
            raise ConfigurationError(f"unknown source for Apify: {source_key}")
        self.SOURCE_NAME = source_key  # type: ignore[misc]

        env_token = token or os.environ.get("APIFY_TOKEN")
        if not env_token:
            raise ConfigurationError("APIFY_TOKEN env var is required")
        self._token = env_token

        # Lazy import so the module loads even when apify-client isn't installed
        # in some environments (e.g. test collection).
        try:
            from apify_client import ApifyClientAsync
        except ImportError as exc:
            raise ConfigurationError(
                "apify-client not installed — pip install apify-client"
            ) from exc
        self._client = ApifyClientAsync(env_token)

        # Build a small helper scraper instance just to reuse its URL builder.
        cfg = _SOURCE_CONFIG[source_key]
        # url_builder_cls.__init__ constructs an httpx client we won't use;
        # we accept the tiny overhead since the class is the source of truth
        # for URL slug rules. We close it immediately.
        url_helper = cfg["url_builder_cls"]()
        self._url_builder = url_helper
        self._page_function_src = _load_page_function(cfg["page_function"])

    async def close(self) -> None:
        # Close the unused helper httpx client to avoid warnings.
        try:
            await self._url_builder.close()
        except Exception:
            pass

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

        start_url = self._url_builder._build_search_url(
            city, zone, property_type, operation, 1
        )
        self.logger.info(
            "apify scrape starting",
            extra={
                "event": "apify_start",
                "source": self._source_key,
                "start_url": start_url,
                "max_pages": max_pages,
            },
        )

        run_input: dict[str, Any] = {
            "startUrls": [{"url": start_url, "userData": {"page": 1}}],
            "pageFunction": self._page_function_src,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "MX",
            },
            "launcher": "chromium",
            "headless": True,
            "maxRequestsPerCrawl": max_pages + 2,  # cushion for redirects
            "ignoreSslErrors": True,
            # 'networkidle' never settles on inmuebles24 (heavy trackers) → 60s nav timeout.
            # 'domcontentloaded' fires as soon as the listing markup is parsed.
            "waitUntil": "domcontentloaded",
            "pageLoadTimeoutSecs": 120,
            "navigationTimeoutSecs": 120,
            "maxRequestRetries": 2,
            "customData": {"maxPages": max_pages},
        }

        from datetime import timedelta

        try:
            run = await asyncio.wait_for(
                self._client.actor(_ACTOR_ID).call(
                    run_input=run_input,
                    run_timeout=timedelta(seconds=_RUN_TIMEOUT_SECONDS),
                    memory_mbytes=2048,
                ),
                timeout=_RUN_TIMEOUT_SECONDS + 30,
            )
        except asyncio.TimeoutError as exc:
            raise ScrapeError(
                "apify_run_timeout", actor=_ACTOR_ID, seconds=_RUN_TIMEOUT_SECONDS
            ) from exc
        except Exception as exc:
            raise ScrapeError(
                "apify_call_failed", actor=_ACTOR_ID, error=str(exc)
            ) from exc

        if run is None:
            raise ScrapeError("apify_run_no_response", actor=_ACTOR_ID)

        status = getattr(run, "status", None) or (run.get("status") if isinstance(run, dict) else None)
        run_id = getattr(run, "id", None) or (run.get("id") if isinstance(run, dict) else None)
        if status != "SUCCEEDED":
            raise ScrapeError(
                "apify_run_failed",
                actor=_ACTOR_ID,
                status=status,
                run_id=run_id,
            )

        dataset_id = getattr(run, "default_dataset_id", None) or (run.get("defaultDatasetId") if isinstance(run, dict) else None)
        if not dataset_id:
            raise ScrapeError("apify_no_dataset", actor=_ACTOR_ID, run_id=run_id)

        items_result = await self._client.dataset(dataset_id).list_items()
        if hasattr(items_result, "items"):
            items = items_result.items
        elif isinstance(items_result, dict):
            items = items_result.get("items", [])
        else:
            items = list(items_result) if items_result else []

        self.logger.info(
            "apify scrape finished",
            extra={
                "event": "apify_done",
                "source": self._source_key,
                "run_id": run_id,
                "items": len(items),
            },
        )

        payloads: list[ListingPayload] = []
        for raw in items:
            payload = self._item_to_payload(
                raw, city, zone, property_type, operation
            )
            if payload is not None:
                payloads.append(payload)

        if not payloads:
            raise ScrapeError(
                "no_listings_found",
                source=self._source_key,
                url=start_url,
                items_returned=len(items),
            )

        return payloads

    def _item_to_payload(
        self,
        raw: dict,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
    ) -> Optional[ListingPayload]:
        listing_id = raw.get("source_listing_id")
        source_url = raw.get("source_url")
        price_text = raw.get("price_text")
        if not (listing_id and source_url and price_text):
            self.logger.info(
                "apify item dropped — missing required field",
                extra={
                    "event": "apify_item_dropped",
                    "source": self._source_key,
                    "listing_id": listing_id,
                    "has_url": bool(source_url),
                    "has_price": bool(price_text),
                },
            )
            return None
        try:
            price = self._parse_price(price_text)
        except ScrapeError:
            self.logger.info(
                "apify item dropped — unparseable price",
                extra={
                    "event": "apify_item_dropped",
                    "source": self._source_key,
                    "listing_id": listing_id,
                    "price_text": price_text,
                },
            )
            return None

        currency = self._detect_currency(price_text)
        features_text = raw.get("features_text") or ""

        area_match = re.search(r"([\d.,]+)\s*m", features_text, flags=re.IGNORECASE)
        area_m2 = None
        if area_match:
            try:
                area_m2 = self._parse_price(area_match.group(1))
            except ScrapeError:
                area_m2 = None

        bed_match = re.search(
            r"(\d+)\s*(?:rec|recám|recamar|dorm|habitac)",
            features_text,
            flags=re.IGNORECASE,
        )
        bedrooms = int(bed_match.group(1)) if bed_match else None

        bath_match = re.search(
            r"(\d+)(?:\.\d+)?\s*baño",
            features_text,
            flags=re.IGNORECASE,
        )
        bathrooms = int(bath_match.group(1)) if bath_match else None

        title = raw.get("title")
        address = raw.get("address")
        combined = " ".join(filter(None, [title or "", features_text, address or ""]))
        is_preventa = self._detect_preventa(combined)

        return ListingPayload(
            source=self._source_key,
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
