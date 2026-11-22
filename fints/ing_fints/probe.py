"""A redacted capability report, never a raw bank-response dump."""
from datetime import date, datetime, timedelta, timezone
from .models import account_record, holding_record, decimal


def supported(metadata):
    operations = metadata.get('supported_operations', {})
    return sorted(getattr(key, 'name', str(key)) for key, value in operations.items()
                  if value and getattr(key, 'name', str(key)) in {
                      'GET_HOLDINGS', 'GET_BALANCE', 'GET_TRANSACTIONS',
                      'GET_TRANSACTIONS_XML', 'GET_SEPA_ACCOUNTS'})


def probe(adapter, *, today=None, live=False):
    today = today or date.today()
    start = today - timedelta(days=89)
    discovered = adapter.accounts()
    information = adapter.information()
    metadata_by_iban = {row.get('iban'): row for row in information.get('accounts', [])}
    rows = []
    valid_holdings = balances = transactions = 0
    for raw in discovered:
        metadata = metadata_by_iban.get(raw.iban, {})
        account = account_record(raw, metadata)
        operations = supported(metadata)
        row = {'id': account.id, 'kind': account.kind, 'masked_iban': account.masked_iban,
               'currency': account.currency, 'supported_operations': operations,
               'holding_count': 0, 'valid_valued_holding_count': 0,
               'transaction_count': 0, 'balance_read': False, 'holding_fields': {}}
        if 'GET_HOLDINGS' in operations:
            holdings = [holding_record(account.id, h) for h in adapter.holdings(raw)]
            row['holding_count'] = len(holdings)
            row['valid_valued_holding_count'] = sum(
                h.isin is not None and h.quantity_decimal is not None
                and h.market_value_decimal is not None and h.currency is not None for h in holdings)
            for field in ('isin', 'quantity_decimal', 'price_decimal', 'market_value_decimal',
                          'acquisition_price_decimal', 'currency', 'valuation_date'):
                row['holding_fields'][field] = sum(getattr(h, field) is not None for h in holdings)
            valid_holdings += row['valid_valued_holding_count']
        if 'GET_BALANCE' in operations:
            balance = adapter.balance(raw)
            if decimal(balance.amount.amount) is None or not balance.amount.currency:
                raise ValueError('Missing balance amount or currency')
            row['balance_read'] = True
            balances += 1
        if {'GET_TRANSACTIONS', 'GET_TRANSACTIONS_XML'} & set(operations):
            records = adapter.transactions(raw, start, today)
            for record in records:
                data = record.data
                if decimal(data['amount'].amount) is None or not data['amount'].currency:
                    raise ValueError('Missing transaction amount or currency')
                if not isinstance(data.get('date'), date):
                    raise ValueError('Missing transaction booking date')
            row['transaction_count'] = len(records)
            transactions += len(records)
        rows.append(row)
    kinds = {row['kind'] for row in rows}
    passed = bool(live and valid_holdings and balances and transactions
                  and {'depot', 'checking', 'savings'} <= kinds)
    return {
        'schema_version': 1, 'source': 'ING FinTS' if live else 'synthetic fixture',
        'completed_at': datetime.now(timezone.utc).isoformat(),
        'milestone_0_passed': passed, 'accounts': rows,
        'transaction_window': {'from': start.isoformat(), 'to': today.isoformat()},
        'warnings': ['Live compatibility is unverified until the live probe passes.',
                     'No financial values, account names, transaction text or credentials are included.',
                     'No retries are performed. Authentication challenges require human action.',
                     'Cost basis is not inferred from acquisition price.',
                     'Historical Girokonto transactions may be limited to 90 days.'],
        'next_step': 'Review report and reconcile with ING before full build.' if passed else
                     'Full build blocked: resolve missing accounts/fields/reads; use ING CSV export if holdings fail.'}
