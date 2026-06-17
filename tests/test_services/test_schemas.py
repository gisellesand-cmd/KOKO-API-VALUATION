import pytest
from pydantic import ValidationError

from services.schemas import ValuationInput, ValuationOutput, DISCLAIMER_TEXT


def test_valuation_input_rejects_zero_area():
    with pytest.raises(ValidationError):
        ValuationInput(
            city_slug="cdmx",
            property_type_slug="departamento",
            operation="venta",
            area_m2=0,
        )


def test_valuation_input_rejects_negative_area():
    with pytest.raises(ValidationError):
        ValuationInput(
            city_slug="cdmx",
            property_type_slug="departamento",
            operation="venta",
            area_m2=-10,
        )


def test_valuation_input_rejects_area_above_10000():
    with pytest.raises(ValidationError):
        ValuationInput(
            city_slug="cdmx",
            property_type_slug="departamento",
            operation="venta",
            area_m2=10_001,
        )


def test_valuation_input_accepts_minimal_valid_payload():
    payload = ValuationInput(
        city_slug="cdmx",
        property_type_slug="departamento",
        operation="venta",
        area_m2=80,
    )
    assert payload.city_slug == "cdmx"
    assert payload.property_type_slug == "departamento"
    assert payload.operation == "venta"
    assert payload.area_m2 == 80


def test_valuation_input_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ValuationInput(
            city_slug="cdmx",
            property_type_slug="departamento",
            operation="venta",
            area_m2=80,
            unexpected_field="boom",
        )


def test_valuation_input_rejects_invalid_operation():
    with pytest.raises(ValidationError):
        ValuationInput(
            city_slug="cdmx",
            property_type_slug="departamento",
            operation="alquiler",
            area_m2=80,
        )


def test_valuation_input_accepts_renta():
    payload = ValuationInput(
        city_slug="cdmx",
        property_type_slug="departamento",
        operation="renta",
        area_m2=80,
    )
    assert payload.operation == "renta"


def test_valuation_output_default_disclaimer():
    out = ValuationOutput(
        confidence_level="insuficiente",
        comparables_count=0,
        geographic_scope="zone",
    )
    assert out.disclaimer == DISCLAIMER_TEXT
