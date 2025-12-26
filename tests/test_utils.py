from datetime import datetime

import pytest

from app.utils import format_date_polish, transform_date, YEAR_OFFSET


def test_transform_date_datetime():
    dt = datetime(2024, 6, 15, 12, 30, 0)
    transformed = transform_date(dt)
    assert transformed.year == 2024 + YEAR_OFFSET
    assert transformed.month == 6
    assert transformed.day == 15


def test_transform_date_string():
    dt_str = "2024-06-15"
    transformed = transform_date(dt_str)
    assert transformed.year == 2024 + YEAR_OFFSET


def test_transform_date_leap_year():
    dt = datetime(2024, 2, 29, 12, 0, 0)
    transformed = transform_date(dt)
    assert transformed.day == 28 or transformed.day == 29


def test_format_date_polish():
    dt = datetime(2024, 1, 15)
    formatted = format_date_polish(dt)
    assert "15" in formatted
    assert "stycznia" in formatted
    assert str(2024 + YEAR_OFFSET) in formatted


def test_format_date_polish_december():
    dt = datetime(2024, 12, 25)
    formatted = format_date_polish(dt)
    assert "25" in formatted
    assert "grudnia" in formatted


def test_format_date_polish_string_input():
    formatted = format_date_polish("2024-03-10")
    assert "10" in formatted
    assert "marca" in formatted
