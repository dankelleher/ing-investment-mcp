import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from .adapter import INGAdapter, HumanActionRequired
from .spike import probe

SERVICE = 'ing-investment-mcp'


def secure_keyring():
    import keyring
    backend = keyring.get_keyring()
    # Fail closed: only audited OS-backed stores, no plaintext/fallback backend.
    if type(backend).__module__ not in ('keyring.backends.macOS', 'keyring.backends.Windows'):
        raise RuntimeError('An OS-backed macOS/Windows keyring is required')
    return keyring


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local read-only ING feasibility gate')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('setup', help='Save credentials to OS keychain using hidden prompts')
    sub.add_parser('forget', help='Delete locally stored bank credentials')
    live = sub.add_parser('probe', help='Explicitly authorized one-shot live bank reads')
    live.add_argument('--approve-live-read', action='store_true', required=True)
    live.add_argument('--product-id', required=True)
    live.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        parser.error('Run from a trusted interactive terminal')
    try:
        keyring = secure_keyring()
        if args.command == 'setup':
            number = getpass.getpass('ING 10-digit access number (hidden): ')
            pin = getpass.getpass('ING PIN/password (hidden): ')
            if len(number) != 10 or not number.isascii() or not number.isdigit() or not pin:
                raise ValueError('Invalid credentials')
            keyring.set_password(SERVICE, 'credentials', json.dumps({'number': number, 'pin': pin}))
            print('Credentials saved in OS keychain.')
            return 0
        if args.command == 'forget':
            keyring.delete_password(SERVICE, 'credentials')
            print('Credentials removed.')
            return 0
        credentials = keyring.get_password(SERVICE, 'credentials')
        if not credentials:
            print('Run setup in a trusted local terminal first.', file=sys.stderr)
            return 2
        credentials = json.loads(credentials)
        adapter = INGAdapter(credentials['number'], credentials['pin'], args.product_id)
        with adapter.connect():
            report = probe(adapter, live=True)
        output = json.dumps(report, indent=2) + '\n'
        if args.report:
            # Do not clobber files or follow existing symlinks.
            fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(output)
        print(output, end='')
        return 0 if report['milestone_0_passed'] else 3
    except HumanActionRequired:
        print('Stopped: authentication challenge. Use trusted local banking setup; no retry performed.', file=sys.stderr)
    except Exception:
        # Never display bank/library exceptions, credentials, or protocol traces.
        print('Stopped: local setup, dependency, bank read, or report failure. No retry performed. '
              'Check setup and bank access locally; no diagnostic payload was saved.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
