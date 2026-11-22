"""Exact decimal parsing for exported monetary literals."""
from decimal import Decimal, InvalidOperation


class InvalidRecord(ValueError):
    pass


def decimal(value):
    """Parse a monetary literal as Decimal, rejecting floats and non-finite values."""
    if value is None:
        return None
    if isinstance(value, float):
        raise InvalidRecord('Float monetary values are unsupported')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise InvalidRecord('Invalid decimal') from None
    if not result.is_finite():
        raise InvalidRecord('Non-finite decimal')
    return result
