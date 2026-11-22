from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import re


class InvalidRecord(ValueError):
    pass


def decimal(value):
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


@dataclass(frozen=True)
class Account:
    id: str
    bank_id: str
    kind: str
    display_name: str
    currency: str
    masked_iban: str
    enabled: bool = True
    last_sync_at: str | None = None


def account_record(raw, metadata):
    iban = str(raw.iban)
    label = str(metadata.get('product_name', '')).casefold()
    if 'depot' in label:
        kind = 'depot'
    elif 'extra' in label or 'spar' in label:
        kind = 'savings'
    elif 'giro' in label:
        kind = 'checking'
    else:
        kind = 'unknown'
    # Do not expose bank-provided labels (which can contain names/identifiers).
    return Account(hashlib.sha256(('ING:' + iban).encode()).hexdigest()[:24],
                   'ING', kind, 'ING ' + kind, metadata.get('currency') or 'EUR',
                   '****' + iban[-4:])


@dataclass(frozen=True)
class Holding:
    account_id: str
    isin: str | None
    quantity_decimal: Decimal | None
    price_decimal: Decimal | None
    market_value_decimal: Decimal | None
    acquisition_price_decimal: Decimal | None
    currency: str | None
    valuation_date: date | None


def holding_record(account_id, raw):
    isin = getattr(raw, 'ISIN', None)
    if isin is not None and not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', isin):
        raise InvalidRecord('Invalid ISIN')
    currency = getattr(raw, 'value_symbol', None)
    # Percentage prices must not be interpreted as currency prices.
    if currency is not None and not re.fullmatch(r'[A-Z]{3}', currency):
        currency = None
    valuation = getattr(raw, 'valuation_date', None)
    if valuation is not None and not isinstance(valuation, date):
        raise InvalidRecord('Invalid valuation date')
    return Holding(account_id, isin, decimal(getattr(raw, 'pieces', None)),
                   decimal(getattr(raw, 'market_value', None)),
                   decimal(getattr(raw, 'total_value', None)),
                   decimal(getattr(raw, 'acquisitionprice', None)), currency, valuation)
