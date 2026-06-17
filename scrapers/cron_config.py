from __future__ import annotations

# Vivanuncios free tier permits ~1 run / 30 min — the schedule is sized accordingly.

from typing import TypedDict


class ScrapeJob(TypedDict):
    cron: str
    source: str
    city: str
    zone: str | None
    property_type: str
    operation: str
    pages: int
    notes: str


_CITIES = ["tulum", "cancun", "playa-del-carmen"]
_PROPERTY_TYPES = ["casa", "departamento"]
_OPERATIONS = ["venta", "renta"]


def _build_inmuebles24_jobs() -> list[ScrapeJob]:
    jobs: list[ScrapeJob] = []
    minute_cursor = 0
    for city in _CITIES:
        for pt in _PROPERTY_TYPES:
            for op in _OPERATIONS:
                jobs.append(
                    ScrapeJob(
                        cron=f"{minute_cursor} 0,6,12,18 * * *",
                        source="inmuebles24",
                        city=city,
                        zone=None,
                        property_type=pt,
                        operation=op,
                        pages=5,
                        notes="every 6h; 3s delay between page fetches",
                    )
                )
                minute_cursor = (minute_cursor + 5) % 60
    return jobs


def _build_vivanuncios_jobs() -> list[ScrapeJob]:
    # One city per 2h slot rotates through Tulum, Cancun, Playa del Carmen.
    # Free-tier 30-min throttle is enforced in-process — the cron just spaces runs further.
    jobs: list[ScrapeJob] = []
    hour_for_city = {"tulum": "0,6,12,18", "cancun": "2,8,14,20", "playa-del-carmen": "4,10,16,22"}
    for city in _CITIES:
        for pt in _PROPERTY_TYPES:
            for op in _OPERATIONS:
                jobs.append(
                    ScrapeJob(
                        cron=f"0 {hour_for_city[city]} * * *",
                        source="vivanuncios",
                        city=city,
                        zone=None,
                        property_type=pt,
                        operation=op,
                        pages=3,
                        notes="free-tier 1 run / 30 min; rotated city schedule",
                    )
                )
    return jobs


SCHEDULES: list[ScrapeJob] = _build_inmuebles24_jobs() + _build_vivanuncios_jobs()


def render_crontab(jobs: list[ScrapeJob] | None = None) -> str:
    jobs = jobs if jobs is not None else SCHEDULES
    lines = []
    for job in jobs:
        cmd_parts = [
            "python -m scrapers.runner",
            f"--source {job['source']}",
            f"--city {job['city']}",
        ]
        if job["zone"]:
            cmd_parts.append(f"--zone {job['zone']}")
        cmd_parts.append(f"--property-type {job['property_type']}")
        cmd_parts.append(f"--operation {job['operation']}")
        cmd_parts.append(f"--pages {job['pages']}")
        cmd = " ".join(cmd_parts)
        lines.append(f"{job['cron']}  {cmd}  # {job['notes']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_crontab())
