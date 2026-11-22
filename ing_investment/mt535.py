"""Exact-decimal MT535 parser for the fields supported by python-fints.

The upstream parser uses float. This replacement does not infer missing values.
Unrecognized formats remain missing and fail the feasibility gate where required.
"""
from datetime import datetime
from decimal import Decimal
import re


class DecimalMT535Parser:
    def parse(self, lines):
        from fints.models import Holding
        clauses = []
        for line in lines:
            if line.startswith(':'):
                clauses.append(line)
            elif line.startswith('-'):
                continue
            elif clauses:
                clauses[-1] += '|' + line
        records, fields = [], None
        patterns = {
            'market_value': r'^:90B::MRKT//ACTU/([A-Z]{3})(\d*),(\d*)$',
            'pieces': r'^:93B::AGGR//UNIT/(\d*),(\d*)$',
            'total_value': r'^:19A::HOLD//([A-Z]{3})(\d*),(\d*)$',
            'acquisitionprice': r'^:70E::HOLD//\d*STK\|2(\d*),(\d*)\+([A-Z]{3})$'}
        for clause in clauses:
            if clause == ':16R:FIN':
                fields = dict.fromkeys(('ISIN', 'name', 'market_value', 'value_symbol',
                                        'valuation_date', 'pieces', 'total_value', 'acquisitionprice'))
            elif clause == ':16S:FIN' and fields is not None:
                records.append(Holding(**fields))
                fields = None
            elif fields is not None:
                match = re.fullmatch(r':35B:ISIN ([^|]+)\|[^|]*\|(.*)', clause)
                if match:
                    fields.update(ISIN=match[1], name=match[2])
                match = re.fullmatch(r':98A::PRIC//(\d{8})', clause)
                if match:
                    fields['valuation_date'] = datetime.strptime(match[1], '%Y%m%d').date()
                for field, pattern in patterns.items():
                    match = re.fullmatch(pattern, clause)
                    if not match:
                        continue
                    if field in ('market_value', 'total_value'):
                        currency, integer, fraction = match.groups()
                        if fields['value_symbol'] not in (None, currency):
                            raise ValueError('Mixed holding currencies')
                        fields['value_symbol'] = currency
                    elif field == 'acquisitionprice':
                        integer, fraction, currency = match.groups()
                        if fields['value_symbol'] not in (None, currency):
                            continue  # Acquisition price in another currency is not normalized.
                    else:
                        integer, fraction = match.groups()
                    fields[field] = Decimal((integer or '0') + '.' + (fraction or '0'))
        if fields is not None:
            raise ValueError('Incomplete MT535 holding')
        return records
