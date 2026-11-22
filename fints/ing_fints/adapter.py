"""BankAdapter boundary and explicitly allowlisted FinTS operations."""
from contextlib import contextmanager
from datetime import date
from typing import Protocol
import logging

ENDPOINT = 'https://fints.ing.de/fints/'
BANK_CODE = '50010517'
BIC = 'INGDDEFFXXX'
ALLOWED = frozenset({'get_sepa_accounts', 'get_information', 'get_holdings',
                     'get_balance', 'get_transactions'})


class HumanActionRequired(RuntimeError):
    pass


class BankAdapter(Protocol):
    def connect(self): ...
    def discover(self): ...
    def holdings(self, account): ...
    def balance(self, account): ...
    def transactions(self, account, start: date, end: date): ...


def valid_user_id(user_id):
    """ING's FinTS user ID is the self-chosen online-banking username: ASCII, no whitespace."""
    return 0 < len(user_id) <= 50 and user_id.isascii() and user_id.isprintable() and not any(
        c.isspace() for c in user_id)


class INGAdapter:
    def __init__(self, user_id, pin, product_id):
        if not valid_user_id(user_id):
            raise ValueError('ING user ID must be your online-banking username')
        if not product_id.strip():
            raise ValueError('A registered FinTS product ID is required')
        from fints.client import FinTS3PinTanClient, NeedRetryResponse
        from fints.models import SEPAAccount
        import fints.client
        from .mt535 import DecimalMT535Parser
        fints.client.MT535_Miniparser = DecimalMT535Parser
        self._challenge_type = NeedRetryResponse
        self._account_type = SEPAAccount
        # Protocol debug logs can include financial data. Disable library handlers.
        for name in ('fints', 'mt940', 'requests', 'urllib3'):
            logger = logging.getLogger(name)
            logger.disabled = True
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            logger.setLevel(logging.CRITICAL + 1)
        self._client = FinTS3PinTanClient(BANK_CODE, user_id, pin, ENDPOINT,
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
        """Open one standing FinTS dialog, so every read in the block shares a single login."""
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

    def discover(self):
        """Pair each account in the bank's user parameter data with a FinTS account reference.

        Depots usually have no IBAN and are absent from the SEPA account list, so their
        reference is built from the account number and ING's fixed bank identifiers.
        """
        sepa = {account.iban: account for account in self._read('get_sepa_accounts')}
        return [(sepa.get(metadata.get('iban')) or self._account_type(
                    iban=metadata.get('iban'), bic=BIC,
                    accountnumber=metadata.get('account_number'),
                    subaccount=metadata.get('subaccount_number'), blz=BANK_CODE), metadata)
                for metadata in self._read('get_information').get('accounts', [])]

    def holdings(self, account):
        return self._read('get_holdings', account)

    def balance(self, account):
        return self._read('get_balance', account)

    def transactions(self, account, start, end):
        return self._read('get_transactions', account, start_date=start,
                          end_date=end, include_pending=False)
