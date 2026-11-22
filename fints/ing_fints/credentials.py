"""ING login stored as one OS-keychain entry; never in files, arguments or MCP responses."""
import json

SERVICE = 'ing-fints-mcp'
ENTRY = 'credentials'


class MissingCredentials(RuntimeError):
    pass


def secure_keyring():
    """Return the keyring module only when backed by the macOS or Windows OS store."""
    import keyring
    backend = keyring.get_keyring()
    # Fail closed: only audited OS-backed stores, no plaintext/fallback backend.
    if type(backend).__module__ not in ('keyring.backends.macOS', 'keyring.backends.Windows'):
        raise RuntimeError('An OS-backed macOS/Windows keyring is required')
    return keyring


def save_credentials(user_id, pin):
    """Store the online-banking username and password in the OS keychain."""
    secure_keyring().set_password(SERVICE, ENTRY, json.dumps({'user_id': user_id, 'pin': pin}))


def load_credentials():
    """Return (user_id, pin) from the OS keychain, or raise MissingCredentials."""
    stored = secure_keyring().get_password(SERVICE, ENTRY)
    if not stored:
        raise MissingCredentials('Run `uv run ing-fints setup` in a trusted local terminal first')
    data = json.loads(stored)
    return data['user_id'], data['pin']


def forget_credentials():
    """Delete the stored login from the OS keychain."""
    secure_keyring().delete_password(SERVICE, ENTRY)
