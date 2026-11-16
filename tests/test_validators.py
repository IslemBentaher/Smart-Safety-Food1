import pytest

from validators import to_choice, to_date, to_number, to_text


def test_to_number():
    assert to_number("5", "x", 0, 10) == 5.0
    assert to_number(None, "x", 0, 10, default=3) == 3
    for bad in (None, "", "abc", 11, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            to_number(bad, "x", 0, 10)


def test_to_date():
    assert to_date("2026-11-02") == "2026-11-02"
    assert to_date(None, default="2026-01-01") == "2026-01-01"
    for bad in ("tomorrow", "2026-13-01", None):
        with pytest.raises(ValueError):
            to_date(bad)


def test_to_choice_and_text():
    assert to_choice(" Lunch ", ("lunch", "dinner"), "meal") == "lunch"
    with pytest.raises(ValueError):
        to_choice("brunch", ("lunch", "dinner"), "meal")
    assert to_text("  hi ", "t") == "hi"
    assert to_text("", "t", required=False) == ""
    with pytest.raises(ValueError):
        to_text("x" * 61, "t", 60)
