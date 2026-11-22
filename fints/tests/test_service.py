from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS
import json
import unittest

from mcp import Client

from ing_fints.adapter import INGAdapter, HumanActionRequired, valid_user_id, BIC, BANK_CODE
from ing_fints.credentials import MissingCredentials
from ing_fints.server import create_server
from ing_fints.service import FinTSService, ServiceError
from test_fints import FakeBank


class ServiceBank(FakeBank):
    def __init__(self):
        self.sessions = 0
        self.fail = None

    @contextmanager
    def connect(self):
        self.sessions += 1
        if self.fail:
            raise self.fail
        yield self

    def balance(self, account):
        return NS(amount=NS(amount=Decimal('-12.99'), currency='EUR'), date=date(2026, 11, 20))

    def transactions(self, account, start, end):
        return [NS(data={'amount': NS(amount=Decimal('-1.23'), currency='EUR'), 'date': end,
                         'entry_date': end, 'purpose': 'Rent DE89370400440532013000'}),
                NS(data={'amount': NS(amount=Decimal('5'), currency='EUR'), 'date': start - timedelta(days=1),
                         'entry_date': start - timedelta(days=1), 'purpose': 'outside window'})]


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def service_for(bank, **kwargs):
    return FinTSService(lambda: bank, **kwargs)


class DiscoveryTests(unittest.TestCase):
    def test_depot_without_iban_gets_account_number_reference(self):
        adapter = object.__new__(INGAdapter)
        adapter._challenge_type = type('Challenge', (), {})
        adapter._account_type = NS
        giro = NS(iban='DE00000000000000000001')
        adapter._client = NS(
            get_sepa_accounts=lambda: [giro],
            get_information=lambda: {'accounts': [
                {'iban': 'DE00000000000000000001', 'product_name': 'Girokonto'},
                {'iban': None, 'account_number': '5550001234', 'subaccount_number': None,
                 'product_name': 'Direkt-Depot'}]})
        (first, _), (depot, metadata) = adapter.discover()
        self.assertIs(first, giro)
        self.assertEqual((depot.accountnumber, depot.bic, depot.blz), ('5550001234', BIC, BANK_CODE))
        self.assertEqual(metadata['product_name'], 'Direkt-Depot')

    def test_user_id_is_username_not_only_access_number(self):
        self.assertTrue(valid_user_id('example.user'))
        self.assertTrue(valid_user_id('1234567890'))
        for bad in ('', 'has space', 'ümlaut', 'x' * 51):
            self.assertFalse(valid_user_id(bad))


class ServiceTests(unittest.TestCase):
    def test_snapshot_is_read_in_one_session_and_cached(self):
        bank, clock = ServiceBank(), Clock()
        service = service_for(bank, clock=clock)
        holdings = service.holdings()['data']
        self.assertEqual(holdings['total_count'], 1)
        self.assertEqual(holdings['items'][0]['market_value_decimal'], '112.63')
        self.assertEqual(holdings['items'][0]['quantity_decimal'], '1.1234567890123456789')
        balances = service.balances()['data']['items']
        self.assertEqual([b['amount_decimal'] for b in balances], ['-12.99', '-12.99'])
        self.assertEqual(bank.sessions, 1)
        clock.now = 901
        service.accounts()
        self.assertEqual(bank.sessions, 2)

    def test_failed_session_pauses_bank_contact(self):
        bank = ServiceBank()
        bank.fail = RuntimeError('9942 secret protocol text')
        service = service_for(bank)
        for _ in range(3):
            with self.assertRaises(ServiceError) as raised:
                service.accounts()
            self.assertNotIn('secret', str(raised.exception))
        self.assertEqual(bank.sessions, 1)

    def test_failure_after_success_serves_degraded_snapshot(self):
        bank, clock = ServiceBank(), Clock()
        service = service_for(bank, clock=clock)
        service.accounts()
        bank.fail = HumanActionRequired()
        clock.now = 1000
        result = service.sync_status()
        self.assertEqual(result['completeness'], 'degraded')
        self.assertTrue(result['data']['bank_contact_paused'])
        clock.now = 2000
        service.accounts()
        self.assertEqual(bank.sessions, 2)

    def test_missing_credentials_do_not_pause_bank_contact(self):
        def factory():
            raise MissingCredentials('run setup')
        service = FinTSService(factory)
        with self.assertRaises(ServiceError):
            service.accounts()
        self.assertIsNone(service.blocked)

    def test_transactions_filter_mask_and_require_opt_in(self):
        bank = ServiceBank()
        service = service_for(bank, enable_transactions=True)
        giro = next(a['id'] for a in service.accounts()['data']['items'] if a['kind'] == 'checking')
        today = date.today()
        rows = service.transactions(giro, (today - timedelta(days=30)).isoformat(), today.isoformat())['data']['items']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['amount_decimal'], '-1.23')
        self.assertNotIn('DE89', rows[0]['purpose'])
        self.assertIsNone(rows[0]['counterparty'])
        savings = next(a['id'] for a in service.accounts()['data']['items'] if a['kind'] == 'savings')
        with self.assertRaises(ServiceError):
            service.transactions(savings, today.isoformat(), today.isoformat())
        with self.assertRaises(ServiceError):
            service_for(ServiceBank()).transactions(giro, today.isoformat(), today.isoformat())

    def test_unknown_account_and_bad_paging_rejected(self):
        service = service_for(ServiceBank())
        with self.assertRaises(ServiceError):
            service.holdings('unknown')
        with self.assertRaises(ServiceError):
            service.accounts(limit=500)


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_are_read_only_and_serve_snapshot(self):
        server = create_server(service_for(ServiceBank()))
        async with Client(server, raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual({t.name for t in tools}, {'list_accounts', 'list_holdings',
                'get_portfolio_summary', 'get_balances', 'get_sync_status'})
            self.assertTrue(all(t.annotations.read_only_hint for t in tools))
            result = await client.call_tool('get_portfolio_summary', {})
            self.assertFalse(result.is_error)
            summary = json.loads(result.content[0].text)['data']
            self.assertEqual(summary['totals_by_currency'], {'EUR': '112.63'})

    async def test_transaction_tool_is_startup_opt_in(self):
        server = create_server(service_for(ServiceBank(), enable_transactions=True))
        async with Client(server, raise_exceptions=True) as client:
            self.assertIn('search_transactions', {t.name for t in (await client.list_tools()).tools})


if __name__ == '__main__':
    unittest.main()
