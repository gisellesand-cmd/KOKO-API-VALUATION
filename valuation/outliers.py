"""IQR-based outlier filtering."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def filter_iqr(values: Iterable[float], k: float = 1.5) -> list[float]:
    """Return values inside [Q1 - k*IQR, Q3 + k*IQR].

    With fewer than 4 values the IQR is not a robust statistic, so the input
    is returned unchanged. With IQR=0 (all equal values) every value is kept.
    """
    arr = np.asarray(list(values), dtype=float)
    if arr.size < 4:
        return arr.tolist()

    q1, q3 = np.percentile(arr, [25, 75], method="linear")
    iqr = q3 - q1
    if iqr == 0:
        return arr.tolist()

    lower = q1 - k * iqr
    upper = q3 + k * iqr
    mask = (arr >= lower) & (arr <= upper)
    return arr[mask].tolist()
