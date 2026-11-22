# Operations and threat model

## Trust boundaries

Only the local terminal accepts bank credentials. The OS keychain stores one credential entry; the FinTS client and bank responses exist in process memory. The connector fixes the ING endpoint and bank code; its HTTP session validates TLS, disallows redirects, ignores ambient proxies and uses bounded connect/read timeouts. Use an OS/network egress allowlist for `fints.ing.de:443` as defense in depth before production.

Account discovery, information, holdings, balances and booked transactions are the sole callable adapter operations. There is no generic agent operation dispatcher. No payment/trade operation is exposed. The upstream library itself supports mutations, so it must never be handed directly to an agent.

Bank text is untrusted data. The probe does not evaluate text, send it to an LLM or echo it. Reports use an explicit field whitelist. Library logging is suppressed; exception messages and tracebacks are not printed. Never enable protocol debug logging with real credentials/data. Do not attach a debugger or dump process memory in a shared environment.

## Emergency disable and rotation

Stop the running CLI (Ctrl-C). There is no scheduler or daemon to stop. Run `uv run ing-investment forget` to remove the keychain credential entry. Rotate credentials through trusted ING banking interfaces and run setup again locally. Inspect authorized bank access/product registration if compromise is suspected. Delete old private reports per your retention policy.

## Report handling

Optional report writes use exclusive creation and mode 0600. Existing files/symlinks are not followed or overwritten. Store reports on an encrypted OS volume and keep them out of Git. Do not retain raw bank records for diagnosis until an encrypted, access-controlled diagnostic store is designed. No backup mechanism exists yet; production backups must be encrypted.

## Failure handling

Never retry authentication/protocol failures in a loop. A rejected login or TAN challenge requires human investigation through local bank access. The CLI deliberately suppresses arbitrary bank exception content. Check local dependency installation, keychain permission, registered product ID and ING access manually. Keep previous successful reports; failures produce no replacement report.

## Full-build gate review

1. Install and lock the pinned dependencies in an isolated environment.
2. Run the explicitly approved probe locally once.
3. Confirm account coverage and the report's required-field counts.
4. Reconcile actual holdings and aggregate values directly against ING locally.
5. Record authentication constraints and field gaps without secrets.
6. If holdings fail, stop full implementation and document official export/CSV fallback.
7. Only after passing, build persistence/API/MCP and their security controls.

Official references: [ING FinTS help](https://www.ing.de/hilfe/log-in/fints/), [python-fints reads](https://python-fints.readthedocs.io/en/latest/reading.html), [python-fints source](https://github.com/raphaelm/python-fints). These describe protocol/library support, not a successful connection to this customer's accounts.
