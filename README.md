# ING Investment MCP

The current path uses **MoneyMoney → local read-only MCP**, avoiding personal FinTS product registration. See [MoneyMoney setup and validation](docs/MONEYMONEY.md). SDK dependencies are installed and locked; the real MCP protocol has been tested with synthetic data and the owner’s captured exports (36 holdings across three ING depots). Live MoneyMoney export validation must run from your trusted terminal because this agent workspace cannot access macOS application services.

The original direct-FinTS feasibility implementation remains below as a separate alternative.

# Direct FinTS — feasibility gate

This repository implements **Milestone 0** of `ING_FinTS_Investment_MCP_Tech_Spec.pdf` (12 October 2026). Section 9 requires a successful live feasibility spike before the full build. This gate has **not passed**: no bank connection has been made. REST, MCP, persistence, analytics, and remote deployment are deliberately pending that gate.

Implemented: trusted local credential setup through OS keychain; read-only ING adapter; account discovery and account-specific capability inspection; holdings, balance, and 90-day transaction reads; exact-decimal MT535 parsing; redacted field-availability report; no automatic retries; explicit live-read opt-in. Bank data stays in memory. Only a redacted report is optionally written with owner-only file permissions.

## Local setup

Python 3.12+ and `uv` are required. Run from this directory in your own trusted terminal:

```sh
uv lock
uv sync --locked
uv run ing-investment setup
```

The top-level dependencies are pinned. `uv.lock` is not included: this environment could not reach PyPI and had no cached `fints` package. Generate and review the lockfile with network access before running the live probe. The actual installed dependency integration remains unverified.

Register a FinTS product ID for your application first. Do not reuse another application's ID. See [python-fints setup](https://python-fints.readthedocs.io/en/latest/quickstart.html).

Credentials are entered through hidden prompts and stored as one OS-keychain entry. Never paste credentials into chat, command arguments, `.env`, reports, or a source file. macOS and Windows native keyring backends are allowed; other backends fail closed.

## Explicitly authorized live feasibility check

Section 10 requires explicit user approval for live smoke tests. Running the following command yourself grants permission for one session of account discovery, holdings, balances and booked transactions. It does not initiate payments or orders. Use a fresh report filename.

```sh
mkdir -p reports
uv run ing-investment probe --approve-live-read --product-id YOUR_REGISTERED_ID --report reports/feasibility.json
```

Exit codes: `0` feasibility gate passed; `3` successful probe with insufficient coverage; `2` setup/dependency/authentication/protocol/report failure. Failed calls are never retried automatically. Authentication challenges stop the session without displaying challenge payloads or saving sessions.

The gate requires a recognized Direkt-Depot, Girokonto and Extra-Konto, at least one holding with ISIN/quantity/value/currency, a valid balance and a booked transaction. Missing accounts, unsupported operations, unknown account labels or an empty transaction window require local review. Labels are used only in memory to identify account types; reports contain generic labels and masked IBAN suffixes.

Review field counts and reconcile quantities/values directly against ING's web/app locally. The report omits financial amounts, ISINs, account names, counterparties, descriptions and raw protocol responses. A programmatic pass alone does not establish reconciliation acceptance. If holdings fail, document the incompatibility and use official ING CSV/export as the fallback; do not scrape banking credentials into a browser.

## Offline validation

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q ing_investment tests
```

Tests use synthetic in-memory bank records, never real credentials. They cover missing and malformed decimals, precision, missing fields, redaction, unsupported account coverage, empty holdings, challenges, no retries, operation allowlist, explicit CLI consent and rejection of plaintext keyrings.

## Next milestones

After the live gate and local reconciliation pass, implement the normalized SQLAlchemy store with encryption, migrations and historical snapshots; FastAPI read API; authenticated MCP SDK tools; transaction identity/collision handling and overlapping incremental sync; analytics with explicit data/reference coverage; daily worker; secure remote gateway with revocation; CSV/manual imports. Acceptance also requires real local and remote MCP clients. None of those acceptance checks is claimed by this spike.

See [limitations](docs/LIMITATIONS.md) and [operations and threat model](docs/OPERATIONS.md).
