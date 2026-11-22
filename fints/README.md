# ING over direct FinTS

Talks to ING's FinTS server (`https://fints.ing.de/fints/`, BLZ `50010517`) directly with [python-fints](https://python-fints.readthedocs.io/), without a banking application in between. FinTS access requires a registered product ID from the Deutsche Kreditwirtschaft ([registration](https://www.fints.org/de/hersteller/produktregistrierung)); never reuse another application's ID.

## Status

No bank connection has been made from this code yet; it is waiting for the FinTS product ID. Implemented and covered by offline tests: OS-keychain credential setup, a restricted read-only ING adapter, account discovery (including depots, which have no IBAN), holdings, balance and transaction reads, exact-decimal MT535 parsing, a redacted feasibility probe, and a stdio MCP server.

ING's published FinTS coverage is Girokonto, Extra-Konto and Direkt-Depot. Smart-Depots are not listed and are expected to be unavailable on this route.

## Setup

Python 3.12+ and `uv` are required. From this directory, in your own trusted terminal:

```sh
uv sync --locked
uv run ing-fints setup
```

`setup` asks for your ING online-banking **username** (not the old 10-digit access number) and password. Credentials are entered through hidden prompts and stored as one OS-keychain entry. Never paste credentials into chat, command arguments, `.env`, reports or source files. macOS and Windows native keyring backends are allowed; other backends fail closed.

## Explicitly authorized live probe

Running this yourself grants permission for one session of account discovery, holdings, balances and booked transactions. It cannot initiate payments or orders. Use a fresh report filename.

```sh
mkdir -p reports
uv run ing-fints probe --approve-live-read --product-id YOUR_REGISTERED_ID --report reports/feasibility.json
```

Exit codes: `0` gate passed; `3` probe succeeded with insufficient coverage; `2` setup, dependency, authentication, protocol or report failure. Failed calls are never retried automatically, which matters because ING locks the login after three failed attempts. Authentication challenges stop the session without displaying challenge payloads or saving sessions.

The gate requires a recognized Direkt-Depot, Girokonto and Extra-Konto, at least one holding with ISIN, quantity, value and currency, a valid balance and a booked transaction. Reports contain generic labels and masked IBAN suffixes only; they omit amounts, ISINs, account names, counterparties, descriptions and raw protocol responses. Reconcile quantities and values against ING's website yourself.

## MCP server

```sh
./run.sh --product-id YOUR_REGISTERED_ID --enable-transactions
```

Register it with an MCP client, for example:

```sh
codex mcp add ing-fints -- /Users/daniel/code/dankelleher/ing-investment-mcp/fints/run.sh --product-id YOUR_REGISTERED_ID --enable-transactions
```

Tools match the MoneyMoney route: `list_accounts`, `list_holdings`, `get_balances`, `get_portfolio_summary`, `get_sync_status`, and `search_transactions` when started with `--enable-transactions`. Responses use decimal strings, masked account numbers and hashed account IDs; counterparties are withheld and bank text is treated as untrusted data.

Unlike MoneyMoney, this server contacts the bank itself. The first tool call opens one FinTS session that reads all accounts, balances and holdings; that snapshot is cached for 15 minutes. Transaction searches open their own session. **Any failed session pauses all bank contact until the server is restarted**, and the previous snapshot is served as degraded. That stops an agent from repeating calls into ING's three-failure lockout. Check the login with the probe before restarting.

ING requires a successful website or QR log-in within the last 90 days for FinTS to work.

## Offline tests

```sh
uv run python -m unittest discover -s tests -v
```

Tests use synthetic in-memory bank records, never real credentials.

See [limitations](LIMITATIONS.md) and [operations and threat model](OPERATIONS.md).
