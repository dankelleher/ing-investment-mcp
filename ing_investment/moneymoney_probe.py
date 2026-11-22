"""Trusted-terminal export probe; saves field availability, never raw bank data."""
import argparse
import json
import os
from pathlib import Path
from .moneymoney import (MoneyMoneyAdapter, MoneyMoneyService, records,
                         is_ing_account, ing_identity, ExportError)


def probe_exports(adapter=None, *, selected_depots=frozenset()):
    adapter = adapter or MoneyMoneyAdapter()
    accounts = records(adapter.accounts(), 'accounts')
    selected = [a for a in accounts if is_ing_account(a, selected_depots)]
    portfolios, portfolio_cache = [], {}
    export_failed = False
    for account in selected:
        if account.get('portfolio') is True:
            raw_id = str(account['uuid'])
            try:
                payload = adapter.portfolio(raw_id)
                rows = records(payload, 'securities')
                portfolio_cache[raw_id] = payload
                portfolios.append({'export_succeeded': True, 'holding_count': len(rows),
                    'field_names': sorted({k for row in rows for k in row}),
                    'numeric_field_types': {key: sorted({type(row[key]).__name__ for row in rows if key in row})
                        for key in ('quantity', 'price', 'marketPrice', 'amount', 'marketValue', 'purchasePrice', 'purchaseValue')}})
            except Exception as error:
                export_failed = True
                portfolios.append({'export_succeeded': False,
                                   'failure_stage': error.stage if isinstance(error, ExportError) else 'unexpected',
                                   'diagnostics': error.details if isinstance(error, ExportError) else {},
                                   'warning': 'Portfolio export unavailable or schema unsupported; raw details withheld.'})

    class CachedExports:
        def accounts(self):
            return accounts
        def portfolio(self, raw_id):
            return portfolio_cache[raw_id]

    holdings = []
    normalization_status = 'no_matching_accounts'
    if selected and not export_failed:
        try:
            # Validate exactly the exports inspected above; do not export twice.
            holdings = MoneyMoneyService(CachedExports(), selected_depots=selected_depots)._load()['holdings']
            normalization_status = 'success'
        except Exception:
            normalization_status = 'unsupported_export_schema'
    elif export_failed:
        normalization_status = 'portfolio_export_failed'
    fields = ('isin', 'quantity_decimal', 'price_decimal', 'market_value_decimal', 'currency', 'cost_basis_decimal')
    coverage = {field: sum(h[field] is not None for h in holdings) for field in fields}
    valid = bool(normalization_status == 'success' and holdings and
                 any(all(h[field] is not None for field in ('isin', 'quantity_decimal', 'market_value_decimal', 'currency'))
                     for h in holdings))
    return {'schema_version': 2, 'source': 'MoneyMoney / ING',
        'validation_passed': valid,
        'total_exported_account_count': len(accounts),
        'all_account_field_names': sorted({k for row in accounts for k in row}),
        'account_diagnostics': [{
            'is_group': row.get('group') is True,
            'group_field_type': type(row.get('group')).__name__,
            'is_portfolio': row.get('portfolio') is True,
            'portfolio_field_type': type(row.get('portfolio')).__name__,
            'bank_code_present': row.get('bankCode') not in (None, ''),
            'bank_code_field_type': type(row.get('bankCode')).__name__,
            'bic_present': row.get('bic') not in (None, ''),
            'iban_present': row.get('iban') not in (None, ''),
            'matched_ing_identity': ing_identity(row),
            'selected': is_ing_account(row, selected_depots)} for row in accounts],
        'ing_account_count': len(selected), 'ing_depot_count': len(portfolios),
        'account_field_names': sorted({k for row in selected for k in row}),
        'portfolios': portfolios, 'normalization_status': normalization_status,
        'captured_portfolio_files': getattr(adapter, 'capture_files', []),
        'normalized_holding_count': len(holdings),
        'normalized_field_coverage': coverage,
        'warnings': ['Report contains counts, field names, types and match flags only.',
                     'MoneyMoney bank sync and reconciliation must be checked locally.']}


def main():
    parser = argparse.ArgumentParser(description='Redacted local MoneyMoney export validation')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--select-depots', action='store_true', help='Choose unidentified ING depots in your trusted terminal')
    parser.add_argument('--capture-portfolio', action='store_true', help='Save private raw portfolio exports locally for debugging')
    args = parser.parse_args()
    try:
        from .moneymoney_selection import load_selected_depots, select_depots_locally
        capture_directory = None
        if args.capture_portfolio:
            capture_directory = Path(__file__).resolve().parents[1] / 'reports'
            capture_directory.mkdir(exist_ok=True, mode=0o700)
        adapter = MoneyMoneyAdapter(capture_directory=capture_directory)
        selected = load_selected_depots()
        if args.select_depots:
            import sys
            if not sys.stdin.isatty():
                raise ValueError('Interactive terminal required')
            selected = select_depots_locally(records(adapter.accounts(), 'accounts'))
        report = probe_exports(adapter, selected_depots=selected)
        text = json.dumps(report, indent=2) + '\n'
        if args.report:
            fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(text)
        print(text, end='')
        return 0 if report['validation_passed'] else 3
    except Exception:
        print('MoneyMoney export unavailable. Open/unlock MoneyMoney and check '
              'System Settings → Privacy & Security → Automation for your terminal. '
              'Use a fresh report filename. No raw diagnostic data was saved.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
