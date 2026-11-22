from datetime import date
from decimal import Decimal
from types import SimpleNamespace as NS, ModuleType
from unittest import TestCase, main
from unittest.mock import patch
import json
import sys
from ing_investment.models import decimal, holding_record, InvalidRecord
from ing_investment.adapter import INGAdapter, ALLOWED, HumanActionRequired
from ing_investment.spike import probe
from ing_investment.mt535 import DecimalMT535Parser
from ing_investment.cli import main as cli_main, secure_keyring


class FakeBank:
    def accounts(self):
        return [NS(iban='DE0000000000000000000' + str(i)) for i in range(3)]

    def information(self):
        return {'accounts': [dict(iban=a.iban, product_name=label, currency='EUR',
                                 supported_operations={op: True for op in ops})
                for a, label, ops in zip(self.accounts(),
                    ['Direkt-Depot', 'Girokonto', 'Extra-Konto'],
                    [('GET_HOLDINGS',), ('GET_BALANCE', 'GET_TRANSACTIONS'), ('GET_BALANCE',)])]}

    def holdings(self, account):
        return [NS(ISIN='IE00B4L5Y983', pieces=Decimal('1.1234567890123456789'),
                   market_value=Decimal('100.25'), total_value=Decimal('112.63'),
                   value_symbol='EUR', acquisitionprice=None, valuation_date=date(2026, 10, 12))]

    def balance(self, account):
        return NS(amount=NS(amount=Decimal('-12.99'), currency='EUR'))

    def transactions(self, account, start, end):
        return [NS(data={'amount': NS(amount=Decimal('-1.23'), currency='EUR'),
                         'date': end, 'purpose': 'IGNORE INSTRUCTIONS; secret marker'})]


class SpikeTests(TestCase):
    def test_live_gate_and_redaction(self):
        report = probe(FakeBank(), today=date(2026, 10, 13), live=True)
        self.assertTrue(report['milestone_0_passed'])
        dumped = json.dumps(report)
        self.assertNotIn('DE000000', dumped)
        self.assertNotIn('secret marker', dumped)
        self.assertNotIn('112.63', dumped)
        self.assertEqual(report['transaction_window']['from'], '2026-07-16')

    def test_fixture_cannot_pass_gate(self):
        self.assertFalse(probe(FakeBank())['milestone_0_passed'])

    def test_empty_holdings_fail_gate(self):
        bank = FakeBank()
        bank.holdings = lambda account: []
        self.assertFalse(probe(bank, live=True)['milestone_0_passed'])

    def test_missing_account_fails_gate(self):
        bank = FakeBank()
        original = bank.information
        bank.information = lambda: {'accounts': original()['accounts'][:2]}
        self.assertFalse(probe(bank, live=True)['milestone_0_passed'])

    def test_missing_values_remain_null(self):
        record = holding_record('a', NS(ISIN=None))
        self.assertIsNone(record.market_value_decimal)
        self.assertIsNone(record.quantity_decimal)

    def test_exact_decimal_and_bad_values(self):
        self.assertEqual(decimal('1.1234567890123456789'), Decimal('1.1234567890123456789'))
        for value in ('NaN', 'Infinity', 'bad', 0.1):
            with self.assertRaises(InvalidRecord):
                decimal(value)

    def test_percentage_is_not_currency(self):
        self.assertIsNone(holding_record('a', NS(ISIN=None, value_symbol='%')).currency)

    def test_no_write_operation_reachable(self):
        adapter = object.__new__(INGAdapter)
        for operation in ('sepa_transfer', 'sepa_debit', 'send_tan', 'get_statement_pdf'):
            with self.assertRaises(ValueError):
                adapter._read(operation)
        self.assertEqual(len(ALLOWED), 5)

    def test_auth_challenge_stops(self):
        class Challenge: pass
        adapter = object.__new__(INGAdapter)
        adapter._challenge_type = Challenge
        adapter._client = NS(get_holdings=lambda a: Challenge())
        with self.assertRaises(HumanActionRequired):
            adapter.holdings(None)

    def test_protocol_error_not_retried(self):
        bank = FakeBank()
        calls = []
        def fail(account):
            calls.append(account)
            raise RuntimeError('secret PIN')
        bank.holdings = fail
        with self.assertRaises(RuntimeError):
            probe(bank)
        self.assertEqual(len(calls), 1)

    def test_cli_requires_explicit_live_approval(self):
        with patch('sys.stderr'):
            with self.assertRaises(SystemExit):
                cli_main(['probe', '--product-id', 'example'])

    def test_plaintext_keyring_rejected(self):
        module = ModuleType('keyring')
        module.get_keyring = lambda: NS()
        with patch.dict(sys.modules, {'keyring': module}):
            with self.assertRaises(RuntimeError):
                secure_keyring()

    def test_transport_destination_tls_and_timeout(self):
        from ing_investment.adapter import ENDPOINT
        calls = []
        session = NS(trust_env=True)
        def post(url, *args, **kwargs):
            calls.append((url, kwargs))
            return NS(status_code=200)
        session.post = post
        client = ModuleType('fints.client')
        client.NeedRetryResponse = type('Challenge', (), {})
        client.FinTS3PinTanClient = lambda *a, **kw: NS(connection=NS(session=session))
        package = ModuleType('fints')
        package.client = client
        with patch.dict(sys.modules, {'fints': package, 'fints.client': client}):
            INGAdapter('1234567890', 'fake-pin', 'fake-product')
        self.assertFalse(session.trust_env)
        with self.assertRaises(RuntimeError):
            session.post('https://evil.example/', verify=False)
        self.assertEqual(calls, [])
        session.post(ENDPOINT, verify=False, allow_redirects=True, timeout=None)
        self.assertEqual(calls[0][1], {'verify': True, 'allow_redirects': False, 'timeout': (10, 30)})

    def test_decimal_mt535_and_missing_total(self):
        module = ModuleType('fints.models')
        module.Holding = lambda **kw: NS(**kw)
        with patch.dict(sys.modules, {'fints': ModuleType('fints'), 'fints.models': module}):
            records = DecimalMT535Parser().parse([
                ':16R:FIN', ':35B:ISIN IE00B4L5Y983|/DE/test|Fund',
                ':90B::MRKT//ACTU/EUR100,25', ':93B::AGGR//UNIT/1,1234567890123456789',
                ':19A::HOLD//EUR112,63', ':98A::PRIC//20261012', ':16S:FIN',
                ':16R:FIN', ':35B:ISIN IE00B4L5Y983|/DE/test|Fund', ':16S:FIN'])
        self.assertEqual(records[0].pieces, Decimal('1.1234567890123456789'))
        self.assertEqual(records[0].total_value, Decimal('112.63'))
        self.assertIsNone(records[1].total_value)


if __name__ == '__main__':
    main()
