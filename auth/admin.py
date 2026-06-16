"""Admin CLI for managing API keys.

Usage::

    python -m auth.admin create-key --name "KOKO Landing" --tier paid
    python -m auth.admin list-keys
    python -m auth.admin revoke-key 42
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from auth.api_key import generate_api_key

_TIER_DEFAULT_REQUESTS = {"free": 100, "paid": 10000}
_VALID_TIERS = tuple(_TIER_DEFAULT_REQUESTS.keys())
_PREFIX_LEN = 12


def _import_db():
    try:
        from sqlalchemy import select

        from db.models.api_key import ApiKey
        from db.session import get_db_session
    except ImportError:
        print(
            "Auth admin CLI requires db.session and db.models.api_key — "
            "wire those up first.",
            file=sys.stderr,
        )
        sys.exit(2)
    return ApiKey, get_db_session, select


async def _session_ctx(get_db_session):
    # get_db_session is an async generator dependency; drive it manually so
    # we get a real session here.
    agen = get_db_session()
    session = await agen.__anext__()
    return agen, session


async def _create_key(name: str, tier: str, requests_per_day: int | None) -> int:
    if tier not in _VALID_TIERS:
        print(f"Invalid tier '{tier}'. Must be one of: {', '.join(_VALID_TIERS)}", file=sys.stderr)
        return 1
    rpd = requests_per_day if requests_per_day is not None else _TIER_DEFAULT_REQUESTS[tier]

    ApiKey, get_db_session, _ = _import_db()
    agen, session = await _session_ctx(get_db_session)
    try:
        plain, hashed = await generate_api_key()
        prefix = plain[:_PREFIX_LEN] + "..."
        row = ApiKey(
            name=name,
            key_hash=hashed,
            key_prefix=prefix,
            tier=tier,
            requests_per_day=rpd,
            active=True,
            revoked_at=None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        print("API key created.\n")
        print(f"  Name:   {name}")
        print(f"  Tier:   {tier}")
        print(f"  ID:     {row.id}")
        print(f"  Prefix: {prefix}\n")
        print("  Plain key (shown once, store it now):")
        print(f"  {plain}\n")
        print("Store this securely - it cannot be retrieved later.")
        return 0
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass


async def _list_keys() -> int:
    ApiKey, get_db_session, select = _import_db()
    agen, session = await _session_ctx(get_db_session)
    try:
        result = await session.execute(select(ApiKey).order_by(ApiKey.id))
        rows = list(result.scalars())
        header = f"{'ID':>4}  {'NAME':<30}  {'TIER':<6}  {'PREFIX':<20}  {'ACTIVE':<6}  {'CREATED':<19}  REVOKED_AT"
        print(header)
        print("-" * len(header))
        for r in rows:
            name = (r.name or "")[:30]
            prefix = getattr(r, "key_prefix", "") or ""
            created = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            revoked = r.revoked_at.strftime("%Y-%m-%d %H:%M:%S") if r.revoked_at else "-"
            print(
                f"{r.id:>4}  {name:<30}  {r.tier:<6}  {prefix:<20}  "
                f"{str(bool(r.active)):<6}  {created:<19}  {revoked}"
            )
        if not rows:
            print("(no keys)")
        return 0
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass


async def _revoke_key(key_id: int) -> int:
    ApiKey, get_db_session, select = _import_db()
    agen, session = await _session_ctx(get_db_session)
    try:
        result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
        row = result.scalar_one_or_none()
        if row is None:
            print(f"Key id={key_id} not found.", file=sys.stderr)
            return 1
        row.active = False
        row.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"Revoked key id={row.id} (name={row.name})")
        return 0
    finally:
        try:
            await agen.aclose()
        except Exception:
            pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auth.admin", description="Manage API keys.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-key", help="Create a new API key.")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--tier", required=True, choices=_VALID_TIERS)
    p_create.add_argument("--requests-per-day", type=int, default=None)

    sub.add_parser("list-keys", help="List all API keys.")

    p_revoke = sub.add_parser("revoke-key", help="Revoke an API key by id.")
    p_revoke.add_argument("id", type=int)

    return parser


async def _main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "create-key":
            return await _create_key(args.name, args.tier, args.requests_per_day)
        if args.command == "list-keys":
            return await _list_keys()
        if args.command == "revoke-key":
            return await _revoke_key(args.id)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
