"""KOKO Valuation API — FastAPI entrypoint.

Cableado: CORS configurable por env, middleware (request_id + timing +
logging JSON), exception handlers para errores HTTP, de validación y de
dominio, y montaje de routers de valuación, catálogo y salud.

Regla no negociable del producto: "cero datos inventados". Cuando
`confidence == "insuficiente"` la respuesta sale con `price_*` en null y
`methodology_note` explicando por qué. Esto se respeta a nivel servicio;
esta capa solo lo deja documentado y no lo enmascara.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers import catalog as catalog_router
from api.routers import health as health_router
from api.routers import valuation as valuation_router

try:
    from services.exceptions import CityNotFoundError, InvalidInputError  # type: ignore
except Exception:
    class CityNotFoundError(Exception):
        """Fallback hasta que services/exceptions.py exista."""

    class InvalidInputError(Exception):
        """Fallback hasta que services/exceptions.py exista."""


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    logging.getLogger(__name__).info("KOKO Valuation API starting")
    yield
    logging.getLogger(__name__).info("KOKO Valuation API stopping")


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if raw == "" or raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


OPENAPI_TAGS = [
    {
        "name": "Valuación",
        "description": (
            "Calcula rangos de precio basados en comparables reales. "
            "Honra la regla 'cero datos inventados'."
        ),
    },
    {
        "name": "Catálogo",
        "description": "Ciudades activas, zonas y tipos de propiedad soportados.",
    },
    {
        "name": "Salud",
        "description": "Liveness y readiness profundo del servicio.",
    },
]


app = FastAPI(
    title="KOKO Valuation API",
    version="0.1.0",
    description=(
        "API de valuación de propiedades para KOKO MLS. "
        "Devuelve un rango estimado en MXN basado en comparables vigentes "
        "de Inmuebles24 y Vivanuncios. Si no hay datos suficientes, no inventa."
    ),
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_id_and_timing(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logging.getLogger("api.access").exception(
            "request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logging.getLogger("api.access").info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": _request_id(request)},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "request_id": _request_id(request)},
    )


@app.exception_handler(CityNotFoundError)
async def city_not_found_handler(request: Request, exc: CityNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": f"Ciudad no encontrada: {exc}",
            "request_id": _request_id(request),
        },
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_handler(request: Request, exc: InvalidInputError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc), "request_id": _request_id(request)},
    )


app.include_router(valuation_router.router)
app.include_router(catalog_router.router)
app.include_router(health_router.router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "KOKO Valuation API",
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
    }
