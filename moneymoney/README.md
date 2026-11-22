# Local ING MCP through MoneyMoney

This connector uses MoneyMoney's registered banking application and documented AppleScript exports. You do not need a personal FinTS product ID for this path. MoneyMoney owns the bank connection and credentials; the bridge reads exported data only.

## Current status

The MCP SDK and all 29 dependencies are installed in `.venv` from the local package cache. Exact versions and package hashes are recorded in `requirements.lock`. A real stdio MCP client successfully initializes the server and reads synthetic holdings/summary data in the test suite. The MoneyMoney application is now installed and the user reports successful ING login and visible accounts/holdings.

The agent workspace cannot reach macOS application services through `osascript`, even for a version query. **The owner’s captured MoneyMoney exports have now been validated:** three depots contain 36 holdings with ISIN, quantity, price, value and currency. A real stdio MCP client successfully read all 36 positions through the corrected parser using those captures. The owner’s subsequent fresh live probe passed: all 12 accounts and all 36 holdings normalized successfully. No bank reconciliation acceptance is implied. Missing fields remain null.

## Validate locally

Keep MoneyMoney open/unlocked and update ING there. In your own terminal:

```sh
cd ~/code/dankelleher/ing-investment-mcp/moneymoney
mkdir -p reports
.venv/bin/python -m ing_moneymoney.probe --report reports/moneymoney-feasibility.json
```

Allow your terminal's MoneyMoney access in macOS Automation when prompted. The report contains account/holding counts, field names, field types, bank-identity match flags and normalization coverage only. It also includes diagnostics for unmatched accounts so an empty match does not hide schema differences. Exit code 3 means the exports did not validate; exit code 0 requires at least one valued holding with ISIN, quantity and currency. It contains no actual account identifiers, holdings names, monetary values, transaction descriptions or credentials. Report creation is exclusive, so use a new filename when repeating. Do not enable raw AppleScript/protocol logging.

## Launch MCP

```sh
./run.sh
```

The process speaks MCP over stdin/stdout and waits for a client; it is not a human-interactive terminal app. Configure a local MCP client using this server entry:

```json
{
  "mcpServers": {
    "ing-moneymoney": {
      "command": "/Users/daniel/code/dankelleher/ing-investment-mcp/moneymoney/run.sh",
      "args": []
    }
  }
}
```

Default tools: `list_accounts`, `list_holdings`, `get_portfolio_summary`, `get_balances`, `get_sync_status`. Pagination uses numeric `cursor` offsets, limits 1–200, and a `next_cursor`. Holdings/summary exclude cash, while balances exclude depots to prevent double counting. Summary reports totals per currency; it does not add currencies without FX data. Missing prices, values, acquisition prices and cost basis remain null.

To separately allow booked cash-account transactions, add `--enable-transactions` to the startup arguments. This adds `search_transactions`; account IDs must come from `list_accounts`, date ranges are capped at 366 days, future dates are rejected, purpose searches are capped and counterparties are withheld. Purpose/asset text is inert data, not instructions. IBAN-like text is masked.

There are no payment/order, arbitrary AppleScript, arbitrary filesystem, arbitrary SQL, arbitrary URL, bank login or bank-refresh tools. Fixed scripts pass validated account UUIDs and ISO dates as AppleScript argv, never interpolated source code.

## Freshness, failure and privacy

The bridge exports MoneyMoney cached data, **not a new ING bank sync**. Update accounts in MoneyMoney yourself. `data_as_of`/`last_successful_sync_at` derive from exported account refresh timestamps; unavailable timestamps produce null and an explicit freshness warning. `last_successful_export_at` is reported separately. Exports are serialized and cached for 60 seconds. Failure retains the previous in-memory snapshot, marks it degraded and preserves its export/sync timestamps. Unknown bank coverage is always explicit.

Only ING accounts identified by bank code `50010517`, BIC `INGDDEFF`/`INGDDEFFXXX`, or a checksum-valid German IBAN containing ING’s bank code are included. User-editable account names never identify a bank. Unknown identifiers are excluded. Generic account labels and hashed identifiers prevent bank-provided names/owner fields from entering MCP responses. No bridge bank credentials or persistent raw exports are needed. The bridge runs locally over stdio; local process access is its authorization boundary. Remote HTTP access, gateways, encrypted historical storage and scheduled refresh are not implemented by this connector.

