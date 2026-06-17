from __future__ import annotations


class ValuationServiceError(Exception):
    """Base for all backend service domain errors."""

    code: str = "service_error"

    def __init__(self, message: str | None = None, **details: object) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__
        self.details = details


class InsufficientDataError(ValuationServiceError):
    code = "insufficient_data"


class CityNotFoundError(ValuationServiceError):
    code = "city_not_found"


class ZoneNotFoundError(ValuationServiceError):
    code = "zone_not_found"


class PropertyTypeNotFoundError(ValuationServiceError):
    code = "property_type_not_found"


class InvalidInputError(ValuationServiceError):
    code = "invalid_input"


__all__ = [
    "ValuationServiceError",
    "InsufficientDataError",
    "CityNotFoundError",
    "ZoneNotFoundError",
    "PropertyTypeNotFoundError",
    "InvalidInputError",
]
