"""BankAdapter boundary and explicitly allowlisted FinTS operations."""
from contextlib import contextmanager
from datetime import date
from typing import Protocol
import logging

ENDPOINT = 'https://fints.ing.de/fints/'
BANK_CODE = '50010517'
ALLOWED = frozenset({'get_sepa_accounts', 'get_information', 'get_holdings',
                     'get_balance', 'get_transactions'})


class HumanActionRequired(RuntimeError):
    pass


class BankAdapter(Protocol):
    def accounts(self): ...
    def information(self): ...
    def holdings(self, account): ...
    def balance(self, account): ...
    def transactions(self, account, start: date, end: date): ...


class INGAdapter:
    def __init__(self, access_number, pin, product_id):
        if len(access_number) != 10 or not access_number.isascii() or not access_number.isdigit():
            raise ValueError('ING access number must have ten digits')
        if not product_id.strip():
            raise ValueError('A registered FinTS product ID is required')
        from fints.client import FinTS3PinTanClient, NeedRetryResponse
        import fints.client
        from .mt535 import DecimalMT535Parser
        fints.client.MT535_Miniparser = DecimalMT535Parser
        self._challenge_type = NeedRetryResponse
        # Protocol debug logs can include financial data. Disable library handlers.
        for name in ('fints', 'mt940', 'requests', 'urllib3'):
            logger = logging.getLogger(name)
            logger.disabled = True
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            logger.setLevel(logging.CRITICAL + 1)
        self._client = FinTS3PinTanClient(BANK_CODE, access_number, pin, ENDPOINT,
                                         customer_id='', product_id=product_id)
        session = self._client.connection.session
        session.trust_env = False  # No ambient proxy credentials or endpoints.
        original_post = session.post

        def restricted_post(url, *args, **kwargs):
            if url != ENDPOINT:
                raise RuntimeError('Connector destination rejected')
            kwargs.update(verify=True, allow_redirects=False, timeout=(10, 30))
            result = original_post(url, *args, **kwargs)
            if 300 <= result.status_code < 400:
                raise RuntimeError('Connector redirect rejected')
            return result

        session.post = restricted_post

    @contextmanager
    def connect(self):
        with self._client:
            if self._client.init_tan_response:
                raise HumanActionRequired('Bank authentication requires local human action')
            yield self

    def _read(self, operation, *args, **kwargs):
        if operation not in ALLOWED:
            raise ValueError('Operation rejected')
        result = getattr(self._client, operation)(*args, **kwargs)
        if isinstance(result, self._challenge_type):
            raise HumanActionRequired('Bank authentication requires local human action')
        return result

    def accounts(self):
        return self._read('get_sepa_accounts')

    def information(self):
        return self._read('get_information')

    def holdings(self, account):
        return self._read('get_holdings', account)

    def balance(self, account):
        return self._read('get_balance', account)

    def transactions(self, account, start, end):
        return self._read('get_transactions', account, start_date=start,
                          end_date=end, include_pending=False)
