import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from .adapter import INGAdapter, HumanActionRequired, valid_user_id
from .credentials import save_credentials, load_credentials, forget_credentials, MissingCredentials
from .probe import probe


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
        if args.command == 'setup':
            user_id = getpass.getpass('ING online-banking username (hidden): ')
            pin = getpass.getpass('ING online-banking password (hidden): ')
            if not valid_user_id(user_id) or not pin:
                raise ValueError('Invalid credentials')
            save_credentials(user_id, pin)
            print('Credentials saved in OS keychain.')
            return 0
        if args.command == 'forget':
            forget_credentials()
            print('Credentials removed.')
            return 0
        adapter = INGAdapter(*load_credentials(), args.product_id)
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
    except MissingCredentials as error:
        print(str(error), file=sys.stderr)
    except HumanActionRequired:
        print('Stopped: authentication challenge. Use trusted local banking setup; no retry performed.', file=sys.stderr)
    except Exception:
        # Never display bank/library exceptions, credentials, or protocol traces.
        print('Stopped: local setup, dependency, bank read, or report failure. No retry performed. '
              'Check setup and bank access locally; no diagnostic payload was saved.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
