"""Display rounding — the single output-edge helper (Task 3).

Covers the awkward cases the brief calls out: None, NaN, negative zero, large
floats and the 0.005 boundary, plus the Jinja filter registration that every
template uses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from backend import create_app
from backend.services.rounding import DASH, fmt2


@pytest.mark.parametrize(
    "value,expected",
    [
        # Whole numbers stay bare; trailing zeros are trimmed.
        (70, "70"),
        (70.0, "70"),
        (70.5, "70.5"),
        (70.50, "70.5"),
        (70.549, "70.55"),
        (0.0, "0"),
        # Nothing to show.
        (None, DASH),
        (float("nan"), DASH),
        (float("inf"), DASH),
        (float("-inf"), DASH),
        ("not a number", DASH),
        # Negative zero and anything that rounds to zero are never "-0.00".
        (-0.0, "0"),
        (-0.001, "0"),
        (-0.004, "0"),
        # Half-up at the boundary, where Python's round() would bank down.
        (0.005, "0.01"),
        (0.015, "0.02"),
        (2.675, "2.68"),
        (1.004, "1"),
        (1.005, "1.01"),
        # Negatives keep their sign and round away from zero.
        (-1.005, "-1.01"),
        (-12.3456, "-12.35"),
        # Large floats survive without scientific notation or crashing.
        (1234567.891, "1234567.89"),
        (1e15, "1000000000000000"),
        (0.1 + 0.2, "0.3"),
    ],
)
def test_fmt2_rules(value, expected):
    assert fmt2(value) == expected


def test_r2_jinja_filter_is_registered():
    app = create_app()
    assert "r2" in app.jinja_env.filters
    template = app.jinja_env.from_string(
        "{{ value|r2 }}|{{ missing|r2 }}|{{ 70.5|r2 }}|{{ -0.0|r2 }}"
    )
    rendered = template.render(value=42.125, missing=None)
    assert rendered == "42.13|%s|70.5|0" % DASH


def test_pages_show_rounded_numbers():
    client = create_app().test_client()
    body = client.get("/students").get_data(as_text=True)
    # The students page must not leak full-precision floats (e.g. 54.8611111).
    for token in ("54.86111", "73.138888", "0.30000000000000004"):
        assert token not in body
