"""Optional Sentry initialization. Call init_sentry() once at app startup."""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

try:
    import sentry_sdk
    from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    _SENTRY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    logger.warning(
        "sentry_sdk is not installed; init_sentry() will be a no-op. "
        "Install with `pip install sentry-sdk` to enable error reporting."
    )
    _SENTRY_AVAILABLE = False

    def init_sentry() -> None:
        """No-op fallback when sentry_sdk is not installed."""
        return None


if _SENTRY_AVAILABLE:

    def init_sentry() -> None:
        """Initialize Sentry SDK if SENTRY_DSN is configured.

        All configuration is read from environment variables. If SENTRY_DSN is
        empty or unset, this function logs a message and returns without
        initializing Sentry. Any errors raised during initialization are caught
        and logged to stderr to ensure Sentry never crashes the application.
        """
        try:
            dsn: str = os.environ.get("SENTRY_DSN", "").strip()
            if not dsn:
                logger.info("Sentry disabled (no DSN)")
                return

            environment: str = os.environ.get(
                "SENTRY_ENVIRONMENT",
                os.environ.get("ENVIRONMENT", "production"),
            )

            traces_sample_rate_raw: str = os.environ.get(
                "SENTRY_TRACES_SAMPLE_RATE", "0.1"
            )
            try:
                traces_sample_rate: float = float(traces_sample_rate_raw)
            except (TypeError, ValueError):
                traces_sample_rate = 0.1

            release: str = os.environ.get(
                "SENTRY_RELEASE",
                os.environ.get("GIT_SHA", "unknown"),
            )

            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                traces_sample_rate=traces_sample_rate,
                profiles_sample_rate=0.1,
                send_default_pii=False,
                attach_stacktrace=True,
                integrations=[
                    FastApiIntegration(),
                    AsyncPGIntegration(),
                    RedisIntegration(),
                ],
            )

            sentry_sdk.set_tag("service", "koko-valuation-api")
        except Exception as exc:  # noqa: BLE001 - never let Sentry crash the app
            print(
                f"[monitoring.sentry] Failed to initialize Sentry: {exc!r}",
                file=sys.stderr,
            )
