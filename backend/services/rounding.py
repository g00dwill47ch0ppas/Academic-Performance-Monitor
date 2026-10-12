"""
Display rounding — one helper, used at every output edge.

Calculations and stored values keep full precision (see the participation and
algorithm modules); only what the lecturer *sees* is rounded, and it is rounded
here so no page invents its own ``round(x, 1)`` / ``toFixed(2)``.

Rules
    * at most 2 decimal places, half-up (so 0.005 -> 0.01, not the binary-float
      2.67-style surprise that ``round()`` produces);
    * integers stay bare (70, not 70.00) and trailing zeros are trimmed, so
      70.50 shows as 70.5;
    * ``None`` / NaN / infinities show as a dash, because "no value" is not zero;
    * ``-0.00`` is never shown: anything that rounds to zero is "0".

The Jinja filter is registered on the app as ``|r2`` and the browser-side twin is
``fmt2()`` in ``frontend/static/js/format.js``; keep the two in step.
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

#: Shown when there is no value to display (None, NaN, infinity).
DASH = "—"

#: Two decimal places, rounded half-up.
TWO_PLACES = Decimal("0.01")


def fmt2(value, dash: str = DASH) -> str:
    """Format a number for display: at most 2 decimals, no ``-0.00``, dash for None."""
    if value is None:
        return dash
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return dash
    if math.isnan(number) or math.isinf(number):
        return dash

    try:
        rounded = Decimal(repr(number)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except InvalidOperation:  # pragma: no cover — unreachable for finite floats
        return dash

    if rounded == 0:
        # Collapses -0.0 and anything smaller than half a hundredth.
        return "0"
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def r2_number(value, dash: str = "") -> str:
    """Same rounding, but blank when there is nothing to show (used in files)."""
    return fmt2(value, dash=dash)
