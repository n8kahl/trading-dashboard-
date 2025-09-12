from datetime import date, datetime, timezone


def parse_expiration(s: str) -> date:
    """Return a date parsed from a ``YYYY-MM-DD`` string.

    Raises
    ------
    ValueError
        If ``s`` is not a valid ISO date.
    """

    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"Invalid expiration date: {s}") from exc


def days_to(d: date, today: date | None = None) -> int:
    """Days between ``today`` (UTC) and ``d``.

    Raises
    ------
    ValueError
        If ``d`` is ``None``.
    """

    if d is None:
        raise ValueError("date must not be None")

    t = today or datetime.now(timezone.utc).date()
    return (d - t).days
