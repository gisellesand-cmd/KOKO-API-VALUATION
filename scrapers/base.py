from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import ClassVar, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ListingPayload:
    source: str
    source_listing_id: str
    source_url: str
    city: str
    zone: Optional[str]
    property_type: str
    operation: str
    price: Decimal
    currency: str
    area_m2: Optional[Decimal]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    address: Optional[str]
    title: Optional[str]
    is_preventa: bool
    scraped_at: datetime


class ScrapeError(Exception):
    def __init__(self, code: str, **context):
        super().__init__(code)
        self.code = code
        self.context = context

    def __str__(self) -> str:
        if self.context:
            ctx = " ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.code} {ctx}"
        return self.code


_PREVENTA_PATTERNS = [
    "preventa",
    "pre-venta",
    "pre venta",
    "en desarrollo",
    "en construcción",
    "en construccion",
    "obra blanca",
    "obra gris",
    "entrega 2026",
    "entrega 2027",
    "entrega 2028",
    "entrega 2029",
    "entrega 2030",
]

_USD_MARKERS = ("usd", "us$", "u$s")


class BaseScraper(ABC):
    SOURCE_NAME: ClassVar[str] = ""
    MIN_DELAY_SECONDS: ClassVar[float] = 2.0
    TIMEOUT_SECONDS: ClassVar[float] = 30.0

    USER_AGENTS: ClassVar[list[str]] = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ]

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        logger_: Optional[logging.Logger] = None,
    ):
        self.logger = logger_ or logger
        self._owns_client = client is None
        if client is None:
            ua = random.choice(self.USER_AGENTS)
            self._client = httpx.AsyncClient(
                timeout=self.TIMEOUT_SECONDS,
                follow_redirects=True,
                headers={
                    "User-Agent": ua,
                    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
        else:
            self._client = client
        self._last_request_at: float = 0.0

    async def __aenter__(self) -> "BaseScraper":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @abstractmethod
    async def scrape(
        self,
        city: str,
        zone: Optional[str],
        property_type: str,
        operation: str,
        max_pages: int,
    ) -> list[ListingPayload]:
        ...

    async def _respect_delay(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.MIN_DELAY_SECONDS:
            await asyncio.sleep(self.MIN_DELAY_SECONDS - elapsed)

    async def _fetch(self, url: str, *, attempt: int = 1) -> httpx.Response:
        await self._respect_delay()
        try:
            resp = await self._client.get(url)
            self._last_request_at = time.monotonic()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt < 3:
                backoff = 2 ** (attempt - 1)
                self.logger.warning(
                    "fetch transient failure, retrying",
                    extra={
                        "event": "fetch_retry",
                        "source": self.SOURCE_NAME,
                        "url": url,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(backoff)
                return await self._fetch(url, attempt=attempt + 1)
            raise ScrapeError("network_error", url=url, error=str(exc)) from exc

        if resp.status_code == 429:
            if attempt == 1:
                self.logger.warning(
                    "rate limited, sleeping 60s",
                    extra={"event": "rate_limited", "source": self.SOURCE_NAME, "url": url},
                )
                await asyncio.sleep(60)
                return await self._fetch(url, attempt=attempt + 1)
            raise ScrapeError("rate_limited", url=url)

        if 500 <= resp.status_code < 600:
            if attempt < 3:
                backoff = 2 ** (attempt - 1)
                self.logger.warning(
                    "server error, retrying",
                    extra={
                        "event": "fetch_retry",
                        "source": self.SOURCE_NAME,
                        "url": url,
                        "attempt": attempt,
                        "status": resp.status_code,
                    },
                )
                await asyncio.sleep(backoff)
                return await self._fetch(url, attempt=attempt + 1)
            raise ScrapeError("server_error", url=url, status=resp.status_code)

        if resp.status_code >= 400:
            raise ScrapeError("client_error", url=url, status=resp.status_code)

        return resp

    def _detect_preventa(self, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        return any(p in lowered for p in _PREVENTA_PATTERNS)

    def _detect_currency(self, price_text: str) -> str:
        if not price_text:
            return "MXN"
        lowered = price_text.lower()
        return "USD" if any(m in lowered for m in _USD_MARKERS) else "MXN"

    def _parse_price(self, price_text: str) -> Decimal:
        if not price_text:
            raise ScrapeError("price_unparseable", value=price_text)
        cleaned = re.sub(r"[^\d.,]", "", price_text)
        if not cleaned:
            raise ScrapeError("price_unparseable", value=price_text)
        # If the same separator appears more than once (e.g. "2,703,000"),
        # all instances of it are thousands separators — a number can have at
        # most one decimal point.
        comma_count = cleaned.count(",")
        dot_count = cleaned.count(".")
        if comma_count > 1 and dot_count == 0:
            normalized = cleaned.replace(",", "")
        elif dot_count > 1 and comma_count == 0:
            normalized = cleaned.replace(".", "")
        elif comma_count > 1 and dot_count > 0:
            # comma is thousands, dot is decimal
            normalized = cleaned.replace(",", "")
        elif dot_count > 1 and comma_count > 0:
            # dot is thousands, comma is decimal
            normalized = cleaned.replace(".", "").replace(",", ".")
        else:
            # At most one of each. Last separator wins as decimal,
            # unless it's a comma followed by exactly 3 digits (Mexican thousands).
            last_dot = cleaned.rfind(".")
            last_comma = cleaned.rfind(",")
            if last_dot == -1 and last_comma == -1:
                normalized = cleaned
            elif last_dot > last_comma:
                normalized = cleaned.replace(",", "")
            elif last_comma >= 0 and last_dot == -1 and len(cleaned) - last_comma - 1 == 3:
                # e.g. "2,500" — Mexican thousands separator, not European decimal.
                normalized = cleaned.replace(",", "")
            else:
                normalized = cleaned.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ScrapeError("price_unparseable", value=price_text) from exc

    def _parse_int(self, text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"\d+", text)
        return int(match.group(0)) if match else None

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
