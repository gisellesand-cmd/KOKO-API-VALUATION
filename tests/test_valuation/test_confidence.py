import pytest

from valuation.confidence import classify_confidence


@pytest.mark.parametrize("n", [0])
def test_zero_is_insufficient(n):
    assert classify_confidence(n, fallback_to_city=False) == "insuficiente"
    assert classify_confidence(n, fallback_to_city=True) == "insuficiente"


@pytest.mark.parametrize("n", [1, 2, 3])
def test_low_is_baja(n):
    assert classify_confidence(n, fallback_to_city=False) == "baja"


@pytest.mark.parametrize("n", [4, 5, 6, 7])
def test_mid_is_media(n):
    assert classify_confidence(n, fallback_to_city=False) == "media"


@pytest.mark.parametrize("n", [8, 50, 500])
def test_high_is_alta(n):
    assert classify_confidence(n, fallback_to_city=False) == "alta"


def test_fallback_downgrade_alta_to_media():
    assert classify_confidence(8, fallback_to_city=True) == "media"


def test_fallback_downgrade_media_to_baja():
    assert classify_confidence(4, fallback_to_city=True) == "baja"


def test_fallback_baja_stays_baja():
    assert classify_confidence(1, fallback_to_city=True) == "baja"


def test_fallback_insuficiente_stays_insuficiente():
    assert classify_confidence(0, fallback_to_city=True) == "insuficiente"
