# Feasibility status

- Live ING compatibility, credentials, product ID, account-specific permissions, session expiry and TAN behavior are not verified.
- The top-level library versions are pinned but cannot be described as tested installed versions. Dependency installation and a resolved lockfile remain blocked by local network restrictions.
- The upstream MT535 parser converts values to float. The connector replaces the parser used by `fints.client` with a deliberately narrow Decimal parser before opening a session. Unsupported MT535 formats remain missing; production support requires sanitized captured-format tests after the live gate.
- Holdings' `market_value` is the unit price; `total_value` is the position valuation. The acquisition price is not cost basis. No missing price/value/date/currency is fabricated.
- Account type is determined from ING product names in memory. Unknown names remain unknown and fail full-account-coverage acceptance.
- Any malformed/partial bank read stops the probe. No prior successful report is overwritten, no financial history is persisted, and no automatic recovery or retry is attempted.
- The spec's 90-day window is a bank retrieval limit, not a promise of complete historical records.
- Reports contain partial IBAN suffixes and stable hashed account identifiers: treat them as private. Hashing is pseudonymization, not anonymization.
- No REST server, MCP server, remote access, normalized database, transaction deduplication, scheduled sync, portfolio performance, FX, classification, or ETF look-through is implemented before feasibility approval.
- Dependency scans, encrypted storage/backups, retention, source reconciliation and MCP client acceptance remain release blockers for later milestones.
