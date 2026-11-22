"""Owner-selected unidentified depots; local configuration is never an MCP tool."""
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID

CONFIG = Path(__file__).resolve().parents[1] / 'moneymoney.local.json'


def load_selected_depots():
    if not CONFIG.exists():
        return frozenset()
    data = json.loads(CONFIG.read_text())
    return frozenset(str(UUID(value)) for value in data['selected_depot_uuids'])


def save_selected_depots(values):
    values = sorted({str(UUID(value)) for value in values})
    fd, temp = tempfile.mkstemp(prefix='.moneymoney-selection-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'selected_depot_uuids': values}, stream)
            stream.write('\n')
        os.replace(temp, CONFIG)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def eligible_unidentified_depot(raw):
    return (raw.get('portfolio') is True and not raw.get('group')
            and not str(raw.get('bankCode') or '').strip()
            and not str(raw.get('bic') or '').strip()
            and not str(raw.get('iban') or '').strip()
            and not str(raw.get('accountNumber') or '').strip().upper().startswith('DE'))


def select_depots_locally(accounts):
    from .exports import scrub_text
    candidates = [a for a in accounts if eligible_unidentified_depot(a)]
    print('MoneyMoney depots with no exported bank identifier (local display only):')
    for index, account in enumerate(candidates, 1):
        print(f"{index}: {scrub_text(account.get('name')) or 'Unnamed depot'}")
    choices = input('Select only your ING depots by number, comma-separated (blank clears selection): ').strip()
    indices = {int(value.strip()) for value in choices.split(',')} if choices else set()
    if any(index < 1 or index > len(candidates) for index in indices):
        raise ValueError('Invalid selection')
    values = {str(UUID(candidates[index - 1]['uuid'])) for index in indices}
    save_selected_depots(values)
    print('Saved owner-selected depots locally. The following report contains no depot names.')
    return frozenset(values)
