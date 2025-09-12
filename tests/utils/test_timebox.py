import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.utils.timebox import days_to, parse_expiration


def test_parse_expiration_valid():
    assert parse_expiration("2024-05-10") == date(2024, 5, 10)


@pytest.mark.parametrize("invalid", ["2024/05/10", "invalid", "2024-13-01"])
def test_parse_expiration_invalid(invalid):
    with pytest.raises(ValueError, match="Invalid expiration date"):
        parse_expiration(invalid)


def test_days_to_valid():
    today = date(2024, 1, 1)
    target = date(2024, 1, 31)
    assert days_to(target, today) == 30


def test_days_to_none():
    with pytest.raises(ValueError, match="date must not be None"):
        days_to(None)  # type: ignore[arg-type]