## Reproduce dependencies and tests

```sh
uv venv .venv
uv pip sync --python .venv/bin/python --require-hashes requirements.lock
.venv/bin/python -m unittest discover -s tests -v
```


Official documentation: [MoneyMoney AppleScript](https://moneymoney.app/api/applescript/), [supported banks](https://moneymoney.app/banken/), [trial download](https://moneymoney.app/download/). The trial is 30 days; this setup does not purchase a license.

## Depots whose bank identifier is empty

The live account export shows cash accounts with ING's BIC, but depot rows with empty bank codes and no BIC/IBAN. Those depots are not automatically attributed to ING. Select your ING depots locally:

```sh
.venv/bin/python -m ing_moneymoney.probe --select-depots
```

The interactive list displays depot names only in your trusted terminal. Enter the numbers belonging to ING, separated by commas. Blank input clears selection. Do not paste the local selection list into chat; the JSON report following it is redacted.

Selection persists in `moneymoney.local.json` with mode 0600, containing only UUIDs, and is excluded from Git. The server automatically reads it at startup. Restart an already running MCP server after changing selection. Selection can admit only unidentified depot rows; it cannot override an identified different bank, include groups or enable cash accounts. MCP responses label this bank attribution `owner_selected_depot` and include a warning. Selection is not available as an agent tool.

## Portfolio export troubleshooting

When a selected depot fails export, the probe now distinguishes AppleScript failure (with numeric error code only), plist parsing, and unexpected record schemas. It does not claim that every export failure is an Automation problem.

The owner can capture raw portfolio data locally for an authorized implementation review:

```sh
.venv/bin/python -m ing_moneymoney.probe --capture-portfolio
```

Successful AppleScript stdout is written before parsing to fresh `reports/moneymoney-portfolio-*.plist` files with mode 0600. Those files contain actual holdings data, are excluded from Git and are never offered as MCP tools. The JSON report lists their paths. This is an opt-in local diagnostic; normal MCP operation does not save raw data. The command uses the existing owner-selected depots, without asking to select them again. Delete diagnostic files after validation.

## Verified portfolio mapping (MoneyMoney 2.5.3)

The live exports have top-level `creator` and `portfolio` keys. Position fields map as follows: `price` → unit price, `amount` → position value, `currencyOfAmount` → valuation currency, `currencyOfPrice` → price currency, `purchasePrice` and `currencyOfPurchasePrice` → acquisition price and its currency, `tradeTimestamp` → separate UTC timestamp and valuation date. Price, valuation and acquisition currencies stay separate. The parser also supports the older `securities` layout; ambiguous dual layouts are rejected.

All 36 captured holdings had required valuation fields. None supplied an explicit `purchaseValue`, so cost basis stays null; it is not inferred from profit or average purchase price. XML real literals are preserved as Decimal, including MoneyMoney’s floating-point export artifacts. The bridge cannot restore precision lost inside MoneyMoney.

## Live acceptance result

On 13 October 2026, the owner ran the corrected probe locally: `validation_passed=true`, 12 accounts, 3 depots, position counts 10/13/13. All 36 positions supplied ISIN, quantity, price, market value and currency. Cost basis coverage remains zero and is represented by null. Bank/app value reconciliation, real transactions and a live MCP-client connection are separate outstanding acceptance steps; this pass establishes export and normalization compatibility.

## Connected MCP acceptance

On 13 October 2026, after client restart, the actual `ing-moneymoney` MCP connection successfully served `list_accounts`, `list_holdings`, `get_balances`, `get_portfolio_summary` and `get_sync_status`. It reported 12 accounts, 36 holding positions across 3 depots, 35 distinct ISIN exposures and no missing valuations. There was no export failure. Transaction tools remain disabled. This establishes live local MCP connectivity; remote-client acceptance and financial reconciliation remain outstanding.
