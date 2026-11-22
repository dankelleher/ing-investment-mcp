# ING over direct FinTS

Talks to ING's FinTS server (`https://fints.ing.de/fints/`, BLZ `50010517`) directly with [python-fints](https://python-fints.readthedocs.io/), without a banking application in between. FinTS access requires a registered product ID from the Deutsche Kreditwirtschaft ([registration](https://www.fints.org/de/hersteller/produktregistrierung)); never reuse another application's ID.

## Status

The live feasibility gate has **not passed**: no bank connection has been made from this code. Implemented and covered by offline tests: OS-keychain credential setup, a restricted read-only ING adapter, account discovery and capability inspection, holdings, balance and 90-day transaction reads, exact-decimal MT535 parsing, and a redacted field-availability report.

ING's published FinTS coverage is Girokonto, Extra-Konto and Direkt-Depot. Smart-Depots are not listed and are expected to be unavailable on this route.

## Setup

Python 3.12+ and `uv` are required. From this directory, in your own trusted terminal:

```sh
uv sync --locked
uv run ing-fints setup
```

Credentials are entered through hidden prompts and stored as one OS-keychain entry. Never paste credentials into chat, command arguments, `.env`, reports or source files. macOS and Windows native keyring backends are allowed; other backends fail closed.

## Explicitly authorized live probe

Running this yourself grants permission for one session of account discovery, holdings, balances and booked transactions. It cannot initiate payments or orders. Use a fresh report filename.

```sh
mkdir -p reports
uv run ing-fints probe --approve-live-read --product-id YOUR_REGISTERED_ID --report reports/feasibility.json
```

Exit codes: `0` gate passed; `3` probe succeeded with insufficient coverage; `2` setup, dependency, authentication, protocol or report failure. Failed calls are never retried automatically, which matters because ING locks the login after three failed attempts. Authentication challenges stop the session without displaying challenge payloads or saving sessions.

The gate requires a recognized Direkt-Depot, Girokonto and Extra-Konto, at least one holding with ISIN, quantity, value and currency, a valid balance and a booked transaction. Reports contain generic labels and masked IBAN suffixes only; they omit amounts, ISINs, account names, counterparties, descriptions and raw protocol responses. Reconcile quantities and values against ING's website yourself.

## Offline tests

```sh
uv run python -m unittest discover -s tests -v
```

Tests use synthetic in-memory bank records, never real credentials.

See [limitations](LIMITATIONS.md) and [operations and threat model](OPERATIONS.md).
